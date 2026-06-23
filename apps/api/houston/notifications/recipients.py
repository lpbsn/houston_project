from __future__ import annotations

import uuid

from houston.actions.models import Action, ActionAssignee
from houston.actions.permissions import can_validate_action_on_object
from houston.checklists.models import ChecklistExecution
from houston.comments.models import Comment
from houston.establishments.models import EstablishmentMembership


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


def _active_assignee_memberships(*, action: Action) -> list[EstablishmentMembership]:
    return list(
        EstablishmentMembership.objects.filter(
            action_assignments__action_id=action.id,
            establishment_id=action.establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
        ).select_related("user")
    )


def resolve_action_created_recipients(*, action: Action) -> list[EstablishmentMembership]:
    return _active_assignee_memberships(action=action)


def resolve_action_reassigned_recipient_groups(
    *,
    action: Action,
    previous_assignee_ids: set[uuid.UUID],
    new_assignee_ids: set[uuid.UUID],
) -> tuple[list[EstablishmentMembership], list[EstablishmentMembership]]:
    added_ids = new_assignee_ids - previous_assignee_ids
    removed_ids = previous_assignee_ids - new_assignee_ids
    if not added_ids and not removed_ids:
        return [], []

    memberships = {
        membership.id: membership
        for membership in EstablishmentMembership.objects.filter(
            id__in=added_ids | removed_ids,
            establishment_id=action.establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
        ).select_related("user")
    }
    added = [
        memberships[membership_id]
        for membership_id in added_ids
        if membership_id in memberships
    ]
    removed = [
        memberships[membership_id] for membership_id in removed_ids if membership_id in memberships
    ]
    return added, removed


def resolve_action_reassigned_recipients(
    *,
    action: Action,
    previous_assignee_ids: set[uuid.UUID],
    new_assignee_ids: set[uuid.UUID],
) -> list[EstablishmentMembership]:
    added, removed = resolve_action_reassigned_recipient_groups(
        action=action,
        previous_assignee_ids=previous_assignee_ids,
        new_assignee_ids=new_assignee_ids,
    )
    return _dedupe_memberships(added + removed)


def resolve_action_pending_validation_recipients(
    *,
    action: Action,
) -> list[EstablishmentMembership]:
    if action.status != Action.Status.PENDING_VALIDATION:
        return []

    validators: list[EstablishmentMembership] = []
    for membership in EstablishmentMembership.objects.filter(
        establishment_id=action.establishment_id,
        status=EstablishmentMembership.Status.ACTIVE,
    ).select_related("user"):
        if can_validate_action_on_object(membership, action):
            validators.append(membership)
    return validators


def resolve_action_reopened_recipients(*, action: Action) -> list[EstablishmentMembership]:
    recipients = _active_assignee_memberships(action=action)
    creator = action.created_by
    if (
        creator is not None
        and creator.status == EstablishmentMembership.Status.ACTIVE
        and creator.establishment_id == action.establishment_id
    ):
        recipients.append(creator)
    return _dedupe_memberships(recipients)


def resolve_action_canceled_recipients(*, action: Action) -> list[EstablishmentMembership]:
    return resolve_action_reopened_recipients(action=action)


def _active_execution_membership(
    membership: EstablishmentMembership | None,
    *,
    establishment_id: uuid.UUID,
) -> EstablishmentMembership | None:
    if membership is None:
        return None
    if (
        membership.status == EstablishmentMembership.Status.ACTIVE
        and membership.establishment_id == establishment_id
    ):
        return membership
    return None


def resolve_checklist_execution_created_recipients(
    *,
    execution: ChecklistExecution,
) -> list[EstablishmentMembership]:
    assignee = _active_execution_membership(
        execution.assigned_to,
        establishment_id=execution.establishment_id,
    )
    if assignee is None:
        return []
    return [assignee]


def resolve_checklist_execution_canceled_recipients(
    *,
    execution: ChecklistExecution,
) -> list[EstablishmentMembership]:
    recipients: list[EstablishmentMembership] = []
    assignee = _active_execution_membership(
        execution.assigned_to,
        establishment_id=execution.establishment_id,
    )
    if assignee is not None:
        recipients.append(assignee)
    assigner = _active_execution_membership(
        execution.assigned_by,
        establishment_id=execution.establishment_id,
    )
    if assigner is not None:
        recipients.append(assigner)
    return _dedupe_memberships(recipients)


def snapshot_action_assignee_ids(*, action_id: uuid.UUID) -> set[uuid.UUID]:
    return set(
        ActionAssignee.objects.filter(action_id=action_id).values_list(
            "membership_id",
            flat=True,
        )
    )


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
