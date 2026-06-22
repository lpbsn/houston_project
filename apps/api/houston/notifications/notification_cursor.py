from __future__ import annotations

import uuid
from datetime import datetime

from django.utils.dateparse import parse_datetime

from houston.notifications.constants import INVALID_CURSOR_ERROR_DETAIL
from houston.notifications.exceptions import NotificationCursorError


def encode_notification_cursor(*, created_at: datetime, notification_id: uuid.UUID) -> str:
    return f"{created_at.isoformat()}|{notification_id}"


def decode_notification_cursor(raw: str | None) -> tuple[datetime, uuid.UUID] | None:
    if not raw:
        return None
    parts = raw.split("|", 1)
    if len(parts) != 2:
        raise NotificationCursorError(INVALID_CURSOR_ERROR_DETAIL)
    created_at = parse_datetime(parts[0])
    if created_at is None:
        raise NotificationCursorError(INVALID_CURSOR_ERROR_DETAIL)
    try:
        notification_id = uuid.UUID(parts[1])
    except ValueError as exc:
        raise NotificationCursorError(INVALID_CURSOR_ERROR_DETAIL) from exc
    return created_at, notification_id
