from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.signals.feed_cursor import (
    SignalFeedCursorError,
    encode_signal_feed_cursor,
    parse_signal_feed_cursor,
)
from houston.signals.models import Signal
from houston.signals.tests.conftest import build_api_membership, create_minimal_v3_signal

pytestmark = pytest.mark.django_db


def _create_signal(
    membership,
    *,
    status: str = Signal.Status.OPEN,
    urgency: str = Signal.Urgency.NORMAL,
    is_pinned: bool = False,
    last_activity_at=None,
):
    signal = create_minimal_v3_signal(membership, title="Cursor signal", status=status)
    if urgency != Signal.Urgency.NORMAL or is_pinned or last_activity_at is not None:
        signal.urgency = urgency
        signal.is_pinned = is_pinned
        if last_activity_at is not None:
            signal.last_activity_at = last_activity_at
        signal.save(update_fields=["urgency", "is_pinned", "last_activity_at", "updated_at"])
    return signal


def test_encode_and_parse_signal_feed_cursor_round_trip():
    membership = build_api_membership()
    now = timezone.now()
    signal = _create_signal(
        membership,
        status=Signal.Status.IN_PROGRESS,
        urgency=Signal.Urgency.HIGH,
        is_pinned=True,
        last_activity_at=now,
    )

    encoded = encode_signal_feed_cursor(signal)
    parsed = parse_signal_feed_cursor(encoded)

    assert parsed is not None
    assert parsed.status_group_rank == 0
    assert parsed.is_pinned is True
    assert parsed.urgency_order == 0
    assert parsed.status_rank == 1
    assert parsed.last_activity_at == signal.last_activity_at
    assert parsed.created_at == signal.created_at
    assert parsed.signal_id == signal.id


def test_parse_signal_feed_cursor_rejects_invalid_values():
    with pytest.raises(SignalFeedCursorError):
        parse_signal_feed_cursor("bad")

    membership = build_api_membership()
    signal = _create_signal(
        membership,
        last_activity_at=timezone.now() - timedelta(days=1),
    )
    encoded = encode_signal_feed_cursor(signal)
    corrupted = encoded[:-4] + "XXXX"

    with pytest.raises(SignalFeedCursorError):
        parse_signal_feed_cursor(corrupted)


def test_parse_signal_feed_cursor_none_for_empty():
    assert parse_signal_feed_cursor(None) is None
    assert parse_signal_feed_cursor("") is None
