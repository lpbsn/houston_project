from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from django.db import transaction
from django.db.models import Prefetch, Q

from houston.establishments.models import (
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
    MembershipScope,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
    TaxonomyMigrationMap,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


class InvalidMembershipScopeAssignmentError(Exception):
    pass


class MembershipScopeType:
    BUSINESS_UNIT = "business_unit"
    MODULE = "module"
    DOMAIN = "domain"
    SUBJECT = "subject"

    _API_ALL = frozenset({BUSINESS_UNIT, MODULE, DOMAIN, SUBJECT})
    _PRIMARY = frozenset({BUSINESS_UNIT})


@dataclass(frozen=True)
class MembershipScopeInput:
    scope_type: str
    scope_id: UUID


@dataclass(frozen=True)
class ResolvedMembershipScope:
    business_unit: BusinessUnit


def membership_scope_prefetch() -> Prefetch:
    return Prefetch(
        "scope_links",
        queryset=MembershipScope.objects.select_related(
            "business_unit",
            "operational_module",
            "operational_domain",
            "operational_subject",
        ),
    )


def normalize_membership_scope_inputs(
    *,
    establishment: Establishment,
    scope_inputs: Iterable[MembershipScopeInput],
) -> list[ResolvedMembershipScope]:
    resolved = _resolve_scope_inputs(
        establishment=establishment,
        scope_inputs=scope_inputs,
    )
    return _dedupe_business_units(resolved)


@transaction.atomic
def replace_membership_scopes(
    *,
    membership: EstablishmentMembership,
    scope_inputs: Iterable[MembershipScopeInput],
) -> list[MembershipScope]:
    establishment = membership.establishment
    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=scope_inputs,
    )

    requested_ids = {scope.business_unit.id for scope in normalized}

    existing_scopes = list(MembershipScope.objects.filter(membership=membership))
    for scope in existing_scopes:
        bu_id = _scope_business_unit_id(scope, establishment=establishment)
        if bu_id not in requested_ids:
            scope.delete()

    existing_bu_ids = {
        _scope_business_unit_id(scope, establishment=establishment)
        for scope in existing_scopes
        if _scope_business_unit_id(scope, establishment=establishment) in requested_ids
    }

    created: list[MembershipScope] = []
    for resolved in normalized:
        if resolved.business_unit.id in existing_bu_ids:
            continue
        created.append(
            MembershipScope.objects.create(
                membership=membership,
                business_unit=resolved.business_unit,
            )
        )
        existing_bu_ids.add(resolved.business_unit.id)

    return created


def membership_scope_covers_business_unit(
    membership: EstablishmentMembership,
    business_unit: BusinessUnit,
) -> bool:
    for scope in _iter_membership_scopes(membership):
        bu_id = _scope_business_unit_id(scope, establishment=membership.establishment)
        if bu_id == business_unit.id:
            return True
    return False


def membership_scope_covers_module(
    membership: EstablishmentMembership,
    module: OperationalModule,
) -> bool:
    bu = _business_unit_for_legacy(
        establishment=membership.establishment,
        legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_MODULE,
        legacy_id=module.id,
    )
    if bu is None:
        for scope in _iter_membership_scopes(membership):
            if scope.operational_module_id == module.id:
                return True
        return False
    return membership_scope_covers_business_unit(membership, bu)


def membership_scope_covers_domain(
    membership: EstablishmentMembership,
    domain: OperationalDomain,
) -> bool:
    bu = _business_unit_for_legacy_module_domain(membership.establishment, domain)
    if bu is not None:
        return membership_scope_covers_business_unit(membership, bu)
    for scope in _iter_membership_scopes(membership):
        if scope.operational_domain_id == domain.id:
            return True
        if scope.operational_module_id is not None and domain.operational_module_id is not None:
            if scope.operational_module_id == domain.operational_module_id:
                return True
    return False


def membership_scope_covers_subject(
    membership: EstablishmentMembership,
    subject: OperationalSubject,
) -> bool:
    bu = _business_unit_for_legacy(
        establishment=membership.establishment,
        legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_SUBJECT,
        legacy_id=subject.id,
    )
    if bu is not None:
        return membership_scope_covers_business_unit(membership, bu)
    subject_domain = subject.operational_domain
    for scope in _iter_membership_scopes(membership):
        if scope.operational_subject_id == subject.id:
            return True
        if scope.operational_domain_id is not None and subject_domain is not None:
            if scope.operational_domain_id == subject_domain.id:
                return True
        if (
            scope.operational_module_id is not None
            and subject_domain is not None
            and subject_domain.operational_module_id is not None
        ):
            if scope.operational_module_id == subject_domain.operational_module_id:
                return True
    return False


def build_signal_feed_scope_q(*, membership: EstablishmentMembership) -> Q | None:
    """Legacy v1 feed scope on operational_module/domain/subject (until Signal 3A cutover)."""
    conditions = Q()
    has_scope = False
    for scope in _iter_membership_scopes(membership):
        has_scope = True
        if scope.business_unit_id is not None:
            continue
        if scope.operational_module_id is not None:
            conditions |= Q(operational_module_id=scope.operational_module_id)
        elif scope.operational_domain_id is not None:
            conditions |= Q(operational_domain_id=scope.operational_domain_id)
        elif scope.operational_subject_id is not None:
            conditions |= Q(operational_subject_id=scope.operational_subject_id)
    if not has_scope:
        return None
    return conditions if conditions else None


def build_signal_feed_scope_q_v2(*, membership: EstablishmentMembership) -> Q | None:
    """Ma vue filter on affected OR responsible BusinessUnit scopes."""
    bu_ids: set[UUID] = set()
    for scope in _iter_membership_scopes(membership):
        bu_id = _scope_business_unit_id(scope, establishment=membership.establishment)
        if bu_id is not None:
            bu_ids.add(bu_id)
    if not bu_ids:
        return None
    return Q(affected_business_unit_id__in=bu_ids) | Q(responsible_business_unit_id__in=bu_ids)


def _iter_membership_scopes(membership: EstablishmentMembership) -> Iterable[MembershipScope]:
    cache = getattr(membership, "_prefetched_objects_cache", None)
    if cache is not None and "scope_links" in cache:
        return membership.scope_links.all()

    return MembershipScope.objects.filter(membership=membership).select_related(
        "business_unit",
        "operational_module",
        "operational_domain",
        "operational_subject",
    )


def _resolve_scope_inputs(
    *,
    establishment: Establishment,
    scope_inputs: Iterable[MembershipScopeInput],
) -> list[ResolvedMembershipScope]:
    resolved_by_bu: dict[UUID, ResolvedMembershipScope] = {}

    for scope_input in scope_inputs:
        if scope_input.scope_type not in MembershipScopeType._API_ALL:
            raise InvalidMembershipScopeAssignmentError(
                "Scope type must be business_unit, module, domain, or subject."
            )

        business_unit = _resolve_scope_input_to_business_unit(
            establishment=establishment,
            scope_input=scope_input,
        )
        resolved_by_bu[business_unit.id] = ResolvedMembershipScope(business_unit=business_unit)

    return list(resolved_by_bu.values())


def _resolve_scope_input_to_business_unit(
    *,
    establishment: Establishment,
    scope_input: MembershipScopeInput,
) -> BusinessUnit:
    if scope_input.scope_type == MembershipScopeType.BUSINESS_UNIT:
        business_unit = (
            BusinessUnit.objects.filter(
                id=scope_input.scope_id,
                establishment=establishment,
                active=True,
            )
            .first()
        )
        if business_unit is None:
            raise InvalidMembershipScopeAssignmentError(
                "Business unit scope must be active and belong to the same establishment."
            )
        return business_unit

    if scope_input.scope_type == MembershipScopeType.MODULE:
        module = OperationalModule.objects.filter(
            id=scope_input.scope_id,
            establishment=establishment,
            active=True,
        ).first()
        if module is None:
            raise InvalidMembershipScopeAssignmentError(
                "Operational scope must be active and belong to the same establishment."
            )
        bu = _business_unit_for_legacy(
            establishment=establishment,
            legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_MODULE,
            legacy_id=module.id,
        )
        if bu is None:
            raise InvalidMembershipScopeAssignmentError(
                "Legacy module scope could not be mapped to a business unit."
            )
        return bu

    if scope_input.scope_type == MembershipScopeType.DOMAIN:
        domain = OperationalDomain.objects.filter(
            id=scope_input.scope_id,
            establishment=establishment,
            active=True,
        ).first()
        if domain is None:
            raise InvalidMembershipScopeAssignmentError(
                "Operational scope must be active and belong to the same establishment."
            )
        bu = _business_unit_for_legacy_module_domain(establishment, domain)
        if bu is None:
            raise InvalidMembershipScopeAssignmentError(
                "Legacy domain scope could not be mapped to a business unit."
            )
        return bu

    subject = OperationalSubject.objects.filter(
        id=scope_input.scope_id,
        establishment=establishment,
        active=True,
    ).first()
    if subject is None:
        raise InvalidMembershipScopeAssignmentError(
            "Operational scope must be active and belong to the same establishment."
        )
    bu = _business_unit_for_legacy(
        establishment=establishment,
        legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_SUBJECT,
        legacy_id=subject.id,
    )
    if bu is None and subject.operational_domain is not None:
        bu = _business_unit_for_legacy_module_domain(establishment, subject.operational_domain)
    if bu is None:
        raise InvalidMembershipScopeAssignmentError(
            "Legacy subject scope could not be mapped to a business unit."
        )
    return bu


def _dedupe_business_units(
    resolved_scopes: list[ResolvedMembershipScope],
) -> list[ResolvedMembershipScope]:
    seen: dict[UUID, ResolvedMembershipScope] = {}
    for scope in resolved_scopes:
        seen[scope.business_unit.id] = scope
    return list(seen.values())


def _business_unit_for_legacy(
    *,
    establishment: Establishment,
    legacy_type: str,
    legacy_id: UUID,
) -> BusinessUnit | None:
    if legacy_type == TaxonomyMigrationMap.LegacyType.OPERATIONAL_SUBJECT:
        mapping = TaxonomyMigrationMap.objects.filter(
            establishment=establishment,
            legacy_type=legacy_type,
            legacy_id=legacy_id,
            new_type=TaxonomyMigrationMap.NewType.ACTIVITY_SUBJECT,
        ).first()
        if mapping is None:
            return None
        from houston.establishments.models import ActivitySubject

        subject = (
            ActivitySubject.objects.filter(id=mapping.new_id)
            .select_related("business_unit")
            .first()
        )
        return subject.business_unit if subject else None

    mapping = TaxonomyMigrationMap.objects.filter(
        establishment=establishment,
        legacy_type=legacy_type,
        legacy_id=legacy_id,
        new_type=TaxonomyMigrationMap.NewType.BUSINESS_UNIT,
    ).first()
    if mapping is None:
        return None
    return BusinessUnit.objects.filter(id=mapping.new_id, active=True).first()


def _business_unit_for_legacy_module_domain(
    establishment: Establishment,
    domain: OperationalDomain,
) -> BusinessUnit | None:
    if domain.operational_module_id is not None:
        bu = _business_unit_for_legacy(
            establishment=establishment,
            legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_MODULE,
            legacy_id=domain.operational_module_id,
        )
        if bu is not None:
            return bu
    return _business_unit_for_legacy(
        establishment=establishment,
        legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_DOMAIN,
        legacy_id=domain.id,
    )


def _scope_business_unit_id(
    scope: MembershipScope,
    *,
    establishment: Establishment,
) -> UUID | None:
    if scope.business_unit_id is not None:
        return scope.business_unit_id
    if scope.operational_module_id is not None:
        bu = _business_unit_for_legacy(
            establishment=establishment,
            legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_MODULE,
            legacy_id=scope.operational_module_id,
        )
        return bu.id if bu else None
    if scope.operational_domain_id is not None:
        domain = scope.operational_domain
        if domain is None:
            domain = OperationalDomain.objects.filter(id=scope.operational_domain_id).first()
        if domain is None:
            return None
        bu = _business_unit_for_legacy_module_domain(establishment, domain)
        return bu.id if bu else None
    if scope.operational_subject_id is not None:
        bu = _business_unit_for_legacy(
            establishment=establishment,
            legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_SUBJECT,
            legacy_id=scope.operational_subject_id,
        )
        return bu.id if bu else None
    return None


def parse_membership_scope_inputs(
    scopes: Iterable[dict[str, object]],
) -> list[MembershipScopeInput]:
    parsed: list[MembershipScopeInput] = []
    for item in scopes:
        if not isinstance(item, dict):
            raise InvalidMembershipScopeAssignmentError(
                "Each scope must include scope_type and scope_id."
            )
        scope_type = item.get("scope_type")
        scope_id = item.get("scope_id")
        if not isinstance(scope_type, str) or scope_type not in MembershipScopeType._API_ALL:
            raise InvalidMembershipScopeAssignmentError(
                "Scope type must be business_unit, module, domain, or subject."
            )
        if scope_id is None:
            raise InvalidMembershipScopeAssignmentError("Each scope must include scope_id.")
        try:
            parsed_scope_id = UUID(str(scope_id))
        except (TypeError, ValueError) as exc:
            raise InvalidMembershipScopeAssignmentError(
                "Each scope must include a valid scope_id."
            ) from exc
        parsed.append(MembershipScopeInput(scope_type=scope_type, scope_id=parsed_scope_id))
    return parsed


def membership_scope_rows_for_membership(
    membership: EstablishmentMembership,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    business_unit_count = 0
    scopes_payload: list[dict[str, str]] = []
    seen_bu: set[UUID] = set()

    for scope in _iter_membership_scopes(membership):
        bu_id = _scope_business_unit_id(scope, establishment=membership.establishment)
        if bu_id is None or bu_id in seen_bu:
            continue
        seen_bu.add(bu_id)
        scopes_payload.append(
            {
                "scope_type": MembershipScopeType.BUSINESS_UNIT,
                "scope_id": str(bu_id),
            }
        )
        business_unit_count += 1

    return scopes_payload, {
        "business_unit_count": business_unit_count,
        "module_count": 0,
        "domain_count": 0,
        "subject_count": 0,
    }


@transaction.atomic
def assign_membership_scopes(
    *,
    membership: EstablishmentMembership,
    scope_inputs: Iterable[MembershipScopeInput],
) -> None:
    replace_membership_scopes(membership=membership, scope_inputs=scope_inputs)


def scopes_not_allowed_for_role(role: str) -> bool:
    return role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }
