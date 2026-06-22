from __future__ import annotations

import uuid

from django.db import transaction
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import _is_valid_membership
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
    exclude_actor_if_recipient: bool = True,
) -> Notification | None:
    if event_key not in LOT1_EVENT_KEYS:
        raise NotificationValidationError("Invalid event_key.")

    if recipient_membership.establishment_id != establishment_id:
        raise NotificationValidationError("Invalid recipient membership.")

    if actor_membership is not None and (
        actor_membership.establishment_id != establishment_id
        or not _is_valid_membership(actor_membership)
    ):
        raise NotificationValidationError("Invalid actor membership.")

    if (
        exclude_actor_if_recipient
        and actor_membership is not None
        and actor_membership.id == recipient_membership.id
    ):
        return None

    if not recipient_can_view_notification_subject(
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

    if effective_dedupe_key:
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
    )

    return Notification.objects.create(
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
    )


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
    return Notification.objects.filter(
        establishment_id=establishment_id,
        recipient_membership_id=membership.id,
        status=Notification.Status.UNREAD,
    ).update(
        status=Notification.Status.READ,
        read_at=now,
        updated_at=now,
    )
