from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.signals.feed_cursor import (
    SignalFeedCursorError,
    encode_signal_feed_cursor,
    parse_signal_feed_cursor,
    signal_feed_auth_context_hash,
    signal_feed_filter_hash,
)
from houston.signals.models import Signal
from houston.signals.tests.conftest import build_api_membership, create_minimal_v3_signal
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def _create_signal(membership, *, status: str = Signal.Status.OPEN, title: str = "Cursor signal"):
    return create_minimal_v3_signal(membership, title=title, status=status)


def _cursor_context(membership):
    return {
        "scope": "establishment",
        "view_mode": "general",
        "status": "all",
        "filter_hash": signal_feed_filter_hash(
            business_unit_ids=(),
            activity_subject_ids=(),
            needs_qualification=False,
        ),
        "auth_context_hash": signal_feed_auth_context_hash(
            memberships=[membership],
            view_mode="general",
            scope="establishment",
        ),
    }


def test_encode_and_parse_signal_feed_cursor_round_trip():
    membership = build_api_membership()
    now = timezone.now()
    signal = _create_signal(membership, status=Signal.Status.IN_PROGRESS)
    signal.last_activity_at = now
    signal.save(update_fields=["last_activity_at", "updated_at"])

    encoded = encode_signal_feed_cursor(signal, **_cursor_context(membership))
    parsed = parse_signal_feed_cursor(encoded)

    assert parsed is not None
    assert parsed.collection == "L"
    assert parsed.scope == "establishment"
    assert parsed.status == "all"
    assert parsed.status_rank == 1
    assert parsed.last_activity_at == signal.last_activity_at
    assert parsed.created_at == signal.created_at
    assert parsed.signal_id == signal.id


def test_parse_signal_feed_cursor_rejects_pin_collection():
    membership = build_api_membership()
    signal = _create_signal(membership)
    signal.is_pinned = True
    signal.pinned_at = timezone.now()
    signal.save(update_fields=["is_pinned", "pinned_at", "updated_at"])
    from houston.signals.feed_cursor import encode_signal_feed_pin_cursor

    encoded = encode_signal_feed_pin_cursor(signal, **_cursor_context(membership))
    with pytest.raises(SignalFeedCursorError):
        parse_signal_feed_cursor(encoded)


def test_parse_signal_feed_cursor_rejects_invalid_values():
    with pytest.raises(SignalFeedCursorError):
        parse_signal_feed_cursor("bad")

    membership = build_api_membership()
    signal = _create_signal(membership)
    encoded = encode_signal_feed_cursor(signal, **_cursor_context(membership))
    assert parse_signal_feed_cursor(encoded) is not None
    assert signal.last_activity_at > timezone.now() - timedelta(days=1)


def test_auth_context_hash_changes_when_role_changes():
    membership = build_api_membership()
    before = signal_feed_auth_context_hash(
        memberships=[membership],
        view_mode="general",
        scope="establishment",
    )
    membership.role = "manager"
    after = signal_feed_auth_context_hash(
        memberships=[membership],
        view_mode="general",
        scope="establishment",
    )
    assert before != after


def test_auth_context_hash_changes_when_business_unit_scope_changes():
    membership = build_api_membership()
    before = signal_feed_auth_context_hash(
        memberships=[membership],
        view_mode="personal",
        scope="establishment",
    )
    business_unit = create_business_unit(
        establishment=membership.establishment,
        key=f"cursor-scope-{membership.establishment_id}",
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    membership = type(membership).objects.get(pk=membership.pk)

    after = signal_feed_auth_context_hash(
        memberships=[membership],
        view_mode="personal",
        scope="establishment",
    )

    assert before != after


def test_auth_context_hash_changes_when_cross_establishment_set_changes():
    first = build_api_membership()
    second = build_api_membership()
    before = signal_feed_auth_context_hash(
        memberships=[first],
        view_mode="general",
        scope="cross",
    )
    after = signal_feed_auth_context_hash(
        memberships=[first, second],
        view_mode="general",
        scope="cross",
    )

    assert before != after
