from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.utils.dateparse import parse_datetime

from houston.notifications.constants import INVALID_CURSOR_ERROR_DETAIL
from houston.notifications.exceptions import NotificationCursorError
from houston.notifications.models import Notification

CURSOR_PART_COUNT = 3
DEFAULT_STATUS_FILTER_TOKEN = "default"


@dataclass(frozen=True)
class NotificationCursor:
    status_filter: str | None
    created_at: datetime
    notification_id: uuid.UUID


def _status_filter_token(status_filter: str | None) -> str:
    if status_filter is None:
        return DEFAULT_STATUS_FILTER_TOKEN
    return status_filter


def _encode_cursor_payload(raw: str) -> str:
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor_payload(raw: str) -> str:
    padding = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(f"{raw}{padding}").decode()
    except (ValueError, UnicodeDecodeError) as exc:
        raise NotificationCursorError(INVALID_CURSOR_ERROR_DETAIL) from exc


def encode_notification_cursor(
    *,
    created_at: datetime,
    notification_id: uuid.UUID,
    status_filter: str | None,
) -> str:
    raw = "|".join(
        [
            _status_filter_token(status_filter),
            created_at.isoformat(),
            str(notification_id),
        ]
    )
    return _encode_cursor_payload(raw)


def decode_notification_cursor(
    raw: str | None,
    *,
    expected_status_filter: str | None,
) -> NotificationCursor | None:
    if not raw:
        return None

    parts = _decode_cursor_payload(raw.strip()).split("|")
    if len(parts) != CURSOR_PART_COUNT:
        raise NotificationCursorError(INVALID_CURSOR_ERROR_DETAIL)

    status_token = parts[0]
    if status_token not in {
        DEFAULT_STATUS_FILTER_TOKEN,
        Notification.Status.UNREAD,
        Notification.Status.READ,
        Notification.Status.ARCHIVED,
    }:
        raise NotificationCursorError(INVALID_CURSOR_ERROR_DETAIL)

    expected_token = _status_filter_token(expected_status_filter)
    if status_token != expected_token:
        raise NotificationCursorError(INVALID_CURSOR_ERROR_DETAIL)

    created_at = parse_datetime(parts[1])
    if created_at is None:
        raise NotificationCursorError(INVALID_CURSOR_ERROR_DETAIL)

    try:
        notification_id = uuid.UUID(parts[2])
    except ValueError as exc:
        raise NotificationCursorError(INVALID_CURSOR_ERROR_DETAIL) from exc

    status_filter = None if status_token == DEFAULT_STATUS_FILTER_TOKEN else status_token
    return NotificationCursor(
        status_filter=status_filter,
        created_at=created_at,
        notification_id=notification_id,
    )
