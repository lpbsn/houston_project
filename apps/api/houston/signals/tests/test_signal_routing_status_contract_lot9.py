"""Lot 9 contract — feed exposes routing_status; detail adds issue_focus."""

from __future__ import annotations

import pytest
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    login,
    signal_detail_url,
    signal_feed_url,
)

pytestmark = pytest.mark.django_db


def _unassigned_signal(membership, *, title: str = "Unassigned") -> Signal:
    return Signal.objects.create(
        establishment=membership.establishment,
        title=title,
        structured_summary="Needs qualification.",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        issue_focus="",
        last_activity_at=timezone.now(),
    )


def test_feed_item_exposes_routing_status_not_issue_focus(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    unassigned = _unassigned_signal(membership, title="Needs qualify")
    resolved = create_minimal_v3_signal(membership, title="Resolved routing")
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )

    assert response.status_code == 200
    items = {item["id"]: item for item in response.json()["items"]}
    assert items[str(unassigned.id)]["routing_status"] == Signal.RoutingStatus.UNASSIGNED
    assert items[str(resolved.id)]["routing_status"] == Signal.RoutingStatus.RESOLVED
    assert "issue_focus" not in items[str(unassigned.id)]
    assert "issue_focus" not in items[str(resolved.id)]


def test_detail_exposes_routing_status_and_issue_focus(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _unassigned_signal(membership)
    signal.issue_focus = "lampe hs"
    signal.save(update_fields=["issue_focus", "updated_at"])
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["routing_status"] == Signal.RoutingStatus.UNASSIGNED
    assert body["issue_focus"] == "lampe hs"
