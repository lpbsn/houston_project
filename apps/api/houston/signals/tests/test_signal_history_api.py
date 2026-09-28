from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from houston.core.civil_time import PARIS
from houston.core.opaque_cursor import OpaqueCursorError, encode_opaque_cursor
from houston.establishments.models import EstablishmentMembership
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    SIGNAL_RESOLUTION_ORIGIN_MANUAL,
)
from houston.signals.history_cursor import parse_signal_history_cursor
from houston.signals.lifecycle_events import record_signal_lifecycle_event
from houston.signals.models import Signal, SignalLifecycleEvent
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    login,
    signal_detail_url,
)

pytestmark = pytest.mark.django_db


def _history_url(establishment_id, **params: str) -> str:
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"/api/v1/establishments/{establishment_id}/history/signals/?{query}"


def _close(
    signal: Signal,
    *,
    at: datetime,
    origin: str | None = SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    actor=None,
    status: str = Signal.Status.RESOLVED,
) -> Signal:
    signal.status = status
    if status == Signal.Status.RESOLVED:
        signal.resolved_at = at
        signal.resolution_origin = origin
        signal.resolved_by_membership = actor
        signal.save(
            update_fields=[
                "status",
                "resolved_at",
                "resolution_origin",
                "resolved_by_membership",
                "updated_at",
            ]
        )
    else:
        signal.canceled_at = at
        signal.canceled_by_membership = actor
        signal.save(
            update_fields=["status", "canceled_at", "canceled_by_membership", "updated_at"]
        )
    return signal


def test_history_cursor_rejects_a_naive_terminal_datetime():
    cursor = encode_opaque_cursor(
        {
            "v": "v1",
            "kind": "signal_history",
            "context_hash": "context",
            "terminal_at": "2026-09-28T12:00:00",
            "item_id": "11111111-1111-4111-8111-111111111111",
        }
    )
    with pytest.raises(OpaqueCursorError):
        parse_signal_history_cursor(cursor)


def test_history_lists_terminal_signals_and_keeps_detail_access(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    membership.user.first_name = "Ada"
    membership.user.last_name = "Lovelace"
    membership.user.save(update_fields=["first_name", "last_name"])
    open_signal = create_minimal_v3_signal(membership, title="Encore ouvert")
    resolved = _close(
        create_minimal_v3_signal(membership, title="Résolu"),
        at=timezone.now(),
        actor=membership,
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        _history_url(membership.establishment_id, view_mode="general", period="all"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body["items"]]
    assert str(resolved.id) in ids
    assert str(open_signal.id) not in ids
    item = next(row for row in body["items"] if row["id"] == str(resolved.id))
    assert item["terminal_date_source"] == "field"
    assert item["termination_origin"] == "manual"
    assert item["termination_actor_display_name"] == "Ada Lovelace"
    assert body["undated_count"] is None

    detail = api_client.get(
        signal_detail_url(membership.establishment_id, resolved.id),
        **auth_headers(token),
    )
    assert detail.status_code == 200


def test_missing_actor_on_manual_resolution_stays_unknown(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _close(
        create_minimal_v3_signal(membership, title="Ancien"),
        at=timezone.now(),
        origin=SIGNAL_RESOLUTION_ORIGIN_MANUAL,
        actor=None,
    )
    token = login(api_client, user=membership.user)
    response = api_client.get(
        _history_url(membership.establishment_id, view_mode="general", period="all"),
        **auth_headers(token),
    )
    item = next(row for row in response.json()["items"] if row["id"] == str(signal.id))
    assert item["termination_origin"] == "unknown"
    assert item["termination_actor_display_name"] is None


def test_canceled_without_actor_is_unknown(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _close(
        create_minimal_v3_signal(membership, title="Annulé"),
        at=timezone.now(),
        status=Signal.Status.CANCELED,
        actor=None,
    )
    token = login(api_client, user=membership.user)
    response = api_client.get(
        _history_url(membership.establishment_id, view_mode="general", period="all"),
        **auth_headers(token),
    )
    item = next(row for row in response.json()["items"] if row["id"] == str(signal.id))
    assert item["termination_origin"] == "unknown"
    assert item["status"] == "canceled"


def test_orphan_is_visible_in_all_and_counted_outside_a_period(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    dated = _close(
        create_minimal_v3_signal(membership, title="Daté"),
        at=timezone.now(),
        actor=membership,
    )
    orphan = create_minimal_v3_signal(membership, title="Sans date", status=Signal.Status.RESOLVED)
    orphan.resolved_at = None
    orphan.resolution_origin = None
    orphan.save(update_fields=["resolved_at", "resolution_origin", "updated_at"])
    token = login(api_client, user=membership.user)

    bounded = api_client.get(
        _history_url(membership.establishment_id, view_mode="general", period="30"),
        **auth_headers(token),
    )
    bounded_body = bounded.json()
    assert bounded_body["undated_count"] == 1
    assert str(orphan.id) not in [item["id"] for item in bounded_body["items"]]
    assert str(dated.id) in [item["id"] for item in bounded_body["items"]]

    everything = api_client.get(
        _history_url(membership.establishment_id, view_mode="general", period="all"),
        **auth_headers(token),
    )
    rows = everything.json()["items"]
    assert rows[-1]["id"] == str(orphan.id)
    assert rows[-1]["terminal_at"] is None
    assert rows[-1]["terminal_date_source"] == "unknown"


def test_all_period_continues_from_dated_rows_into_undated_rows(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    dated = _close(
        create_minimal_v3_signal(membership, title="Daté"),
        at=timezone.now(),
        actor=membership,
    )
    orphans = [
        create_minimal_v3_signal(
            membership,
            title=f"Sans date {index}",
            status=Signal.Status.RESOLVED,
        )
        for index in range(2)
    ]
    for orphan in orphans:
        orphan.resolved_at = None
        orphan.resolution_origin = None
        orphan.save(update_fields=["resolved_at", "resolution_origin", "updated_at"])
    expected_orphan_ids = sorted([orphan.id for orphan in orphans], reverse=True)
    token = login(api_client, user=membership.user)

    cursor = None
    returned_ids = []
    for _ in range(3):
        params = {
            "view_mode": "general",
            "period": "all",
            "page_size": "1",
        }
        if cursor is not None:
            params["cursor"] = cursor
        response = api_client.get(
            _history_url(membership.establishment_id, **params),
            **auth_headers(token),
        )
        assert response.status_code == 200
        body = response.json()
        returned_ids.append(body["items"][0]["id"])
        cursor = body["next_cursor"]

    assert returned_ids == [str(dated.id), *(str(item_id) for item_id in expected_orphan_ids)]
    assert cursor is None


def test_missing_field_uses_the_latest_terminal_event(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Événement", status=Signal.Status.RESOLVED)
    signal.resolved_at = None
    signal.save(update_fields=["resolved_at", "updated_at"])
    occurred_at = datetime(2026, 3, 29, 0, 30, tzinfo=PARIS)
    record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=occurred_at,
        actor_membership=membership,
    )
    token = login(api_client, user=membership.user)
    response = api_client.get(
        _history_url(
            membership.establishment_id,
            view_mode="general",
            period="custom",
            **{"from": "2026-03-29", "to": "2026-03-29"},
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == str(signal.id)
    assert item["terminal_date_source"] == "event"
    assert item["terminal_at"].startswith("2026-03-28T23:30:00")


def test_paris_custom_window_keeps_the_spring_forward_civil_day(api_client, monkeypatch):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    included = _close(
        create_minimal_v3_signal(membership, title="Dans la journée"),
        at=datetime(2026, 3, 28, 23, 30, tzinfo=ZoneInfo("UTC")),
        actor=membership,
    )
    excluded = _close(
        create_minimal_v3_signal(membership, title="La veille"),
        at=datetime(2026, 3, 28, 22, 30, tzinfo=ZoneInfo("UTC")),
        actor=membership,
    )
    monkeypatch.setattr(
        "houston.signals.api.history_views.timezone.now",
        lambda: datetime(2026, 3, 29, 12, tzinfo=PARIS),
    )
    token = login(api_client, user=membership.user)
    response = api_client.get(
        _history_url(
            membership.establishment_id,
            view_mode="general",
            period="custom",
            **{"from": "2026-03-29", "to": "2026-03-29"},
        ),
        **auth_headers(token),
    )
    ids = [item["id"] for item in response.json()["items"]]
    assert ids == [str(included.id)]
    assert str(excluded.id) not in ids


def test_equal_terminal_dates_continue_by_descending_id(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    terminal_at = datetime(2026, 9, 28, 18, tzinfo=PARIS)
    first_signal = _close(
        create_minimal_v3_signal(membership, title="Premier"),
        at=terminal_at,
        actor=membership,
    )
    second_signal = _close(
        create_minimal_v3_signal(membership, title="Second"),
        at=terminal_at,
        actor=membership,
    )
    expected_ids = sorted([first_signal.id, second_signal.id], reverse=True)
    token = login(api_client, user=membership.user)
    first = api_client.get(
        _history_url(
            membership.establishment_id,
            view_mode="general",
            period="all",
            page_size="1",
        ),
        **auth_headers(token),
    )
    first_body = first.json()
    assert first_body["items"][0]["id"] == str(expected_ids[0])
    assert first_body["has_more"] is True
    second = api_client.get(
        _history_url(
            membership.establishment_id,
            view_mode="general",
            period="all",
            page_size="1",
            cursor=first_body["next_cursor"],
        ),
        **auth_headers(token),
    )
    second_body = second.json()
    assert second_body["items"][0]["id"] == str(expected_ids[1])
    assert second_body["undated_count"] is None
    assert second_body["items"][0]["terminal_at"] == first_body["items"][0]["terminal_at"]


def test_cursor_rejects_a_different_view_mode(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _close(
        create_minimal_v3_signal(membership, title="Un"),
        at=timezone.now(),
        actor=membership,
    )
    _close(
        create_minimal_v3_signal(membership, title="Deux"),
        at=timezone.now(),
        actor=membership,
    )
    token = login(api_client, user=membership.user)
    first = api_client.get(
        _history_url(
            membership.establishment_id,
            view_mode="general",
            period="all",
            page_size="1",
        ),
        **auth_headers(token),
    )
    mismatched = api_client.get(
        _history_url(
            membership.establishment_id,
            view_mode="personal",
            period="all",
            page_size="1",
            cursor=first.json()["next_cursor"],
        ),
        **auth_headers(token),
    )
    assert mismatched.status_code == 400
    assert mismatched.json()["code"] == "cursor_context_mismatch"


def test_cursor_rejects_a_changed_authorization_context(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    for title in ("Un", "Deux"):
        _close(
            create_minimal_v3_signal(membership, title=title),
            at=timezone.now(),
            actor=membership,
        )
    token = login(api_client, user=membership.user)
    first = api_client.get(
        _history_url(
            membership.establishment_id,
            view_mode="general",
            period="all",
            page_size="1",
        ),
        **auth_headers(token),
    )
    membership.role = EstablishmentMembership.Role.DIRECTOR
    membership.save(update_fields=["role", "updated_at"])

    mismatched = api_client.get(
        _history_url(
            membership.establishment_id,
            view_mode="general",
            period="all",
            page_size="1",
            cursor=first.json()["next_cursor"],
        ),
        **auth_headers(token),
    )
    assert mismatched.status_code == 400
    assert mismatched.json()["code"] == "cursor_context_mismatch"


def test_other_establishment_history_is_not_found(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    stranger = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=stranger.user)
    response = api_client.get(
        _history_url(owner.establishment_id, view_mode="general", period="all"),
        **auth_headers(token),
    )
    assert response.status_code == 403


def test_staff_cannot_open_cross_history(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    token = login(api_client, user=membership.user)
    response = api_client.get(
        "/api/v1/cross/history/signals/?view_mode=general&period=all",
        **auth_headers(token),
    )
    assert response.status_code == 403


def test_resolved_signal_leaves_history_when_it_is_no_longer_terminal(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _close(
        create_minimal_v3_signal(membership, title="Cycle"),
        at=timezone.now(),
        actor=membership,
    )
    record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=signal.resolved_at,
        actor_membership=membership,
    )
    signal.status = Signal.Status.OPEN
    signal.resolved_at = None
    signal.save(update_fields=["status", "resolved_at", "updated_at"])
    token = login(api_client, user=membership.user)
    response = api_client.get(
        _history_url(membership.establishment_id, view_mode="general", period="all"),
        **auth_headers(token),
    )
    assert str(signal.id) not in [item["id"] for item in response.json()["items"]]
    assert SignalLifecycleEvent.objects.filter(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    ).exists()
