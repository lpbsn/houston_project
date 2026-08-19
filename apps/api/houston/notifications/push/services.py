from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.chat.presence import is_chat_presence_active
from houston.notifications.models import Notification, PushDelivery, PushDevice
from houston.notifications.permissions import recipient_can_view_notification_subject
from houston.notifications.push import constants as push_constants
from houston.notifications.push.chat_guards import (
    claim_chat_push_throttle,
    release_chat_push_throttle,
)
from houston.notifications.push.exceptions import FcmSendError
from houston.notifications.push.payloads import build_push_payload
from houston.notifications.push.sender import (
    is_fcm_configured,
    log_fcm_not_configured,
    send_fcm,
)

logger = logging.getLogger(__name__)

TERMINAL_PUSH_DELIVERY_STATUSES = frozenset(
    {
        PushDelivery.Status.SENT,
        PushDelivery.Status.FAILED,
        PushDelivery.Status.SKIPPED,
        PushDelivery.Status.PROCESSING,
    }
)


def get_push_device_for_user(
    *,
    device_id: uuid.UUID,
    user,
) -> PushDevice | None:
    return PushDevice.objects.filter(pk=device_id, user=user).first()


def _refresh_push_device(
    *,
    device: PushDevice,
    user,
    platform: str,
    now,
) -> PushDevice:
    device.user = user
    device.platform = platform
    device.last_seen_at = now
    device.revoked_at = None
    device.save(
        update_fields=[
            "user",
            "platform",
            "last_seen_at",
            "revoked_at",
            "updated_at",
        ],
    )
    return device


@transaction.atomic
def upsert_push_device(
    *,
    user,
    token: str,
    platform: str,
) -> PushDevice:
    now = timezone.now()
    existing = PushDevice.objects.filter(token=token, revoked_at__isnull=True).first()
    if existing is not None:
        return _refresh_push_device(
            device=existing,
            user=user,
            platform=platform,
            now=now,
        )

    try:
        with transaction.atomic():
            return PushDevice.objects.create(
                user=user,
                token=token,
                platform=platform,
                last_seen_at=now,
            )
    except IntegrityError:
        existing = PushDevice.objects.filter(token=token, revoked_at__isnull=True).first()
        if existing is None:
            raise
        return _refresh_push_device(
            device=existing,
            user=user,
            platform=platform,
            now=now,
        )


@transaction.atomic
def revoke_push_device(
    *,
    device: PushDevice,
    user,
) -> PushDevice | None:
    if device.user_id != user.id:
        return None
    if device.revoked_at is not None:
        return device

    now = timezone.now()
    device.revoked_at = now
    device.save(update_fields=["revoked_at", "updated_at"])
    return device


def _queue_push_delivery(*, notification_id: uuid.UUID, device_id: uuid.UUID) -> PushDelivery:
    try:
        delivery, _created = PushDelivery.objects.get_or_create(
            notification_id=notification_id,
            device_id=device_id,
            defaults={"status": PushDelivery.Status.QUEUED},
        )
        return delivery
    except IntegrityError:
        delivery = PushDelivery.objects.filter(
            notification_id=notification_id,
            device_id=device_id,
        ).first()
        if delivery is None:
            raise
        return delivery


def _try_claim_push_delivery_for_send(*, delivery_id: uuid.UUID, now) -> bool:
    return (
        PushDelivery.objects.filter(
            pk=delivery_id,
            status=PushDelivery.Status.QUEUED,
        ).update(status=PushDelivery.Status.PROCESSING, updated_at=now)
        == 1
    )


def _try_mark_push_delivery_skipped(*, delivery_id: uuid.UUID, error_code: str, now) -> bool:
    return (
        PushDelivery.objects.filter(
            pk=delivery_id,
            status=PushDelivery.Status.QUEUED,
        ).update(
            status=PushDelivery.Status.SKIPPED,
            error_code=error_code,
            updated_at=now,
        )
        == 1
    )


def _mark_push_delivery_failed(*, delivery: PushDelivery, error_code: str) -> None:
    delivery.status = PushDelivery.Status.FAILED
    delivery.error_code = error_code
    delivery.save(update_fields=["status", "error_code", "updated_at"])


def _mark_push_delivery_sent(*, delivery: PushDelivery, now) -> None:
    delivery.status = PushDelivery.Status.SENT
    delivery.sent_at = now
    delivery.error_code = ""
    delivery.save(update_fields=["status", "sent_at", "error_code", "updated_at"])


@transaction.atomic
def _revoke_device_internal(*, device: PushDevice, now) -> None:
    if device.revoked_at is not None:
        return
    device.revoked_at = now
    device.save(update_fields=["revoked_at", "updated_at"])


def run_push_for_notification(notification_id: uuid.UUID) -> int:
    if not settings.HOUSTON_PUSH_ENABLED:
        return 0

    notification = (
        Notification.objects.select_related(
            "recipient_membership",
            "recipient_membership__user",
            "actor_membership",
        )
        .filter(pk=notification_id)
        .first()
    )
    if notification is None:
        return 0

    if notification.event_key not in push_constants.PUSH_V1_EVENT_KEYS:
        return 0

    recipient = notification.recipient_membership
    if not recipient.notifications_enabled or not recipient.push_enabled:
        return 0

    if (
        notification.actor_membership_id is not None
        and notification.actor_membership_id == notification.recipient_membership_id
    ):
        return 0

    if not recipient_can_view_notification_subject(
        recipient=recipient,
        establishment_id=notification.establishment_id,
        subject_type=notification.subject_type,
        subject_id=notification.subject_id,
    ):
        return 0

    is_chat_push = notification.event_key == Notification.EventKey.CHAT_MESSAGE_RECEIVED
    if is_chat_push and is_chat_presence_active(
        membership_id=recipient.id,
        conversation_id=notification.subject_id,
    ):
        return 0

    if not is_fcm_configured():
        log_fcm_not_configured(notification_id=str(notification.id))
        return 0

    devices = list(
        PushDevice.objects.filter(
            user_id=recipient.user_id,
            revoked_at__isnull=True,
        )
    )
    if not devices:
        return 0

    payload = build_push_payload(notification)
    push_url = payload["data"]["url"]
    if is_chat_push and push_url is None:
        return 0

    chat_throttle_owner = str(notification.id)
    if is_chat_push and not claim_chat_push_throttle(
        conversation_id=notification.subject_id,
        recipient_membership_id=recipient.id,
        owner_token=chat_throttle_owner,
    ):
        return 0

    now = timezone.now()
    sent_count = 0
    skipped_count = 0
    failed_count = 0

    for device in devices:
        delivery = _queue_push_delivery(
            notification_id=notification.id,
            device_id=device.id,
        )
        if delivery.status in TERMINAL_PUSH_DELIVERY_STATUSES:
            continue

        if push_url is None:
            if _try_mark_push_delivery_skipped(
                delivery_id=delivery.id,
                error_code="missing_navigation",
                now=now,
            ):
                skipped_count += 1
            continue

        if not _try_claim_push_delivery_for_send(delivery_id=delivery.id, now=now):
            continue

        delivery.refresh_from_db()

        try:
            send_fcm(device=device, payload=payload)
        except FcmSendError as exc:
            _mark_push_delivery_failed(delivery=delivery, error_code=exc.error_code)
            failed_count += 1
            if exc.should_revoke:
                _revoke_device_internal(device=device, now=now)
            continue
        except Exception as exc:
            _mark_push_delivery_failed(delivery=delivery, error_code="unexpected_error")
            failed_count += 1
            logger.warning(
                "push_delivery_unexpected_error",
                extra={
                    "event": "push_delivery_unexpected_error",
                    "notification_id": str(notification.id),
                    "device_id": str(device.id),
                    "error_code": "unexpected_error",
                    "exception_class": type(exc).__name__,
                },
                exc_info=False,
            )
            continue

        _mark_push_delivery_sent(delivery=delivery, now=now)
        sent_count += 1

    if is_chat_push and sent_count == 0:
        release_chat_push_throttle(
            conversation_id=notification.subject_id,
            recipient_membership_id=recipient.id,
            owner_token=chat_throttle_owner,
        )

    logger.info(
        "push_for_notification_processed",
        extra={
            "event": "push_for_notification_processed",
            "notification_id": str(notification.id),
            "delivery_count": len(devices),
            "sent_count": sent_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
        },
    )
    return sent_count
