"""Preflight and limited repair for organizational owner membership coverage.

Does not import establishments.services (avoids circular dependencies).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.db import transaction

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.selectors import org_establishments_draft_active
from houston.organizations.models import Organization

ISSUE_MISSING_OWNER = "missing_owner"
ISSUE_STATUS_MIX = "status_mix"
ISSUE_NON_OWNER_CONFLICT = "non_owner_conflict"
ISSUE_OWNER_USER_STATUS_CONFLICT = "owner_user_status_conflict"
ISSUE_MISSING_FULL_COVERAGE_ACTIVE_OWNER = "missing_full_coverage_active_owner"

_USER_BLOCKING_ISSUES = frozenset(
    {
        ISSUE_STATUS_MIX,
        ISSUE_NON_OWNER_CONFLICT,
        ISSUE_OWNER_USER_STATUS_CONFLICT,
    }
)


@dataclass(frozen=True)
class ConsistencyIssue:
    code: str
    organization_id: Any
    user_id: Any | None = None
    establishment_id: Any | None = None
    detail: str = ""
    blocking: bool = True


@dataclass
class PlannedOwnerCreate:
    organization_id: Any
    user_id: Any
    establishment_id: Any
    status: str


@dataclass
class OrganizationConsistencyReport:
    organization_id: Any
    issues: list[ConsistencyIssue] = field(default_factory=list)
    planned_creates: list[PlannedOwnerCreate] = field(default_factory=list)

    @property
    def has_blocking_issues(self) -> bool:
        return any(issue.blocking for issue in self.issues)

    @property
    def has_hard_conflicts(self) -> bool:
        """status_mix / non_owner / user.status — block all writes in this org."""
        return any(issue.code in _USER_BLOCKING_ISSUES for issue in self.issues)

    @property
    def is_repair_eligible(self) -> bool:
        # Homogeneous missing_owner gaps may clear a blocking full-coverage issue;
        # hard conflicts never allow writes in the organization.
        if self.has_hard_conflicts:
            return False
        return bool(self.planned_creates)


@dataclass
class ConsistencyInventory:
    organizations: list[OrganizationConsistencyReport] = field(default_factory=list)

    @property
    def has_blocking_issues(self) -> bool:
        return any(report.has_blocking_issues for report in self.organizations)

    @property
    def planned_creates(self) -> list[PlannedOwnerCreate]:
        return [
            create
            for report in self.organizations
            if report.is_repair_eligible
            for create in report.planned_creates
        ]


@dataclass
class RepairResult:
    dry_run: bool
    created: list[PlannedOwnerCreate] = field(default_factory=list)
    skipped_organization_ids: list[Any] = field(default_factory=list)
    inventory: ConsistencyInventory | None = None

    @property
    def has_unresolved_conflicts(self) -> bool:
        """True when hard conflicts remain, or blocking issues remain after apply."""
        if self.inventory is None:
            return bool(self.skipped_organization_ids)
        if any(report.has_hard_conflicts for report in self.inventory.organizations):
            return True
        if self.skipped_organization_ids:
            return True
        if not self.dry_run and self.inventory.has_blocking_issues:
            return True
        # Dry-run: unfixable blocking full-coverage (nothing this repair can create).
        if self.dry_run:
            for report in self.inventory.organizations:
                if report.is_repair_eligible:
                    continue
                if any(
                    issue.code == ISSUE_MISSING_FULL_COVERAGE_ACTIVE_OWNER and issue.blocking
                    for issue in report.issues
                ):
                    return True
        return False


def _lock_organization(*, organization_id) -> Organization:
    return Organization.objects.select_for_update().get(id=organization_id)


def _lock_memberships_by_ids(*, membership_ids: list) -> list[EstablishmentMembership]:
    ordered_ids = sorted({membership_id for membership_id in membership_ids if membership_id})
    locked: list[EstablishmentMembership] = []
    qs = EstablishmentMembership.objects.select_for_update().select_related("user", "establishment")
    for membership_id in ordered_ids:
        membership = qs.filter(id=membership_id).first()
        if membership is not None:
            locked.append(membership)
    return locked


def _owner_user_status_conflict(*, user_status: str, owner_statuses: set[str]) -> bool:
    if (
        user_status == User.Status.PENDING
        and EstablishmentMembership.Status.ACTIVE in owner_statuses
    ):
        return True
    if (
        user_status == User.Status.ACTIVE
        and EstablishmentMembership.Status.INVITED in owner_statuses
    ):
        return True
    if user_status in {User.Status.SUSPENDED, User.Status.ANONYMIZED} and (
        EstablishmentMembership.Status.ACTIVE in owner_statuses
        or EstablishmentMembership.Status.INVITED in owner_statuses
    ):
        return True
    return False


def _analyze_organization(
    *,
    organization_id,
    establishments: list[Establishment] | None = None,
) -> OrganizationConsistencyReport:
    if establishments is None:
        establishments = org_establishments_draft_active(organization_id=organization_id)

    report = OrganizationConsistencyReport(organization_id=organization_id)
    if not establishments:
        return report

    establishment_ids = [est.id for est in establishments]
    has_active_establishment = any(
        est.status == Establishment.Status.ACTIVE for est in establishments
    )

    memberships = list(
        EstablishmentMembership.objects.filter(establishment_id__in=establishment_ids)
        .select_related("user")
        .order_by("id")
    )
    by_user: dict[Any, dict[Any, EstablishmentMembership]] = {}
    owner_user_ids: set[Any] = set()
    for membership in memberships:
        by_user.setdefault(membership.user_id, {})[membership.establishment_id] = membership
        if membership.role == EstablishmentMembership.Role.OWNER:
            owner_user_ids.add(membership.user_id)

    full_coverage_active_owner = False

    for user_id in sorted(owner_user_ids, key=str):
        per_est = by_user.get(user_id, {})
        owner_statuses: set[str] = set()
        missing_establishment_ids: list[Any] = []
        user_status: str | None = None

        for establishment in establishments:
            membership = per_est.get(establishment.id)
            if membership is None:
                missing_establishment_ids.append(establishment.id)
                report.issues.append(
                    ConsistencyIssue(
                        code=ISSUE_MISSING_OWNER,
                        organization_id=organization_id,
                        user_id=user_id,
                        establishment_id=establishment.id,
                        detail="owner membership absent",
                    )
                )
                continue

            if user_status is None:
                user_status = membership.user.status

            if membership.role != EstablishmentMembership.Role.OWNER:
                report.issues.append(
                    ConsistencyIssue(
                        code=ISSUE_NON_OWNER_CONFLICT,
                        organization_id=organization_id,
                        user_id=user_id,
                        establishment_id=establishment.id,
                        detail=f"non-owner role={membership.role}",
                    )
                )
                continue

            owner_statuses.add(membership.status)

        if len(owner_statuses) > 1:
            report.issues.append(
                ConsistencyIssue(
                    code=ISSUE_STATUS_MIX,
                    organization_id=organization_id,
                    user_id=user_id,
                    detail=f"owner statuses={sorted(owner_statuses)}",
                )
            )

        if user_status is not None and owner_statuses and _owner_user_status_conflict(
            user_status=user_status,
            owner_statuses=owner_statuses,
        ):
            report.issues.append(
                ConsistencyIssue(
                    code=ISSUE_OWNER_USER_STATUS_CONFLICT,
                    organization_id=organization_id,
                    user_id=user_id,
                    detail=f"user.status={user_status} owner_statuses={sorted(owner_statuses)}",
                )
            )

        user_has_blockers = any(
            issue.user_id == user_id and issue.code in _USER_BLOCKING_ISSUES
            for issue in report.issues
        )
        if (
            missing_establishment_ids
            and len(owner_statuses) == 1
            and not user_has_blockers
        ):
            homogeneous_status = next(iter(owner_statuses))
            for establishment_id in missing_establishment_ids:
                report.planned_creates.append(
                    PlannedOwnerCreate(
                        organization_id=organization_id,
                        user_id=user_id,
                        establishment_id=establishment_id,
                        status=homogeneous_status,
                    )
                )

        covers_all = True
        for establishment in establishments:
            membership = per_est.get(establishment.id)
            if (
                membership is None
                or membership.role != EstablishmentMembership.Role.OWNER
                or membership.status != EstablishmentMembership.Status.ACTIVE
            ):
                covers_all = False
                break
        if covers_all:
            full_coverage_active_owner = True

    if not full_coverage_active_owner:
        report.issues.append(
            ConsistencyIssue(
                code=ISSUE_MISSING_FULL_COVERAGE_ACTIVE_OWNER,
                organization_id=organization_id,
                detail=(
                    "no owner/active user covers all draft/active establishments"
                ),
                blocking=has_active_establishment,
            )
        )

    return report


def plan_owner_memberships_for_establishment(
    *,
    organization_id,
    establishment_id,
) -> tuple[OrganizationConsistencyReport, list[PlannedOwnerCreate]]:
    """Lot B analysis; return planned owner creates for one establishment.

    Caller should hold the organization row lock. Hard conflicts
    (``status_mix`` / ``non_owner_conflict`` / ``owner_user_status_conflict``)
    are reported on the full organization; ``planned_creates`` are filtered to
    ``establishment_id`` only.
    """
    report = _analyze_organization(organization_id=organization_id)
    plans = [
        plan
        for plan in report.planned_creates
        if plan.establishment_id == establishment_id
    ]
    return report, plans


def inventory_organizational_owners(
    *,
    organization_ids: list | None = None,
) -> ConsistencyInventory:
    if organization_ids is None:
        org_ids = list(Organization.objects.order_by("id").values_list("id", flat=True))
    else:
        org_ids = list(organization_ids)

    inventory = ConsistencyInventory()
    for organization_id in org_ids:
        establishments = org_establishments_draft_active(organization_id=organization_id)
        if not establishments:
            continue
        inventory.organizations.append(
            _analyze_organization(
                organization_id=organization_id,
                establishments=establishments,
            )
        )
    return inventory


def repair_organizational_owners(*, dry_run: bool = True) -> RepairResult:
    """Create missing homogeneous owner memberships. Dry-run by default."""
    if dry_run:
        inventory = inventory_organizational_owners()
        created: list[PlannedOwnerCreate] = []
        skipped: list[Any] = []
        for report in inventory.organizations:
            if report.is_repair_eligible:
                created.extend(report.planned_creates)
            elif report.planned_creates or any(
                issue.code in _USER_BLOCKING_ISSUES for issue in report.issues
            ):
                skipped.append(report.organization_id)
            elif report.has_blocking_issues and not report.planned_creates:
                # Blocking full-coverage (or similar) with nothing to repair.
                skipped.append(report.organization_id)
        return RepairResult(
            dry_run=True,
            created=created,
            skipped_organization_ids=skipped,
            inventory=inventory,
        )

    created = []
    skipped = []
    # Discover candidate org ids without holding long locks.
    initial = inventory_organizational_owners()
    candidate_org_ids = [report.organization_id for report in initial.organizations]

    for organization_id in candidate_org_ids:
        with transaction.atomic():
            _lock_organization(organization_id=organization_id)
            establishments = org_establishments_draft_active(organization_id=organization_id)
            membership_ids = list(
                EstablishmentMembership.objects.filter(
                    establishment_id__in=[est.id for est in establishments]
                ).values_list("id", flat=True)
            )
            _lock_memberships_by_ids(membership_ids=membership_ids)
            report = _analyze_organization(
                organization_id=organization_id,
                establishments=establishments,
            )
            if not report.is_repair_eligible:
                if report.planned_creates or any(
                    issue.code in _USER_BLOCKING_ISSUES for issue in report.issues
                ):
                    skipped.append(organization_id)
                elif report.has_blocking_issues:
                    skipped.append(organization_id)
                continue

            for plan in report.planned_creates:
                EstablishmentMembership.objects.create(
                    user_id=plan.user_id,
                    establishment_id=plan.establishment_id,
                    role=EstablishmentMembership.Role.OWNER,
                    status=plan.status,
                )
                created.append(plan)

    final_inventory = inventory_organizational_owners()
    return RepairResult(
        dry_run=False,
        created=created,
        skipped_organization_ids=skipped,
        inventory=final_inventory,
    )


def summarize_inventory(inventory: ConsistencyInventory) -> dict[str, int]:
    counts: dict[str, int] = {
        "organizations": len(inventory.organizations),
        "blocking_issues": 0,
        "informative_issues": 0,
        "planned_creates": len(inventory.planned_creates),
        ISSUE_MISSING_OWNER: 0,
        ISSUE_STATUS_MIX: 0,
        ISSUE_NON_OWNER_CONFLICT: 0,
        ISSUE_OWNER_USER_STATUS_CONFLICT: 0,
        ISSUE_MISSING_FULL_COVERAGE_ACTIVE_OWNER: 0,
    }
    for report in inventory.organizations:
        for issue in report.issues:
            counts[issue.code] = counts.get(issue.code, 0) + 1
            if issue.blocking:
                counts["blocking_issues"] += 1
            else:
                counts["informative_issues"] += 1
    return counts
