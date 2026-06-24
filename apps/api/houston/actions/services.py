from __future__ import annotations

import uuid

from django.db import transaction
from django.utils import timezone

from houston.actions.action_classification import (
    classification_from_signal,
    resolve_responsible_business_unit,
)
from houston.actions.constants import (
    ACTION_INSTRUCTION_MAX_LENGTH,
    ACTION_TITLE_MAX_LENGTH,
    ACTIVE_ACTION_STATUSES,
    TERMINAL_ACTION_STATUSES,
)
from houston.actions.exceptions import (
    ActionPermissionError,
    ActionStateError,
    ActionValidationError,
)
from houston.actions.models import Action, ActionAssignee
from houston.actions.permissions import (
    can_create_free_action,
    can_create_linked_action,
    can_mark_action_done,
    can_validate_action_on_object,
)
from houston.establishments.models import EstablishmentMembership
from houston.notifications.recipients import snapshot_action_assignee_ids
from houston.notifications.scheduling import (
    schedule_action_canceled_notification,
    schedule_action_created_notification,
    schedule_action_pending_validation_notification,
    schedule_action_reassigned_notification,
    schedule_action_reopened_notification,
)
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES
from houston.signals.models import Signal
from houston.signals.services import touch_signal_activity, unpin_signal


def touch_action_activity(*, action: Action, at=None) -> None:
    action.last_activity_at = at or timezone.now()
    action.save(update_fields=["last_activity_at", "updated_at"])


def _validate_membership_in_establishment(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> EstablishmentMembership:
    membership = (
        EstablishmentMembership.objects.filter(
            id=membership_id,
            establishment_id=establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
        )
        .select_related("user", "establishment")
        .first()
    )
    if membership is None:
        raise ActionValidationError("Invalid assignee membership.")
    return membership


def _validate_assignee_ids(
    *,
    establishment_id: uuid.UUID,
    assignee_ids: list[uuid.UUID],
) -> list[EstablishmentMembership]:
    if not assignee_ids:
        raise ActionValidationError("At least one assignee is required.")
    if len(set(assignee_ids)) != len(assignee_ids):
        raise ActionValidationError("Duplicate assignees are not allowed.")

    memberships: list[EstablishmentMembership] = []
    for assignee_id in assignee_ids:
        memberships.append(
            _validate_membership_in_establishment(
                establishment_id=establishment_id,
                membership_id=assignee_id,
            )
        )
    return memberships


def _validate_staff_create_constraints(
    *,
    created_by: EstablishmentMembership,
    assignee_ids: list[uuid.UUID],
    signal_id: uuid.UUID | None,
) -> None:
    if created_by.role != EstablishmentMembership.Role.STAFF:
        return
    if signal_id is not None:
        raise ActionValidationError("Staff members cannot create linked actions.")
    if len(assignee_ids) != 1 or assignee_ids[0] != created_by.id:
        raise ActionValidationError(
            "Staff members can only create actions assigned to themselves."
        )


def _replace_action_assignees(
    *,
    action: Action,
    memberships: list[EstablishmentMembership],
) -> None:
    ActionAssignee.objects.filter(action_id=action.id).delete()
    ActionAssignee.objects.bulk_create(
        [
            ActionAssignee(action_id=action.id, membership=membership)
            for membership in memberships
        ]
    )


def _normalize_title(title: str) -> str:
    normalized = (title or "").strip()
    if not normalized:
        raise ActionValidationError("Title is required.")
    if len(normalized) > ACTION_TITLE_MAX_LENGTH:
        raise ActionValidationError("Title is too long.")
    return normalized


def _normalize_instruction(instruction: str) -> str:
    normalized = (instruction or "").strip()
    if not normalized:
        raise ActionValidationError("Instruction is required.")
    if len(normalized) > ACTION_INSTRUCTION_MAX_LENGTH:
        raise ActionValidationError("Instruction is too long.")
    return normalized


@transaction.atomic
def sync_signal_after_action_change(*, signal: Signal) -> Signal:
    linked = Action.objects.filter(signal_id=signal.id)
    active_exists = linked.filter(status__in=ACTIVE_ACTION_STATUSES).exists()
    if active_exists:
        return signal

    if linked.exclude(status__in=TERMINAL_ACTION_STATUSES).exists():
        return signal

    if linked.filter(status=Action.Status.DONE).exists():
        from houston.signals.services import resolve_signal

        return resolve_signal(signal=signal)

    if linked.filter(status=Action.Status.CANCELED).count() == linked.count():
        if signal.status in ACTIVE_SIGNAL_STATUSES:
            signal.status = Signal.Status.OPEN
            signal.is_pinned = False
            signal.pinned_at = None
            signal.pinned_by_membership = None
            touch_signal_activity(signal=signal)
            signal.save(
                update_fields=[
                    "status",
                    "is_pinned",
                    "pinned_at",
                    "pinned_by_membership",
                    "last_activity_at",
                    "updated_at",
                ]
            )
    return signal


@transaction.atomic
def create_action(
    *,
    establishment_id: uuid.UUID,
    created_by: EstablishmentMembership,
    title: str,
    instruction: str,
    assignee_ids: list[uuid.UUID],
    due_at,
    requires_validation: bool = True,
    signal_id: uuid.UUID | None = None,
    responsible_business_unit_id: uuid.UUID | None = None,
) -> Action:
    if signal_id is not None and responsible_business_unit_id is not None:
        raise ActionValidationError("Cannot provide both signal and responsible_business_unit_id.")
    if signal_id is None and responsible_business_unit_id is None:
        raise ActionValidationError("Either signal or responsible_business_unit_id is required.")

    assignees = _validate_assignee_ids(
        establishment_id=establishment_id,
        assignee_ids=assignee_ids,
    )
    _validate_staff_create_constraints(
        created_by=created_by,
        assignee_ids=assignee_ids,
        signal_id=signal_id,
    )
    now = timezone.now()

    if signal_id is not None:
        signal = (
            Signal.objects.filter(
                id=signal_id,
                establishment_id=establishment_id,
            )
            .select_related(
                "establishment",
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
            )
            .first()
        )
        if signal is None:
            raise ActionValidationError("Invalid signal.")
        if not can_create_linked_action(created_by, signal=signal):
            raise ActionValidationError("Not allowed to create this action.")

        classification = classification_from_signal(signal=signal)
        action = Action.objects.create(
            establishment_id=establishment_id,
            signal=signal,
            affected_business_unit=classification.affected_business_unit,
            responsible_business_unit=classification.responsible_business_unit,
            activity_subject=classification.activity_subject,
            title=_normalize_title(title),
            instruction=_normalize_instruction(instruction),
            status=Action.Status.OPEN,
            created_by=created_by,
            requires_validation=requires_validation,
            due_at=due_at,
            last_activity_at=now,
        )
        _replace_action_assignees(action=action, memberships=assignees)

        if signal.status == Signal.Status.OPEN:
            signal.status = Signal.Status.IN_PROGRESS
            touch_signal_activity(signal=signal)
            signal.save(update_fields=["status", "last_activity_at", "updated_at"])
        if signal.is_pinned:
            unpin_signal(signal=signal)

        _schedule_action_invalidation(action=action, reason="action.created")
        schedule_action_created_notification(
            action_id=action.id,
            actor_membership_id=created_by.id,
        )
        return action

    responsible_business_unit = resolve_responsible_business_unit(
        establishment_id=establishment_id,
        business_unit_id=responsible_business_unit_id,
    )
    if not can_create_free_action(
        created_by,
        business_unit=responsible_business_unit,
    ):
        raise ActionValidationError("Not allowed to create this action.")

    action = Action.objects.create(
        establishment_id=establishment_id,
        signal=None,
        affected_business_unit=None,
        responsible_business_unit=responsible_business_unit,
        activity_subject=None,
        title=_normalize_title(title),
        instruction=_normalize_instruction(instruction),
        status=Action.Status.OPEN,
        created_by=created_by,
        requires_validation=requires_validation,
        due_at=due_at,
        last_activity_at=now,
    )
    _replace_action_assignees(action=action, memberships=assignees)
    _schedule_action_invalidation(action=action, reason="action.created")
    schedule_action_created_notification(
        action_id=action.id,
        actor_membership_id=created_by.id,
    )
    return action


def _lock_action_for_transition(*, action_id: uuid.UUID) -> Action:
    return Action.objects.select_for_update().get(pk=action_id)


def _assert_assignee_membership(*, action_id: uuid.UUID, membership_id: uuid.UUID) -> None:
    if not ActionAssignee.objects.filter(
        action_id=action_id,
        membership_id=membership_id,
    ).exists():
        raise ActionStateError("Action cannot be accepted in its current state.")


@transaction.atomic
def accept_action(
    *,
    action_id: uuid.UUID,
    accepted_by: EstablishmentMembership,
) -> Action:
    action = _lock_action_for_transition(action_id=action_id)
    if action.status not in {Action.Status.OPEN, Action.Status.REOPENED}:
        raise ActionStateError("Action cannot be accepted in its current state.")
    _assert_assignee_membership(action_id=action.id, membership_id=accepted_by.id)

    now = timezone.now()
    action.status = Action.Status.IN_PROGRESS
    action.accepted_by = accepted_by
    action.accepted_at = now
    action.last_activity_at = now
    action.save(
        update_fields=[
            "status",
            "accepted_by",
            "accepted_at",
            "last_activity_at",
            "updated_at",
        ]
    )
    _schedule_action_invalidation(action=action, reason="action.updated")
    return action


@transaction.atomic
def mark_action_done(
    *,
    action_id: uuid.UUID,
    actor_membership: EstablishmentMembership,
) -> Action:
    action = _lock_action_for_transition(action_id=action_id)
    if action.status != Action.Status.IN_PROGRESS:
        raise ActionStateError("Action cannot be marked done in its current state.")
    if not can_mark_action_done(actor_membership, action):
        raise ActionPermissionError("Not allowed to mark this action done.")
    now = timezone.now()
    action.marked_done_at = now
    action.last_activity_at = now

    if action.requires_validation:
        action.status = Action.Status.PENDING_VALIDATION
        action.save(
            update_fields=[
                "status",
                "marked_done_at",
                "last_activity_at",
                "updated_at",
            ]
        )
        if action.signal_id is not None:
            signal = Signal.objects.get(pk=action.signal_id)
            touch_signal_activity(signal=signal)
        _schedule_action_invalidation(action=action, reason="action.updated")
        schedule_action_pending_validation_notification(action_id=action.id)
        return action

    action.status = Action.Status.DONE
    action.save(
        update_fields=[
            "status",
            "marked_done_at",
            "last_activity_at",
            "updated_at",
        ]
    )
    if action.signal_id is not None:
        sync_signal_after_action_change(signal=action.signal)
    _schedule_action_invalidation(action=action, reason="action.updated")
    return action


@transaction.atomic
def validate_action(
    *,
    action_id: uuid.UUID,
    actor_membership: EstablishmentMembership,
) -> Action:
    action = _lock_action_for_transition(action_id=action_id)
    if action.status != Action.Status.PENDING_VALIDATION:
        raise ActionStateError("Action cannot be validated in its current state.")
    if not can_validate_action_on_object(actor_membership, action):
        raise ActionPermissionError("Not allowed to validate this action.")
    now = timezone.now()
    action.status = Action.Status.DONE
    action.validated_at = now
    action.last_activity_at = now
    action.save(update_fields=["status", "validated_at", "last_activity_at", "updated_at"])
    if action.signal_id is not None:
        sync_signal_after_action_change(signal=action.signal)
    _schedule_action_invalidation(action=action, reason="action.updated")
    return action


@transaction.atomic
def reopen_action(
    *,
    action_id: uuid.UUID,
    actor: EstablishmentMembership,
) -> Action:
    action = _lock_action_for_transition(action_id=action_id)
    if action.status not in {Action.Status.PENDING_VALIDATION, Action.Status.DONE}:
        raise ActionStateError("Action cannot be reopened in its current state.")
    action.status = Action.Status.REOPENED
    action.accepted_by = None
    action.accepted_at = None
    touch_action_activity(action=action)
    action.save(
        update_fields=[
            "status",
            "accepted_by",
            "accepted_at",
            "last_activity_at",
            "updated_at",
        ]
    )
    if action.signal_id is not None:
        signal = action.signal
        if signal.status == Signal.Status.RESOLVED:
            signal.status = Signal.Status.IN_PROGRESS
            touch_signal_activity(signal=signal)
            signal.save(update_fields=["status", "last_activity_at", "updated_at"])
    _schedule_action_invalidation(action=action, reason="action.updated")
    schedule_action_reopened_notification(
        action_id=action.id,
        actor_membership_id=actor.id,
    )
    return action


@transaction.atomic
def cancel_action(
    *,
    action_id: uuid.UUID,
    actor: EstablishmentMembership,
) -> Action:
    action = _lock_action_for_transition(action_id=action_id)
    if action.status not in ACTIVE_ACTION_STATUSES:
        raise ActionStateError("Action cannot be canceled in its current state.")
    action.status = Action.Status.CANCELED
    touch_action_activity(action=action)
    action.save(update_fields=["status", "last_activity_at", "updated_at"])
    if action.signal_id is not None:
        sync_signal_after_action_change(signal=action.signal)
    _schedule_action_invalidation(action=action, reason="action.updated")
    schedule_action_canceled_notification(
        action_id=action.id,
        actor_membership_id=actor.id,
    )
    return action


@transaction.atomic
def reassign_action(
    *,
    action_id: uuid.UUID,
    assignee_ids: list[uuid.UUID],
    actor: EstablishmentMembership,
) -> Action:
    action = _lock_action_for_transition(action_id=action_id)
    if action.status in {
        Action.Status.PENDING_VALIDATION,
        Action.Status.DONE,
        Action.Status.CANCELED,
    }:
        raise ActionStateError("Action cannot be reassigned in its current state.")

    assignees = _validate_assignee_ids(
        establishment_id=action.establishment_id,
        assignee_ids=assignee_ids,
    )
    previous_assignee_ids = snapshot_action_assignee_ids(action_id=action.id)
    new_assignee_ids = {membership.id for membership in assignees}
    _replace_action_assignees(action=action, memberships=assignees)

    update_fields = ["last_activity_at", "updated_at"]
    if action.status == Action.Status.IN_PROGRESS:
        action.status = Action.Status.OPEN
        action.accepted_by = None
        action.accepted_at = None
        update_fields.extend(["status", "accepted_by", "accepted_at"])

    touch_action_activity(action=action)
    action.save(update_fields=update_fields)
    _schedule_action_invalidation(action=action, reason="action.updated")
    schedule_action_reassigned_notification(
        action_id=action.id,
        actor_membership_id=actor.id,
        previous_assignee_ids=previous_assignee_ids,
        new_assignee_ids=new_assignee_ids,
    )
    return action


@transaction.atomic
def update_action_due_at(*, action_id: uuid.UUID, due_at) -> Action:
    action = _lock_action_for_transition(action_id=action_id)
    if action.status in {Action.Status.DONE, Action.Status.CANCELED}:
        raise ActionStateError("Due date cannot be updated in the current state.")
    action.due_at = due_at
    touch_action_activity(action=action)
    action.save(update_fields=["due_at", "last_activity_at", "updated_at"])
    _schedule_action_invalidation(action=action, reason="action.updated")
    return action


def _schedule_action_invalidation(*, action: Action, reason: str) -> None:
    from houston.realtime.broadcast import schedule_establishment_invalidation

    schedule_establishment_invalidation(
        establishment_id=action.establishment_id,
        subject_type="action",
        reason=reason,
        entity_id=action.id,
    )
