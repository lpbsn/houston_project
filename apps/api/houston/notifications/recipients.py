from __future__ import annotations

import uuid

from houston.action_plans.constants import EXECUTION_STATUS_PENDING_VALIDATION
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.permissions import can_validate_action_plan_execution
from houston.comments.models import Comment
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal


def _dedupe_memberships(
    memberships: list[EstablishmentMembership],
) -> list[EstablishmentMembership]:
    seen_ids: set[uuid.UUID] = set()
    deduped: list[EstablishmentMembership] = []
    for membership in memberships:
        if membership.id in seen_ids:
            continue
        seen_ids.add(membership.id)
        deduped.append(membership)
    return deduped


def _active_action_plan_assignee_memberships(
    *,
    execution: ActionPlanExecution,
) -> list[EstablishmentMembership]:
    return [
        assignee.membership
        for assignee in execution.assignees.select_related("membership").all()
        if assignee.membership.status == EstablishmentMembership.Status.ACTIVE
        and assignee.membership.establishment_id == execution.establishment_id
    ]


def resolve_action_plan_execution_created_recipients(
    *,
    execution: ActionPlanExecution,
) -> list[EstablishmentMembership]:
    return _dedupe_memberships(_active_action_plan_assignee_memberships(execution=execution))


def resolve_action_plan_execution_pending_validation_recipients(
    *,
    execution: ActionPlanExecution,
) -> list[EstablishmentMembership]:
    if execution.status != EXECUTION_STATUS_PENDING_VALIDATION:
        return []

    validators: list[EstablishmentMembership] = []
    for membership in EstablishmentMembership.objects.filter(
        establishment_id=execution.establishment_id,
        status=EstablishmentMembership.Status.ACTIVE,
    ).select_related("user"):
        if can_validate_action_plan_execution(membership, execution):
            validators.append(membership)
    return validators


def resolve_action_plan_execution_reopened_recipients(
    *,
    execution: ActionPlanExecution,
) -> list[EstablishmentMembership]:
    recipients = _active_action_plan_assignee_memberships(execution=execution)
    creator = execution.created_by
    if (
        creator is not None
        and creator.status == EstablishmentMembership.Status.ACTIVE
        and creator.establishment_id == execution.establishment_id
    ):
        recipients.append(creator)
    return _dedupe_memberships(recipients)


def resolve_action_plan_execution_canceled_recipients(
    *,
    execution: ActionPlanExecution,
) -> list[EstablishmentMembership]:
    return resolve_action_plan_execution_reopened_recipients(execution=execution)


def resolve_comment_mention_recipients(
    *,
    comment: Comment,
) -> list[EstablishmentMembership]:
    recipients: list[EstablishmentMembership] = []
    for link in comment.mention_links.all():
        membership = link.mentioned_membership
        if (
            membership.status == EstablishmentMembership.Status.ACTIVE
            and membership.establishment_id == comment.establishment_id
        ):
            recipients.append(membership)
    return _dedupe_memberships(recipients)


def _signal_pole_business_unit_ids(signal: Signal) -> set[uuid.UUID]:
    bu_ids: set[uuid.UUID] = set()
    if signal.responsible_business_unit_id is not None:
        bu_ids.add(signal.responsible_business_unit_id)
    if (
        signal.affected_business_unit_id is not None
        and signal.affected_business_unit_id != signal.responsible_business_unit_id
    ):
        bu_ids.add(signal.affected_business_unit_id)
    return bu_ids


def resolve_signal_pole_recipients(*, signal: Signal) -> list[EstablishmentMembership]:
    bu_ids = _signal_pole_business_unit_ids(signal)
    if not bu_ids:
        return []
    return _dedupe_memberships(
        list(
            EstablishmentMembership.objects.filter(
                establishment_id=signal.establishment_id,
                status=EstablishmentMembership.Status.ACTIVE,
                scope_links__business_unit_id__in=bu_ids,
            )
            .select_related("user")
            .distinct()
        )
    )
