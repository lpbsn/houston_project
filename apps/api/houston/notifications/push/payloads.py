from __future__ import annotations

from houston.notifications.models import Notification
from houston.notifications.navigation import resolve_notification_url

ALLOWED_PUSH_DATA_KEYS: frozenset[str] = frozenset(
    {
        "notification_id",
        "event_key",
        "establishment_id",
        "url",
    }
)


def stringify_push_data(data: dict) -> dict[str, str]:
    return {key: "" if value is None else str(value) for key, value in data.items()}


def build_push_payload(notification: Notification) -> dict:
    return {
        "title": notification.title,
        "body": notification.body,
        "data": {
            "notification_id": str(notification.id),
            "event_key": notification.event_key,
            "establishment_id": str(notification.establishment_id),
            "url": resolve_notification_url(notification),
        },
    }
