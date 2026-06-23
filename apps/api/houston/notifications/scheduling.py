from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from django.db import transaction
from django.db.models import Prefetch

from houston.actions.models import Action
from houston.checklists.models import ChecklistExecution
from houston.comments.models import Comment, CommentMention
from houston.establishments.models import EstablishmentMembership
from houston.notifications.constants import (
    build_action_reassigned_dedupe_key,
    build_mention_dedupe_key,
)
from houston.notifications.models import Notification
from houston.notifications.recipients import (
    resolve_action_canceled_recipients,
    resolve_action_created_recipients,
    resolve_action_pending_validation_recipients,
    resolve_action_reassigned_recipient_groups,
    resolve_action_reopened_recipients,
    resolve_checklist_execution_canceled_recipients,
    resolve_checklist_execution_created_recipients,
    resolve_comment_mention_recipients,
    resolve_signal_pole_recipients,
)
from houston.notifications.services import (
    create_in_app_notification,
    create_in_app_notifications_for_recipients,
)
from houston.signals.models import Signal

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
    dedupe_key: str | None = None,
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
        dedupe_key=dedupe_key,
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
    # One uuid per schedule() call: dedupes accidental double-delivery of the
    # same on_commit callback (e.g. added + removed batches, or a retried deliver).
    # It does NOT dedupe two distinct reassign_action calls — each call gets its own uuid.
    reassignment_id = uuid.uuid4()
    dedupe_key = build_action_reassigned_dedupe_key(
        action_id=action_id,
        reassignment_id=reassignment_id,
    )

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
            dedupe_key=dedupe_key,
        )
        _deliver_action_notifications(
            action=action,
            event_key=Notification.EventKey.ACTION_REASSIGNED,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=removed_recipients,
            actor_membership=actor,
            skip_subject_visibility_recheck=True,
            dedupe_key=dedupe_key,
        )

    _run_notification_after_commit(deliver=deliver)


def schedule_action_pending_validation_notification(*, action_id: uuid.UUID) -> None:
    def deliver() -> None:
        action = _load_action(action_id=action_id)
        if action is None:
            return
        recipients = resolve_action_pending_validation_recipients(action=action)
        _deliver_action_notifications(
            action=action,
            event_key=Notification.EventKey.ACTION_PENDING_VALIDATION,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=action.establishment_id,
                actor_membership_id=action.accepted_by_id,
            ),
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


def _load_execution(*, execution_id: uuid.UUID) -> ChecklistExecution | None:
    return (
        ChecklistExecution.objects.filter(id=execution_id)
        .select_related("assigned_to", "assigned_by")
        .first()
    )


def _deliver_execution_notifications(
    *,
    execution: ChecklistExecution,
    event_key: str,
    priority: str,
    recipients: list[EstablishmentMembership],
    actor_membership: EstablishmentMembership | None,
    exclude_actor_if_recipient: bool = True,
) -> None:
    if not recipients:
        return
    create_in_app_notifications_for_recipients(
        establishment_id=execution.establishment_id,
        recipient_memberships=recipients,
        event_key=event_key,
        subject_type=Notification.SubjectType.CHECKLIST_EXECUTION,
        subject_id=execution.id,
        priority=priority,
        actor_membership=actor_membership,
        exclude_actor_if_recipient=exclude_actor_if_recipient,
    )


def schedule_checklist_execution_created_notification(
    *,
    execution_id: uuid.UUID,
    actor_membership_id: uuid.UUID | None,
) -> None:
    def deliver() -> None:
        execution = _load_execution(execution_id=execution_id)
        if execution is None:
            return
        recipients = resolve_checklist_execution_created_recipients(execution=execution)
        _deliver_execution_notifications(
            execution=execution,
            event_key=Notification.EventKey.CHECKLIST_EXECUTION_CREATED,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=execution.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(deliver=deliver)


def schedule_checklist_execution_canceled_notification(
    *,
    execution_id: uuid.UUID,
    actor_membership_id: uuid.UUID | None,
) -> None:
    def deliver() -> None:
        execution = _load_execution(execution_id=execution_id)
        if execution is None:
            return
        recipients = resolve_checklist_execution_canceled_recipients(execution=execution)
        _deliver_execution_notifications(
            execution=execution,
            event_key=Notification.EventKey.CHECKLIST_EXECUTION_CANCELED,
            priority=Notification.Priority.INFO,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=execution.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(deliver=deliver)


def _load_comment(*, comment_id: uuid.UUID) -> Comment | None:
    return (
        Comment.objects.filter(id=comment_id)
        .prefetch_related(
            Prefetch(
                "mention_links",
                queryset=CommentMention.objects.select_related(
                    "mentioned_membership__user",
                ).order_by("id"),
            )
        )
        .first()
    )


def _deliver_comment_mention_notifications(
    *,
    comment: Comment,
    actor_membership: EstablishmentMembership | None,
) -> None:
    recipients = resolve_comment_mention_recipients(comment=comment)
    for recipient in recipients:
        create_in_app_notification(
            establishment_id=comment.establishment_id,
            recipient_membership=recipient,
            event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
            subject_type=Notification.SubjectType.COMMENT,
            subject_id=comment.id,
            priority=Notification.Priority.INFO,
            actor_membership=actor_membership,
            dedupe_key=build_mention_dedupe_key(
                comment_id=comment.id,
                mentioned_membership_id=recipient.id,
            ),
        )


def schedule_comment_mention_created_notification(
    *,
    comment_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
) -> None:
    def deliver() -> None:
        comment = _load_comment(comment_id=comment_id)
        if comment is None:
            return
        _deliver_comment_mention_notifications(
            comment=comment,
            actor_membership=_load_actor(
                establishment_id=comment.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(deliver=deliver)


def _load_signal(*, signal_id: uuid.UUID) -> Signal | None:
    return (
        Signal.objects.filter(id=signal_id)
        .select_related("affected_business_unit", "responsible_business_unit")
        .first()
    )


def _deliver_signal_notifications(
    *,
    signal: Signal,
    event_key: str,
    priority: str,
    recipients: list[EstablishmentMembership],
    actor_membership: EstablishmentMembership | None,
    exclude_actor_if_recipient: bool = True,
) -> None:
    if not recipients:
        return
    create_in_app_notifications_for_recipients(
        establishment_id=signal.establishment_id,
        recipient_memberships=recipients,
        event_key=event_key,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=signal.id,
        priority=priority,
        actor_membership=actor_membership,
        exclude_actor_if_recipient=exclude_actor_if_recipient,
    )


def schedule_signal_created_notification(*, signal_id: uuid.UUID) -> None:
    def deliver() -> None:
        signal = _load_signal(signal_id=signal_id)
        if signal is None:
            return
        recipients = resolve_signal_pole_recipients(signal=signal)
        _deliver_signal_notifications(
            signal=signal,
            event_key=Notification.EventKey.SIGNAL_CREATED,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=recipients,
            actor_membership=None,
            exclude_actor_if_recipient=False,
        )

    _run_notification_after_commit(deliver=deliver)


def schedule_signal_urgency_changed_notification(
    *,
    signal_id: uuid.UUID,
    actor_membership_id: uuid.UUID | None,
) -> None:
    def deliver() -> None:
        signal = _load_signal(signal_id=signal_id)
        if signal is None:
            return
        recipients = resolve_signal_pole_recipients(signal=signal)
        _deliver_signal_notifications(
            signal=signal,
            event_key=Notification.EventKey.SIGNAL_URGENCY_CHANGED,
            priority=Notification.Priority.URGENT,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=signal.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(deliver=deliver)


def schedule_signal_pinned_notification(
    *,
    signal_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
) -> None:
    def deliver() -> None:
        signal = _load_signal(signal_id=signal_id)
        if signal is None:
            return
        recipients = resolve_signal_pole_recipients(signal=signal)
        _deliver_signal_notifications(
            signal=signal,
            event_key=Notification.EventKey.SIGNAL_PINNED,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=signal.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(deliver=deliver)


def schedule_signal_resolved_notification(
    *,
    signal_id: uuid.UUID,
    actor_membership_id: uuid.UUID | None,
) -> None:
    def deliver() -> None:
        signal = _load_signal(signal_id=signal_id)
        if signal is None:
            return
        recipients = resolve_signal_pole_recipients(signal=signal)
        _deliver_signal_notifications(
            signal=signal,
            event_key=Notification.EventKey.SIGNAL_RESOLVED,
            priority=Notification.Priority.INFO,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=signal.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
            exclude_actor_if_recipient=actor_membership_id is not None,
        )

    _run_notification_after_commit(deliver=deliver)


def schedule_signal_canceled_notification(
    *,
    signal_id: uuid.UUID,
    actor_membership_id: uuid.UUID | None,
) -> None:
    def deliver() -> None:
        signal = _load_signal(signal_id=signal_id)
        if signal is None:
            return
        recipients = resolve_signal_pole_recipients(signal=signal)
        _deliver_signal_notifications(
            signal=signal,
            event_key=Notification.EventKey.SIGNAL_CANCELED,
            priority=Notification.Priority.INFO,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=signal.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
            exclude_actor_if_recipient=actor_membership_id is not None,
        )

    _run_notification_after_commit(deliver=deliver)
