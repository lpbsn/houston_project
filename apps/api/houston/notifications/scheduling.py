from __future__ import annotations

import logging
import uuid
from collections.abc import Callable

from django.db import transaction
from django.db.models import Prefetch

from houston.action_plans.models import ActionPlanExecution
from houston.chat.models import ChatMessage
from houston.comments.models import Comment, CommentMention
from houston.establishments.models import EstablishmentMembership
from houston.notifications.constants import (
    build_chat_message_dedupe_key,
    build_mention_dedupe_key,
)
from houston.notifications.models import Notification
from houston.notifications.recipients import (
    resolve_action_plan_execution_canceled_recipients,
    resolve_action_plan_execution_created_recipients,
    resolve_action_plan_execution_pending_validation_recipients,
    resolve_action_plan_execution_reopened_recipients,
    resolve_chat_message_recipients,
    resolve_comment_action_plan_execution_created_recipients,
    resolve_comment_mention_recipients,
    resolve_comment_reply_created_recipients,
    resolve_comment_signal_created_recipients,
    resolve_signal_pole_recipients,
    resolve_signal_unassigned_global_recipients,
)
from houston.notifications.services import (
    create_in_app_notification,
    create_in_app_notifications_for_recipients,
)
from houston.signals.models import Signal, SignalSourceObservation

logger = logging.getLogger(__name__)


def _run_notification_after_commit(
    *,
    deliver: Callable[[], None],
    event_key: str | None = None,
    subject_type: str | None = None,
    subject_id: uuid.UUID | None = None,
) -> None:
    def _wrapped() -> None:
        try:
            deliver()
        except Exception:
            extra: dict[str, str] = {}
            if event_key is not None:
                extra["event_key"] = event_key
            if subject_type is not None:
                extra["subject_type"] = subject_type
            if subject_id is not None:
                extra["subject_id"] = str(subject_id)
            logger.exception(
                "Failed to create in-app notification after business commit",
                extra=extra,
            )

    transaction.on_commit(_wrapped)


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


def _load_action_plan_execution(*, execution_id: uuid.UUID) -> ActionPlanExecution | None:
    return (
        ActionPlanExecution.objects.filter(id=execution_id)
        .select_related("created_by")
        .prefetch_related("assignees__membership")
        .first()
    )


def _resolve_execution_created_event_key(*, execution: ActionPlanExecution) -> str:
    if execution.source_signal_id is not None:
        return Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED_FROM_SIGNAL
    return Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED


def _deliver_action_plan_execution_notifications(
    *,
    execution: ActionPlanExecution,
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
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution.id,
        priority=priority,
        actor_membership=actor_membership,
        exclude_actor_if_recipient=exclude_actor_if_recipient,
    )


def schedule_action_plan_execution_created_notification(
    *,
    execution_id: uuid.UUID,
    actor_membership_id: uuid.UUID | None,
) -> None:
    def deliver() -> None:
        execution = _load_action_plan_execution(execution_id=execution_id)
        if execution is None:
            return
        event_key = _resolve_execution_created_event_key(execution=execution)
        recipients = resolve_action_plan_execution_created_recipients(execution=execution)
        _deliver_action_plan_execution_notifications(
            execution=execution,
            event_key=event_key,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=execution.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    log_event_key = (
        Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED_FROM_SIGNAL
        if ActionPlanExecution.objects.filter(
            id=execution_id,
            source_signal_id__isnull=False,
        ).exists()
        else Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED
    )
    _run_notification_after_commit(
        deliver=deliver,
        event_key=log_event_key,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution_id,
    )


def schedule_action_plan_execution_pending_validation_notification(
    *,
    execution_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
) -> None:
    def deliver() -> None:
        execution = _load_action_plan_execution(execution_id=execution_id)
        if execution is None:
            return
        recipients = resolve_action_plan_execution_pending_validation_recipients(
            execution=execution,
        )
        _deliver_action_plan_execution_notifications(
            execution=execution,
            event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_PENDING_VALIDATION,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=execution.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_PENDING_VALIDATION,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution_id,
    )


def schedule_action_plan_execution_canceled_notification(
    *,
    execution_id: uuid.UUID,
    actor_membership_id: uuid.UUID | None,
) -> None:
    def deliver() -> None:
        execution = _load_action_plan_execution(execution_id=execution_id)
        if execution is None:
            return
        recipients = resolve_action_plan_execution_canceled_recipients(execution=execution)
        _deliver_action_plan_execution_notifications(
            execution=execution,
            event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_CANCELED,
            priority=Notification.Priority.INFO,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=execution.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_CANCELED,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution_id,
    )


def schedule_action_plan_execution_reopened_notification(
    *,
    execution_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
) -> None:
    def deliver() -> None:
        execution = _load_action_plan_execution(execution_id=execution_id)
        if execution is None:
            return
        recipients = resolve_action_plan_execution_reopened_recipients(execution=execution)
        _deliver_action_plan_execution_notifications(
            execution=execution,
            event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_REOPENED,
            priority=Notification.Priority.ACTION_REQUIRED,
            recipients=recipients,
            actor_membership=_load_actor(
                establishment_id=execution.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_REOPENED,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution_id,
    )


def _load_comment(*, comment_id: uuid.UUID) -> Comment | None:
    return (
        Comment.objects.filter(id=comment_id)
        .select_related(
            "signal",
            "action_plan_execution__created_by",
            "parent_comment__author_membership",
        )
        .prefetch_related(
            Prefetch(
                "mention_links",
                queryset=CommentMention.objects.select_related(
                    "mentioned_membership__user",
                ).order_by("id"),
            ),
            Prefetch(
                "parent_comment__mention_links",
                queryset=CommentMention.objects.select_related(
                    "mentioned_membership__user",
                ).order_by("id"),
            ),
            Prefetch(
                "parent_comment__replies",
                queryset=Comment.objects.select_related("author_membership").order_by(
                    "created_at",
                    "id",
                ),
            ),
            "action_plan_execution__assignees__membership",
        )
        .first()
    )


def _exclude_membership_ids(
    recipients: list[EstablishmentMembership],
    exclude_ids: set[uuid.UUID],
) -> list[EstablishmentMembership]:
    if not exclude_ids:
        return recipients
    return [recipient for recipient in recipients if recipient.id not in exclude_ids]


def _deliver_comment_notifications(
    *,
    comment: Comment,
    event_key: str,
    recipients: list[EstablishmentMembership],
    actor_membership: EstablishmentMembership | None,
) -> None:
    for recipient in recipients:
        create_in_app_notification(
            establishment_id=comment.establishment_id,
            recipient_membership=recipient,
            event_key=event_key,
            subject_type=Notification.SubjectType.COMMENT,
            subject_id=comment.id,
            priority=Notification.Priority.INFO,
            actor_membership=actor_membership,
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

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=comment_id,
    )


def _load_signal_for_comment(*, signal_id: uuid.UUID) -> Signal | None:
    return (
        Signal.objects.filter(id=signal_id)
        .prefetch_related(
            Prefetch(
                "source_observation_links",
                queryset=SignalSourceObservation.objects.filter(
                    link_type=SignalSourceObservation.LinkType.CREATED_FROM,
                )
                .select_related("observation__submitted_by_membership")
                .order_by("observation__created_at", "observation__id"),
                to_attr="created_from_source_links",
            ),
        )
        .first()
    )


def _deliver_comment_signal_created_notifications(
    *,
    comment: Comment,
    actor_membership: EstablishmentMembership | None,
    exclude_mentioned_membership_ids: set[uuid.UUID],
) -> None:
    if comment.signal_id is None:
        return
    signal = _load_signal_for_comment(signal_id=comment.signal_id)
    if signal is None:
        return
    recipients = _exclude_membership_ids(
        resolve_comment_signal_created_recipients(signal=signal),
        exclude_mentioned_membership_ids,
    )
    _deliver_comment_notifications(
        comment=comment,
        event_key=Notification.EventKey.COMMENT_SIGNAL_CREATED,
        recipients=recipients,
        actor_membership=actor_membership,
    )


def schedule_comment_signal_created_notification(
    *,
    comment_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
    exclude_mentioned_membership_ids: set[uuid.UUID] | frozenset[uuid.UUID] = frozenset(),
) -> None:
    def deliver() -> None:
        comment = _load_comment(comment_id=comment_id)
        if comment is None:
            return
        _deliver_comment_signal_created_notifications(
            comment=comment,
            actor_membership=_load_actor(
                establishment_id=comment.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
            exclude_mentioned_membership_ids=set(exclude_mentioned_membership_ids),
        )

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.COMMENT_SIGNAL_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=comment_id,
    )


def _deliver_comment_action_plan_execution_created_notifications(
    *,
    comment: Comment,
    actor_membership: EstablishmentMembership | None,
    exclude_mentioned_membership_ids: set[uuid.UUID],
) -> None:
    if comment.action_plan_execution_id is None:
        return
    execution = comment.action_plan_execution
    if execution is None:
        return
    recipients = _exclude_membership_ids(
        resolve_comment_action_plan_execution_created_recipients(execution=execution),
        exclude_mentioned_membership_ids,
    )
    _deliver_comment_notifications(
        comment=comment,
        event_key=Notification.EventKey.COMMENT_ACTION_PLAN_EXECUTION_CREATED,
        recipients=recipients,
        actor_membership=actor_membership,
    )


def schedule_comment_action_plan_execution_created_notification(
    *,
    comment_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
    exclude_mentioned_membership_ids: set[uuid.UUID] | frozenset[uuid.UUID] = frozenset(),
) -> None:
    def deliver() -> None:
        comment = _load_comment(comment_id=comment_id)
        if comment is None:
            return
        _deliver_comment_action_plan_execution_created_notifications(
            comment=comment,
            actor_membership=_load_actor(
                establishment_id=comment.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
            exclude_mentioned_membership_ids=set(exclude_mentioned_membership_ids),
        )

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.COMMENT_ACTION_PLAN_EXECUTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=comment_id,
    )


def _deliver_comment_reply_created_notifications(
    *,
    comment: Comment,
    actor_membership: EstablishmentMembership | None,
    exclude_mentioned_membership_ids: set[uuid.UUID],
) -> None:
    recipients = _exclude_membership_ids(
        resolve_comment_reply_created_recipients(reply_comment=comment),
        exclude_mentioned_membership_ids,
    )
    _deliver_comment_notifications(
        comment=comment,
        event_key=Notification.EventKey.COMMENT_REPLY_CREATED,
        recipients=recipients,
        actor_membership=actor_membership,
    )


def schedule_comment_reply_created_notification(
    *,
    comment_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
    exclude_mentioned_membership_ids: set[uuid.UUID] | frozenset[uuid.UUID] = frozenset(),
) -> None:
    def deliver() -> None:
        comment = _load_comment(comment_id=comment_id)
        if comment is None:
            return
        _deliver_comment_reply_created_notifications(
            comment=comment,
            actor_membership=_load_actor(
                establishment_id=comment.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
            exclude_mentioned_membership_ids=set(exclude_mentioned_membership_ids),
        )

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.COMMENT_REPLY_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=comment_id,
    )


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
        pole_recipients = resolve_signal_pole_recipients(signal=signal)
        if pole_recipients:
            _deliver_signal_notifications(
                signal=signal,
                event_key=Notification.EventKey.SIGNAL_CREATED,
                priority=Notification.Priority.ACTION_REQUIRED,
                recipients=pole_recipients,
                actor_membership=None,
                exclude_actor_if_recipient=False,
            )
        else:
            _deliver_signal_notifications(
                signal=signal,
                event_key=Notification.EventKey.SIGNAL_CREATED_UNASSIGNED_GLOBAL,
                priority=Notification.Priority.ACTION_REQUIRED,
                recipients=resolve_signal_unassigned_global_recipients(signal=signal),
                actor_membership=None,
                exclude_actor_if_recipient=False,
            )

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.SIGNAL_CREATED,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=signal_id,
    )


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

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.SIGNAL_URGENCY_CHANGED,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=signal_id,
    )


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

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.SIGNAL_PINNED,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=signal_id,
    )


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

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.SIGNAL_RESOLVED,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=signal_id,
    )


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

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.SIGNAL_CANCELED,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=signal_id,
    )


def _load_chat_message(*, message_id: uuid.UUID) -> ChatMessage | None:
    return (
        ChatMessage.objects.filter(id=message_id)
        .select_related("conversation", "author_membership", "author_membership__user")
        .first()
    )


def _deliver_chat_message_notifications(
    *,
    message: ChatMessage,
    actor_membership: EstablishmentMembership | None,
) -> None:
    if actor_membership is None:
        return
    recipients = resolve_chat_message_recipients(
        conversation=message.conversation,
        exclude_membership_id=actor_membership.id,
    )
    for recipient in recipients:
        create_in_app_notification(
            establishment_id=message.conversation.establishment_id,
            recipient_membership=recipient,
            event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
            subject_type=Notification.SubjectType.CHAT_CONVERSATION,
            subject_id=message.conversation_id,
            priority=Notification.Priority.INFO,
            actor_membership=actor_membership,
            dedupe_key=build_chat_message_dedupe_key(
                conversation_id=message.conversation_id,
                recipient_membership_id=recipient.id,
                actor_membership_id=actor_membership.id,
            ),
        )


def schedule_chat_message_received_notification(
    *,
    message_id: uuid.UUID,
    actor_membership_id: uuid.UUID,
) -> None:
    conversation_id = (
        ChatMessage.objects.filter(id=message_id)
        .values_list("conversation_id", flat=True)
        .first()
    )
    if conversation_id is None:
        return

    def deliver() -> None:
        message = _load_chat_message(message_id=message_id)
        if message is None:
            return
        _deliver_chat_message_notifications(
            message=message,
            actor_membership=_load_actor(
                establishment_id=message.conversation.establishment_id,
                actor_membership_id=actor_membership_id,
            ),
        )

    _run_notification_after_commit(
        deliver=deliver,
        event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
        subject_type=Notification.SubjectType.CHAT_CONVERSATION,
        subject_id=conversation_id,
    )
