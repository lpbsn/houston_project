from __future__ import annotations

import uuid

from django.db import transaction
from django.db.models import Q

from houston.establishments.models import (
    ContentReport,
    EstablishmentMembership,
    MembershipBlock,
)
from houston.establishments.safety_constants import (
    CONTENT_REPORT_REASON_MAX_LENGTH,
    MEMBERSHIP_BLOCKED_CODE,
    MEMBERSHIP_BLOCKED_DETAIL,
)


class MembershipBlockedError(Exception):
    code = MEMBERSHIP_BLOCKED_CODE
    detail = MEMBERSHIP_BLOCKED_DETAIL


class ContentReportValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


def memberships_are_blocked(
    *,
    first_membership_id: uuid.UUID,
    second_membership_id: uuid.UUID,
) -> bool:
    if first_membership_id == second_membership_id:
        return False
    return MembershipBlock.objects.filter(
        Q(
            blocker_membership_id=first_membership_id,
            blocked_membership_id=second_membership_id,
        )
        | Q(
            blocker_membership_id=second_membership_id,
            blocked_membership_id=first_membership_id,
        )
    ).exists()


def blocked_membership_ids_for(*, membership_id: uuid.UUID) -> set[uuid.UUID]:
    outgoing = MembershipBlock.objects.filter(blocker_membership_id=membership_id).values_list(
        "blocked_membership_id",
        flat=True,
    )
    incoming = MembershipBlock.objects.filter(blocked_membership_id=membership_id).values_list(
        "blocker_membership_id",
        flat=True,
    )
    return set(outgoing) | set(incoming)


def require_not_blocked(
    *,
    actor_membership_id: uuid.UUID,
    other_membership_id: uuid.UUID,
) -> None:
    if memberships_are_blocked(
        first_membership_id=actor_membership_id,
        second_membership_id=other_membership_id,
    ):
        raise MembershipBlockedError


@transaction.atomic
def block_membership(
    *,
    actor_membership: EstablishmentMembership,
    target_membership: EstablishmentMembership,
) -> MembershipBlock:
    if actor_membership.id == target_membership.id:
        raise ContentReportValidationError("You cannot block yourself.")
    if actor_membership.establishment_id != target_membership.establishment_id:
        raise ContentReportValidationError("Members must belong to the same establishment.")
    if target_membership.status != EstablishmentMembership.Status.ACTIVE:
        raise ContentReportValidationError("This member cannot be blocked.")

    block, _created = MembershipBlock.objects.get_or_create(
        establishment_id=actor_membership.establishment_id,
        blocker_membership=actor_membership,
        blocked_membership=target_membership,
    )
    return block


@transaction.atomic
def unblock_membership(
    *,
    actor_membership: EstablishmentMembership,
    target_membership_id: uuid.UUID,
) -> None:
    MembershipBlock.objects.filter(
        blocker_membership=actor_membership,
        blocked_membership_id=target_membership_id,
    ).delete()


@transaction.atomic
def create_content_report(
    *,
    actor_membership: EstablishmentMembership,
    content_kind: str,
    reason: str,
    target_membership_id: uuid.UUID | None = None,
    content_id: uuid.UUID | None = None,
) -> ContentReport:
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise ContentReportValidationError("A reason is required.")
    if len(normalized_reason) > CONTENT_REPORT_REASON_MAX_LENGTH:
        raise ContentReportValidationError("Reason is too long.")
    if content_kind not in ContentReport.ContentKind.values:
        raise ContentReportValidationError("Invalid content kind.")

    target = None
    if target_membership_id is not None:
        target = EstablishmentMembership.objects.filter(
            id=target_membership_id,
            establishment_id=actor_membership.establishment_id,
        ).first()
        if target is None:
            raise ContentReportValidationError("Invalid target member.")
        if target.id == actor_membership.id:
            raise ContentReportValidationError("You cannot report yourself.")

    report = ContentReport.objects.create(
        establishment_id=actor_membership.establishment_id,
        reporter_membership=actor_membership,
        target_membership=target,
        content_kind=content_kind,
        content_id=content_id,
        reason=normalized_reason,
        status=ContentReport.Status.OPEN,
    )
    from houston.establishments.report_email import schedule_content_report_operator_email

    schedule_content_report_operator_email(report_id=report.id)
    return report
