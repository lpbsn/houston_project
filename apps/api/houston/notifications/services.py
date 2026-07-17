from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import is_valid_membership
from houston.notifications.constants import (
    DEDUPE_WINDOW,
    LOT1_EVENT_KEYS,
    build_default_dedupe_key,
    render_notification_copy,
)
from houston.notifications.exceptions import NotificationValidationError
from houston.notifications.models import Notification
from houston.notifications.permissions import recipient_can_view_notification_subject
from houston.notifications.selectors import get_notification_for_recipient
from houston.realtime.operational_invalidation_events import (
    NOTIFICATION_BULK_UPDATED_REASON,
    NOTIFICATION_CREATED_REASON,
    NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
    NOTIFICATION_UPDATED_REASON,
)

logger = logging.getLogger(__name__)


def _schedule_notification_invalidation(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
    reason: str,
    entity_id: uuid.UUID,
) -> None:
    from houston.realtime.broadcast import schedule_membership_invalidation

    schedule_membership_invalidation(
        establishment_id=establishment_id,
        membership_id=membership_id,
        subject_type=NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
        reason=reason,
        entity_id=entity_id,
    )


def _membership_display_name(membership: EstablishmentMembership | None) -> str | None:
    if membership is None:
        return None
    user = membership.user
    return user.get_full_name() or user.email or user.username


def _is_duplicate_notification(
    *,
    recipient_membership_id: uuid.UUID,
    dedupe_key: str,
) -> bool:
    if not dedupe_key:
        return False
    cutoff = timezone.now() - DEDUPE_WINDOW
    return Notification.objects.filter(
        recipient_membership_id=recipient_membership_id,
        dedupe_key=dedupe_key,
        created_at__gte=cutoff,
    ).exists()


@transaction.atomic
def create_in_app_notification(
    *,
    establishment_id: uuid.UUID,
    recipient_membership: EstablishmentMembership,
    event_key: str,
    subject_type: str,
    subject_id: uuid.UUID,
    priority: str,
    actor_membership: EstablishmentMembership | None = None,
    dedupe_key: str | None = None,
    idempotency_key: str | None = None,
    exclude_actor_if_recipient: bool = True,
    skip_subject_visibility_recheck: bool = False,
    pole_name: str | None = None,
) -> Notification | None:
    if event_key not in LOT1_EVENT_KEYS:
        raise NotificationValidationError("Invalid event_key.")

    if recipient_membership.establishment_id != establishment_id:
        raise NotificationValidationError("Invalid recipient membership.")

    if actor_membership is not None and (
        actor_membership.establishment_id != establishment_id
        or not is_valid_membership(actor_membership)
    ):
        raise NotificationValidationError("Invalid actor membership.")

    if (
        exclude_actor_if_recipient
        and actor_membership is not None
        and actor_membership.id == recipient_membership.id
    ):
        return None

    if not recipient_membership.notifications_enabled:
        return None

    if not skip_subject_visibility_recheck and not recipient_can_view_notification_subject(
        recipient=recipient_membership,
        establishment_id=establishment_id,
        subject_type=subject_type,
        subject_id=subject_id,
    ):
        return None

    effective_dedupe_key = dedupe_key or build_default_dedupe_key(
        event_key=event_key,
        subject_type=subject_type,
        subject_id=subject_id,
    )

    if effective_dedupe_key and not idempotency_key:
        EstablishmentMembership.objects.select_for_update().get(
            pk=recipient_membership.pk,
            establishment_id=establishment_id,
        )
        if _is_duplicate_notification(
            recipient_membership_id=recipient_membership.id,
            dedupe_key=effective_dedupe_key,
        ):
            return None

    title, body = render_notification_copy(
        event_key,
        actor_display_name=_membership_display_name(actor_membership),
        pole_name=pole_name,
    )

    try:
        notification = Notification.objects.create(
            establishment_id=establishment_id,
            recipient_membership=recipient_membership,
            actor_membership=actor_membership,
            event_key=event_key,
            subject_type=subject_type,
            subject_id=subject_id,
            priority=priority,
            status=Notification.Status.UNREAD,
            title=title,
            body=body,
            dedupe_key=effective_dedupe_key,
            idempotency_key=idempotency_key or "",
        )
    except IntegrityError:
        if idempotency_key:
            return None
        raise
    _schedule_notification_invalidation(
        establishment_id=establishment_id,
        membership_id=recipient_membership.id,
        reason=NOTIFICATION_CREATED_REASON,
        entity_id=notification.id,
    )
    if settings.HOUSTON_PUSH_ENABLED:
        notification_id = notification.id

        def _enqueue_push_task() -> None:
            from houston.notifications.push.tasks import send_push_for_notification_task

            try:
                send_push_for_notification_task.delay(str(notification_id))
            except Exception:
                logger.exception(
                    "push_notification_enqueue_failed",
                    extra={
                        "event": "push_notification_enqueue_failed",
                        "notification_id": str(notification_id),
                    },
                )

        transaction.on_commit(_enqueue_push_task)
    return notification


@transaction.atomic
def create_in_app_notifications_for_recipients(
    *,
    establishment_id: uuid.UUID,
    recipient_memberships: list[EstablishmentMembership],
    event_key: str,
    subject_type: str,
    subject_id: uuid.UUID,
    priority: str,
    actor_membership: EstablishmentMembership | None = None,
    dedupe_key: str | None = None,
    exclude_actor_if_recipient: bool = True,
    skip_subject_visibility_recheck: bool = False,
    pole_name: str | None = None,
) -> list[Notification]:
    seen_recipient_ids: set[uuid.UUID] = set()
    created: list[Notification] = []

    for recipient in recipient_memberships:
        if recipient.id in seen_recipient_ids:
            continue
        seen_recipient_ids.add(recipient.id)

        notification = create_in_app_notification(
            establishment_id=establishment_id,
            recipient_membership=recipient,
            event_key=event_key,
            subject_type=subject_type,
            subject_id=subject_id,
            priority=priority,
            actor_membership=actor_membership,
            dedupe_key=dedupe_key,
            exclude_actor_if_recipient=exclude_actor_if_recipient,
            skip_subject_visibility_recheck=skip_subject_visibility_recheck,
            pole_name=pole_name,
        )
        if notification is not None:
            created.append(notification)

    return created


@transaction.atomic
def mark_notification_read(
    *,
    membership: EstablishmentMembership,
    notification_id: uuid.UUID,
) -> Notification | None:
    notification = get_notification_for_recipient(
        membership=membership,
        notification_id=notification_id,
    )
    if notification is None:
        return None

    if notification.status == Notification.Status.UNREAD:
        now = timezone.now()
        notification.status = Notification.Status.READ
        notification.read_at = now
        notification.save(update_fields=["status", "read_at", "updated_at"])
        _schedule_notification_invalidation(
            establishment_id=notification.establishment_id,
            membership_id=membership.id,
            reason=NOTIFICATION_UPDATED_REASON,
            entity_id=notification.id,
        )

    return notification


@transaction.atomic
def archive_notification(
    *,
    membership: EstablishmentMembership,
    notification_id: uuid.UUID,
) -> Notification | None:
    notification = get_notification_for_recipient(
        membership=membership,
        notification_id=notification_id,
    )
    if notification is None:
        return None

    if notification.status == Notification.Status.ARCHIVED:
        return notification

    now = timezone.now()
    notification.status = Notification.Status.ARCHIVED
    notification.archived_at = now
    if notification.read_at is None:
        notification.read_at = now
    notification.save(
        update_fields=["status", "archived_at", "read_at", "updated_at"],
    )
    _schedule_notification_invalidation(
        establishment_id=notification.establishment_id,
        membership_id=membership.id,
        reason=NOTIFICATION_UPDATED_REASON,
        entity_id=notification.id,
    )
    return notification


@transaction.atomic
def mark_all_notifications_read(
    *,
    membership: EstablishmentMembership,
    establishment_id: uuid.UUID,
) -> int:
    if membership.establishment_id != establishment_id:
        return 0

    now = timezone.now()
    updated_count = Notification.objects.filter(
        establishment_id=establishment_id,
        recipient_membership_id=membership.id,
        status=Notification.Status.UNREAD,
    ).update(
        status=Notification.Status.READ,
        read_at=now,
        updated_at=now,
    )
    if updated_count > 0:
        _schedule_notification_invalidation(
            establishment_id=establishment_id,
            membership_id=membership.id,
            reason=NOTIFICATION_BULK_UPDATED_REASON,
            entity_id=membership.id,
        )
    return updated_count


def get_notification_preferences(*, membership: EstablishmentMembership) -> dict:
    return {
        "notifications_enabled": membership.notifications_enabled,
        "push_enabled": membership.push_enabled,
    }


@transaction.atomic
def update_notification_preferences(
    *,
    membership: EstablishmentMembership,
    notifications_enabled: bool | None = None,
    push_enabled: bool | None = None,
) -> dict:
    update_fields: list[str] = []

    if (
        notifications_enabled is not None
        and membership.notifications_enabled != notifications_enabled
    ):
        membership.notifications_enabled = notifications_enabled
        update_fields.append("notifications_enabled")
        if not notifications_enabled:
            if membership.push_enabled:
                membership.push_enabled = False
                update_fields.append("push_enabled")

    if push_enabled is not None and membership.push_enabled != push_enabled:
        effective_push_enabled = push_enabled
        if not membership.notifications_enabled:
            effective_push_enabled = False
        if membership.push_enabled != effective_push_enabled:
            membership.push_enabled = effective_push_enabled
            if "push_enabled" not in update_fields:
                update_fields.append("push_enabled")

    if update_fields:
        update_fields.append("updated_at")
        membership.save(update_fields=update_fields)

    return get_notification_preferences(membership=membership)
