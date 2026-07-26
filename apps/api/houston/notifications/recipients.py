from __future__ import annotations

import uuid

from houston.action_plans.constants import EXECUTION_STATUS_PENDING_VALIDATION
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.permissions import can_validate_action_plan_execution
from houston.chat.models import ChatConversation
from houston.chat.permissions import can_access_chat
from houston.chat.selectors import active_participant_queryset
from houston.comments.models import Comment
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.signals.reporter_display import created_from_source_observation_link


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


def _active_membership_in_establishment(
    membership: EstablishmentMembership | None,
    *,
    establishment_id: uuid.UUID,
) -> EstablishmentMembership | None:
    if membership is None:
        return None
    if membership.status != EstablishmentMembership.Status.ACTIVE:
        return None
    if membership.establishment_id != establishment_id:
        return None
    return membership


def resolve_comment_signal_created_recipients(
    *,
    signal: Signal,
) -> list[EstablishmentMembership]:
    recipients: list[EstablishmentMembership] = []
    linked_executions = ActionPlanExecution.objects.filter(
        establishment_id=signal.establishment_id,
        source_signal_id=signal.id,
    ).prefetch_related("assignees__membership")
    for execution in linked_executions:
        recipients.extend(_active_action_plan_assignee_memberships(execution=execution))

    observation_link = created_from_source_observation_link(signal)
    if observation_link is not None:
        submitter = _active_membership_in_establishment(
            observation_link.observation.submitted_by_membership,
            establishment_id=signal.establishment_id,
        )
        if submitter is not None:
            recipients.append(submitter)

    return _dedupe_memberships(recipients)


def resolve_comment_action_plan_execution_created_recipients(
    *,
    execution: ActionPlanExecution,
) -> list[EstablishmentMembership]:
    return resolve_action_plan_execution_reopened_recipients(execution=execution)


def resolve_comment_reply_created_recipients(
    *,
    reply_comment: Comment,
) -> list[EstablishmentMembership]:
    if reply_comment.parent_comment_id is None:
        return []
    if reply_comment.action_plan_execution_id is None:
        return []

    root = reply_comment.parent_comment
    if root is None or root.parent_comment_id is not None:
        return []

    recipients: list[EstablishmentMembership] = []

    root_author = _active_membership_in_establishment(
        root.author_membership,
        establishment_id=reply_comment.establishment_id,
    )
    if root_author is not None:
        recipients.append(root_author)

    for sibling in root.replies.all():
        if sibling.id == reply_comment.id:
            continue
        author = _active_membership_in_establishment(
            sibling.author_membership,
            establishment_id=reply_comment.establishment_id,
        )
        if author is not None:
            recipients.append(author)

    for link in root.mention_links.all():
        mentioned = _active_membership_in_establishment(
            link.mentioned_membership,
            establishment_id=reply_comment.establishment_id,
        )
        if mentioned is not None:
            recipients.append(mentioned)

    return _dedupe_memberships(recipients)


def resolve_chat_message_recipients(
    *,
    conversation: ChatConversation,
    exclude_membership_id: uuid.UUID,
) -> list[EstablishmentMembership]:
    recipients: list[EstablishmentMembership] = []
    for participant in active_participant_queryset(conversation_id=conversation.id):
        membership = participant.membership
        if membership.id == exclude_membership_id:
            continue
        if membership.status != EstablishmentMembership.Status.ACTIVE:
            continue
        if membership.establishment_id != conversation.establishment_id:
            continue
        if not can_access_chat(membership):
            continue
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


def resolve_signal_triage_recipients(
    *,
    signal: Signal,
) -> list[EstablishmentMembership]:
    """Owner, Director, and Manager — establishment-wide triage (Lot 8 E1–E3)."""
    return _dedupe_memberships(
        list(
            EstablishmentMembership.objects.filter(
                establishment_id=signal.establishment_id,
                status=EstablishmentMembership.Status.ACTIVE,
                role__in={
                    EstablishmentMembership.Role.OWNER,
                    EstablishmentMembership.Role.DIRECTOR,
                    EstablishmentMembership.Role.MANAGER,
                },
            ).select_related("user")
        )
    )


def resolve_signal_unassigned_global_recipients(
    *,
    signal: Signal,
) -> list[EstablishmentMembership]:
    """Backward-compatible alias for triage recipients (admins + managers)."""
    return resolve_signal_triage_recipients(signal=signal)


def resolve_signal_attention_recipients(
    *,
    signal: Signal,
) -> list[EstablishmentMembership]:
    """Recipients for create / post-qualify attention based on current routing."""
    has_pole = (
        signal.affected_business_unit_id is not None
        or signal.responsible_business_unit_id is not None
    )
    triage = resolve_signal_triage_recipients(signal=signal)
    if not has_pole:
        return triage
    pole = resolve_signal_pole_recipients(signal=signal)
    # Lot 8 E2: any unassigned with identifiable poles → triage ∪ pole (deduped).
    # Resolved routing keeps pole-or-triage fallback (assigned create path).
    if signal.routing_status == Signal.RoutingStatus.UNASSIGNED:
        return _dedupe_memberships([*triage, *pole])
    return pole or triage
