from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.signals.feed_cursor import encode_signal_feed_cursor
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
from houston.testing.signal_feed import flatten_signal_feed_items, signal_feed_section

pytestmark = pytest.mark.django_db


def _create_signal(
    membership,
    *,
    title: str = "Test signal",
    status: str = Signal.Status.OPEN,
    is_pinned: bool = False,
    last_activity_at=None,
):
    signal = create_minimal_v3_signal(membership, title=title, status=status)
    if is_pinned or last_activity_at is not None:
        signal.is_pinned = is_pinned
        if last_activity_at is not None:
            signal.last_activity_at = last_activity_at
        signal.save(update_fields=["is_pinned", "last_activity_at", "updated_at"])
    return signal


def test_feed_includes_open_in_progress_resolved_and_canceled(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _create_signal(membership, title="Open", status=Signal.Status.OPEN)
    _create_signal(membership, title="Progress", status=Signal.Status.IN_PROGRESS)
    _create_signal(membership, title="Done", status=Signal.Status.RESOLVED)
    _create_signal(membership, title="Canceled", status=Signal.Status.CANCELED)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    statuses = {item["status"] for item in flatten_signal_feed_items(response.json())}
    assert statuses == {
        Signal.Status.OPEN,
        Signal.Status.IN_PROGRESS,
        Signal.Status.RESOLVED,
        Signal.Status.CANCELED,
    }


def test_feed_orders_all_active_before_resolved(api_client):
    membership = build_api_membership()
    now = timezone.now()
    resolved = _create_signal(
        membership,
        title="Resolved recent",
        status=Signal.Status.RESOLVED,
        is_pinned=True,
        last_activity_at=now,
    )
    weak_active = _create_signal(
        membership,
        title="Weak active",
        status=Signal.Status.OPEN,
        is_pinned=False,
        last_activity_at=now - timedelta(days=30),
    )
    strong_active = _create_signal(
        membership,
        title="Strong active",
        status=Signal.Status.IN_PROGRESS,
        is_pinned=True,
        last_activity_at=now - timedelta(days=1),
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    section_statuses = [section["status"] for section in response.json()["sections"]]
    assert section_statuses == [
        Signal.Status.OPEN,
        Signal.Status.IN_PROGRESS,
        Signal.Status.RESOLVED,
    ]
    ids = [item["id"] for item in flatten_signal_feed_items(response.json())]
    assert ids.index(str(weak_active.id)) < ids.index(str(strong_active.id))
    assert ids.index(str(strong_active.id)) < ids.index(str(resolved.id))


def test_feed_orders_resolved_before_canceled(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    canceled = _create_signal(
        membership,
        title="Canceled recent",
        status=Signal.Status.CANCELED,
        is_pinned=True,
        last_activity_at=now,
    )
    resolved = _create_signal(
        membership,
        title="Resolved older",
        status=Signal.Status.RESOLVED,
        is_pinned=False,
        last_activity_at=now - timedelta(days=1),
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    ids = [item["id"] for item in flatten_signal_feed_items(response.json())]
    assert ids.index(str(resolved.id)) < ids.index(str(canceled.id))


def test_apply_feed_sorting_active_before_dirty_resolved():
    membership = build_api_membership()
    now = timezone.now()
    resolved = _create_signal(
        membership,
        status=Signal.Status.RESOLVED,
        is_pinned=True,
        last_activity_at=now,
    )
    active = _create_signal(
        membership,
        status=Signal.Status.OPEN,
        is_pinned=False,
        last_activity_at=now - timedelta(days=60),
    )

    ordered = list(
        apply_feed_sorting(
            feed_signals_for_establishment(establishment_id=membership.establishment_id),
        ),
    )

    assert [signal.id for signal in ordered] == [active.id, resolved.id]


def test_feed_pagination_keeps_later_sections_visible_when_actives_fill_page(api_client):
    membership = build_api_membership()
    for index in range(3):
        _create_signal(
            membership,
            title=f"Active {index}",
            status=Signal.Status.OPEN,
        )
    _create_signal(membership, title="Progress", status=Signal.Status.IN_PROGRESS)
    resolved = _create_signal(membership, title="Resolved", status=Signal.Status.RESOLVED)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general&page_size=2",
        **auth_headers(token),
    )

    body = response.json()
    assert response.status_code == 200
    open_section = signal_feed_section(body, Signal.Status.OPEN)
    progress_section = signal_feed_section(body, Signal.Status.IN_PROGRESS)
    resolved_section = signal_feed_section(body, Signal.Status.RESOLVED)
    assert open_section is not None
    assert len(open_section["items"]) == 2
    assert open_section["has_more"] is True
    assert open_section["next_cursor"] is not None
    assert progress_section is not None
    assert len(progress_section["items"]) == 1
    assert progress_section["has_more"] is False
    assert resolved_section is not None
    assert [item["id"] for item in resolved_section["items"]] == [str(resolved.id)]
    assert resolved_section["has_more"] is False

    page_two = api_client.get(
        signal_feed_url(membership.establishment_id)
        + (
            "?view_mode=general&page_size=2"
            f"&statuses=open&cursor={open_section['next_cursor']}"
        ),
        **auth_headers(token),
    )

    assert page_two.status_code == 200
    page_two_body = page_two.json()
    assert [section["status"] for section in page_two_body["sections"]] == [Signal.Status.OPEN]
    page_two_ids = {item["id"] for item in flatten_signal_feed_items(page_two_body)}
    first_page_open_ids = {item["id"] for item in open_section["items"]}
    assert page_two_ids.isdisjoint(first_page_open_ids)
    assert len(page_two_ids) == 1
    assert page_two_body["sections"][0]["has_more"] is False


def test_feed_cursor_without_single_status_returns_400(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership, status=Signal.Status.OPEN)
    token = login(api_client, user=membership.user)
    cursor = encode_signal_feed_cursor(signal)

    missing_status = api_client.get(
        signal_feed_url(membership.establishment_id) + f"?view_mode=general&cursor={cursor}",
        **auth_headers(token),
    )
    mismatched = api_client.get(
        signal_feed_url(membership.establishment_id)
        + f"?view_mode=general&statuses=resolved&cursor={cursor}",
        **auth_headers(token),
    )

    assert missing_status.status_code == 400
    assert missing_status.json()["code"] == "validation_error"
    assert mismatched.status_code == 400
    assert mismatched.json()["code"] == "validation_error"


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

    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _create_signal(
        membership,
        status=Signal.Status.RESOLVED,
        is_pinned=True,
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    hints = response.json()["permission_hints"]
    assert hints["can_pin"] is False
    assert hints["can_cancel"] is False
    assert hints["can_resolve"] is False
    assert hints["can_create_linked_action_plan"] is False


def test_in_progress_permission_hints_deny_pin(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    signal = _create_signal(membership, title="Progress", status=Signal.Status.IN_PROGRESS)
    token = login(api_client, user=membership.user)

    feed_response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert feed_response.status_code == 200
    feed_item = next(
        item
        for item in flatten_signal_feed_items(feed_response.json())
        if item["id"] == str(signal.id)
    )
    assert feed_item["permission_hints"]["can_pin"] is False

    detail_response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )
    assert detail_response.status_code == 200
    hints = detail_response.json()["permission_hints"]
    assert hints["can_pin"] is False
    assert hints["can_cancel"] is False
    assert hints["can_resolve"] is False
