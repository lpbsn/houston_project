from __future__ import annotations

import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

from houston.notifications.models import WebPushSubscription

logger = logging.getLogger(__name__)

PERMANENT_REVOKE_STATUS_CODES = frozenset({404, 410})


def is_vapid_configured() -> bool:
    return bool(
        settings.HOUSTON_VAPID_PRIVATE_KEY.strip()
        and settings.HOUSTON_VAPID_PUBLIC_KEY.strip()
        and settings.HOUSTON_VAPID_SUBJECT.strip()
    )


def web_push_error_code(exc: WebPushException) -> str:
    status_code = None
    if exc.response is not None:
        status_code = exc.response.status_code
    if status_code is None:
        return "unknown"
    if status_code >= 500:
        return "transient"
    return f"http_{status_code}"


def should_revoke_subscription_for_error(exc: WebPushException) -> bool:
    if exc.response is None:
        return False
    return exc.response.status_code in PERMANENT_REVOKE_STATUS_CODES


def send_web_push(*, subscription: WebPushSubscription, payload: dict) -> None:
    webpush(
        subscription_info={
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh,
                "auth": subscription.auth,
            },
        },
        data=json.dumps(payload),
        vapid_private_key=settings.HOUSTON_VAPID_PRIVATE_KEY,
        vapid_claims={"sub": settings.HOUSTON_VAPID_SUBJECT},
    )


def log_vapid_not_configured(*, notification_id: str) -> None:
    logger.warning(
        "push_vapid_not_configured",
        extra={
            "event": "push_vapid_not_configured",
            "notification_id": notification_id,
        },
    )
