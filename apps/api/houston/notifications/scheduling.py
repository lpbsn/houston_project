from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from django.db import transaction

from houston.actions.models import Action
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.recipients import (
    resolve_action_canceled_recipients,
    resolve_action_created_recipients,
    resolve_action_pending_validation_recipients,
    resolve_action_reassigned_recipient_groups,
    resolve_action_reopened_recipients,
)
from houston.notifications.services import create_in_app_notifications_for_recipients

logger = logging.getLogger(__name__)


def _run_notification_after_commit(*, deliver: Callable[[], None]) -> None:
    def _wrapped() -> None:
        try:
            deliver()
        except Exception:
            logger.exception("Failed to create in-app notification after business commit")

    transaction.on_commit(_wrapped)


def _load_action(*, action_id: uuid.UUID) -> Action | None:
    return (
        Action.objects.filter(id=action_id)
        .select_related("created_by", "accepted_by")
        .first()
    )


def _load_actor(
    *,
    establishment_id: uuid.UUID,
    actor_membership_id: uuid.UUID | None,
) -> EstablishmentMembership | None:
    if actor_membership_id is None:
        return None
    return (
        EstablishmentMembership.objects.filter(
            id=actor_membership_id,
            establishment_id=establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
        )
        .select_related("user")
        .first()
    )


def _deliver_action_notifications(
    *,
    action: Action,
    event_key: str,
    priority: str,
    recipients: list[EstablishmentMembership],
    actor_membership: EstablishmentMembership | None,
    exclude_actor_if_recipient: bool = True,
    skip_subject_visibility_recheck: bool = False,
) -> None:
    if not recipients:
        return
    create_in_app_notifications_for_recipients(
        establishment_id=action.establishment_id,
        recipient_memberships=recipients,
        event_key=event_key,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
        priority=priority,
        actor_membership=actor_membership,
        exclude_actor_if_recipient=exclude_actor_if_recipient,
        skip_subject_visibility_recheck=skip_subject_visibility_recheck,
    )


def schedule_action_created_notification(
    *,
    action_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
) -> None:
    def deliver() -> None:
        action = _load_action(action_id=action_id)
        if action is None:
            return
        recipients = resolve_action_created_recipients(action=action)
        _deliver_action_notifications(
            action=action,
            event_key=Notification.EventKey.ACTION_CREATED,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=action.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(deliver=deliver)


def schedule_action_reassigned_notification(
    *,
    action_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
    previous_assignee_ids: set[uuid.UUID],
    new_assignee_ids: set[uuid.UUID],
) -> None:
    frozen_previous = frozenset(previous_assignee_ids)
    frozen_new = frozenset(new_assignee_ids)

    def deliver() -> None:
        action = _load_action(action_id=action_id)
        if action is None:
            return
        added_recipients, removed_recipients = resolve_action_reassigned_recipient_groups(
            action=action,
            previous_assignee_ids=set(frozen_previous),
            new_assignee_ids=set(frozen_new),
        )
        actor = _load_actor(
            establishment_id=action.establishment_id,
            actor_membership_id=actor_membership_id,
        )
        _deliver_action_notifications(
            action=action,
            event_key=Notification.EventKey.ACTION_REASSIGNED,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=added_recipients,
            actor_membership=actor,
        )
        _deliver_action_notifications(
            action=action,
            event_key=Notification.EventKey.ACTION_REASSIGNED,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=removed_recipients,
            actor_membership=actor,
            skip_subject_visibility_recheck=True,
        )

    _run_notification_after_commit(deliver=deliver)


def schedule_action_pending_validation_notification(*, action_id: uuid.UUID) -> None:
    def deliver() -> None:
        action = _load_action(action_id=action_id)
        if action is None:
            return
        recipients = resolve_action_pending_validation_recipients(action=action)
        accepted_by = action.accepted_by
        _deliver_action_notifications(
            action=action,
            event_key=Notification.EventKey.ACTION_PENDING_VALIDATION,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=recipients,
            actor_membership=accepted_by,
        )

    _run_notification_after_commit(deliver=deliver)


def schedule_action_reopened_notification(
    *,
    action_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
) -> None:
    def deliver() -> None:
        action = _load_action(action_id=action_id)
        if action is None:
            return
        recipients = resolve_action_reopened_recipients(action=action)
        _deliver_action_notifications(
            action=action,
            event_key=Notification.EventKey.ACTION_REOPENED,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=action.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(deliver=deliver)


def schedule_action_canceled_notification(
    *,
    action_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
) -> None:
    def deliver() -> None:
        action = _load_action(action_id=action_id)
        if action is None:
            return
        recipients = resolve_action_canceled_recipients(action=action)
        _deliver_action_notifications(
            action=action,
            event_key=Notification.EventKey.ACTION_CANCELED,
            priority=Notification.Priority.INFO,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=action.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(deliver=deliver)
