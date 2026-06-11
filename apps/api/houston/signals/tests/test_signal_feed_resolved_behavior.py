from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.signals.selectors import apply_feed_sorting, feed_signals_for_establishment
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    login,
    signal_detail_url,
    signal_feed_url,
)

pytestmark = pytest.mark.django_db


def _create_signal(
    membership,
    *,
    title: str = "Test signal",
    status: str = Signal.Status.OPEN,
    urgency: str = Signal.Urgency.NORMAL,
    is_pinned: bool = False,
    last_activity_at=None,
):
    signal = create_minimal_v3_signal(membership, title=title, status=status)
    if urgency != Signal.Urgency.NORMAL or is_pinned or last_activity_at is not None:
        signal.urgency = urgency
        signal.is_pinned = is_pinned
        if last_activity_at is not None:
            signal.last_activity_at = last_activity_at
        signal.save(update_fields=["urgency", "is_pinned", "last_activity_at", "updated_at"])
    return signal


def test_feed_includes_open_in_progress_and_resolved(api_client):
    membership = build_api_membership()
    _create_signal(membership, title="Open", status=Signal.Status.OPEN)
    _create_signal(membership, title="Progress", status=Signal.Status.IN_PROGRESS)
    _create_signal(membership, title="Done", status=Signal.Status.RESOLVED)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    statuses = {item["status"] for item in response.json()["items"]}
    assert statuses == {
        Signal.Status.OPEN,
        Signal.Status.IN_PROGRESS,
        Signal.Status.RESOLVED,
    }


def test_feed_excludes_canceled_and_archived(api_client):
    membership = build_api_membership()
    _create_signal(membership, status=Signal.Status.CANCELED)
    _create_signal(membership, status=Signal.Status.ARCHIVED)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_feed_orders_all_active_before_resolved(api_client):
    membership = build_api_membership()
    now = timezone.now()
    resolved = _create_signal(
        membership,
        title="Resolved recent",
        status=Signal.Status.RESOLVED,
        is_pinned=True,
        urgency=Signal.Urgency.HIGH,
        last_activity_at=now,
    )
    weak_active = _create_signal(
        membership,
        title="Weak active",
        status=Signal.Status.OPEN,
        is_pinned=False,
        urgency=Signal.Urgency.NORMAL,
        last_activity_at=now - timedelta(days=30),
    )
    strong_active = _create_signal(
        membership,
        title="Strong active",
        status=Signal.Status.IN_PROGRESS,
        is_pinned=True,
        urgency=Signal.Urgency.HIGH,
        last_activity_at=now - timedelta(days=1),
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert ids.index(str(strong_active.id)) < ids.index(str(weak_active.id))
    assert ids.index(str(weak_active.id)) < ids.index(str(resolved.id))


def test_apply_feed_sorting_active_before_dirty_resolved():
    membership = build_api_membership()
    now = timezone.now()
    resolved = _create_signal(
        membership,
        status=Signal.Status.RESOLVED,
        is_pinned=True,
        urgency=Signal.Urgency.HIGH,
        last_activity_at=now,
    )
    active = _create_signal(
        membership,
        status=Signal.Status.OPEN,
        is_pinned=False,
        urgency=Signal.Urgency.NORMAL,
        last_activity_at=now - timedelta(days=60),
    )

    ordered = list(
        apply_feed_sorting(
            feed_signals_for_establishment(establishment_id=membership.establishment_id),
        ),
    )

    assert [signal.id for signal in ordered] == [active.id, resolved.id]


def test_feed_pagination_offset_may_hide_resolved_when_actives_fill_page(api_client):
    membership = build_api_membership()
    for index in range(3):
        _create_signal(
            membership,
            title=f"Active {index}",
            status=Signal.Status.OPEN,
        )
    resolved = _create_signal(membership, title="Resolved", status=Signal.Status.RESOLVED)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general&page_size=2",
        **auth_headers(token),
    )

    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 2
    assert all(item["status"] != Signal.Status.RESOLVED for item in body["items"])
    assert body["has_more"] is True
    assert body["next_cursor"] is not None

    page_two = api_client.get(
        signal_feed_url(membership.establishment_id)
        + f"?view_mode=general&page_size=2&cursor={body['next_cursor']}",
        **auth_headers(token),
    )

    assert page_two.status_code == 200
    page_two_body = page_two.json()
    page_two_ids = {item["id"] for item in page_two_body["items"]}
    assert str(resolved.id) in page_two_ids


def test_detail_resolved_returns_200(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership, status=Signal.Status.RESOLVED)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == Signal.Status.RESOLVED


def test_detail_canceled_returns_404(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership, status=Signal.Status.CANCELED)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_detail_resolved_permission_hints_all_false(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _create_signal(
        membership,
        status=Signal.Status.RESOLVED,
        is_pinned=True,
        urgency=Signal.Urgency.HIGH,
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    hints = response.json()["permission_hints"]
    assert hints["can_pin"] is False
    assert hints["can_set_urgency"] is False
    assert hints["can_cancel"] is False
    assert hints["can_resolve"] is False
    assert hints["can_create_action"] is False
