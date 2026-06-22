from __future__ import annotations

import uuid

import pytest
from django.utils import timezone

from houston.notifications.exceptions import NotificationCursorError
from houston.notifications.models import Notification
from houston.notifications.notification_cursor import (
    decode_notification_cursor,
    encode_notification_cursor,
)

pytestmark = pytest.mark.django_db


def test_encode_decode_roundtrip_default_status_filter():
    created_at = timezone.now()
    notification_id = uuid.uuid4()

    encoded = encode_notification_cursor(
        created_at=created_at,
        notification_id=notification_id,
        status_filter=None,
    )
    decoded = decode_notification_cursor(
        encoded,
        expected_status_filter=None,
    )

    assert decoded is not None
    assert decoded.status_filter is None
    assert decoded.created_at == created_at
    assert decoded.notification_id == notification_id


def test_encode_decode_roundtrip_explicit_status_filter():
    created_at = timezone.now()
    notification_id = uuid.uuid4()

    encoded = encode_notification_cursor(
        created_at=created_at,
        notification_id=notification_id,
        status_filter=Notification.Status.UNREAD,
    )
    decoded = decode_notification_cursor(
        encoded,
        expected_status_filter=Notification.Status.UNREAD,
    )

    assert decoded is not None
    assert decoded.status_filter == Notification.Status.UNREAD
    assert decoded.notification_id == notification_id


def test_encoded_cursor_is_url_safe():
    created_at = timezone.now()
    encoded = encode_notification_cursor(
        created_at=created_at,
        notification_id=uuid.uuid4(),
        status_filter=None,
    )

    assert "+" not in encoded
    assert "/" not in encoded
    assert "=" not in encoded


def test_decode_rejects_status_filter_mismatch():
    created_at = timezone.now()
    encoded = encode_notification_cursor(
        created_at=created_at,
        notification_id=uuid.uuid4(),
        status_filter=Notification.Status.UNREAD,
    )

    with pytest.raises(NotificationCursorError):
        decode_notification_cursor(
            encoded,
            expected_status_filter=Notification.Status.READ,
        )


def test_decode_rejects_legacy_plain_text_cursor():
    legacy = f"{timezone.now().isoformat()}|{uuid.uuid4()}"

    with pytest.raises(NotificationCursorError):
        decode_notification_cursor(
            legacy,
            expected_status_filter=None,
        )
