from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from houston.notifications.models import Notification, PushDelivery, WebPushSubscription
from houston.notifications.push import constants as push_constants
from houston.notifications.push.exceptions import WebPushSubscriptionValidationError

logger = logging.getLogger(__name__)


def get_web_push_subscription_for_user(
    *,
    subscription_id: uuid.UUID,
    user,
) -> WebPushSubscription | None:
    return WebPushSubscription.objects.filter(pk=subscription_id, user=user).first()


@transaction.atomic
def upsert_web_push_subscription(
    *,
    user,
    endpoint: str,
    p256dh: str,
    auth: str,
    user_agent: str = "",
) -> WebPushSubscription:
    now = timezone.now()
    existing = WebPushSubscription.objects.filter(endpoint=endpoint).first()
    if existing is not None:
        if existing.user_id != user.id:
            raise WebPushSubscriptionValidationError("Endpoint already registered to another user.")
        existing.p256dh = p256dh
        existing.auth = auth
        existing.user_agent = user_agent
        existing.last_seen_at = now
        existing.revoked_at = None
        existing.save(
            update_fields=[
                "p256dh",
                "auth",
                "user_agent",
                "last_seen_at",
                "revoked_at",
                "updated_at",
            ],
        )
        return existing

    return WebPushSubscription.objects.create(
        user=user,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=user_agent,
        last_seen_at=now,
    )


@transaction.atomic
def touch_subscription_last_seen(
    *,
    subscription: WebPushSubscription,
    user,
) -> WebPushSubscription | None:
    if subscription.user_id != user.id:
        return None
    if subscription.revoked_at is not None:
        return None

    now = timezone.now()
    subscription.last_seen_at = now
    subscription.save(update_fields=["last_seen_at", "updated_at"])
    return subscription


@transaction.atomic
def revoke_subscription(
    *,
    subscription: WebPushSubscription,
    user,
) -> WebPushSubscription | None:
    if subscription.user_id != user.id:
        return None
    if subscription.revoked_at is not None:
        return subscription

    now = timezone.now()
    subscription.revoked_at = now
    subscription.save(update_fields=["revoked_at", "updated_at"])
    return subscription


def run_push_for_notification(notification_id: uuid.UUID) -> int:
    if not settings.HOUSTON_PUSH_ENABLED:
        return 0

    notification = (
        Notification.objects.select_related(
            "recipient_membership",
            "recipient_membership__user",
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

    subscriptions = list(
        WebPushSubscription.objects.filter(
            user_id=recipient.user_id,
            revoked_at__isnull=True,
        )
    )
    if not subscriptions:
        return 0

    created_count = 0
    for subscription in subscriptions:
        _, created = PushDelivery.objects.get_or_create(
            notification_id=notification.id,
            subscription_id=subscription.id,
            defaults={"status": PushDelivery.Status.QUEUED},
        )
        if created:
            created_count += 1

    logger.info(
        "push_for_notification_processed",
        extra={
            "event": "push_for_notification_processed",
            "notification_id": str(notification.id),
            "delivery_count": len(subscriptions),
            "created_count": created_count,
        },
    )
    return created_count
