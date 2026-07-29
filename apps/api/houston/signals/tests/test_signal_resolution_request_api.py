from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.signals.models import SignalResolutionRequest
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    login,
    signal_detail_url,
)
from houston.testing.auth import assign_business_unit_scope, build_api_membership_on_establishment

pytestmark = pytest.mark.django_db


def _setup_manager_director_signal():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, title="API resolution")
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    assign_business_unit_scope(manager, signal.responsible_business_unit)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    return owner, signal, manager, director


def test_manager_can_create_resolution_request_via_api(api_client):
    owner, signal, manager, _director = _setup_manager_director_signal()
    token = login(api_client, user=manager.user)

    response = api_client.post(
        signal_detail_url(owner.establishment_id, signal.id) + "resolution-requests/",
        {"request_comment": "Corrigé"},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "open"
    assert body["resolution_request"]["status"] == SignalResolutionRequest.Status.PENDING
    assert (
        body["resolution_request"]["review_route"]
        == SignalResolutionRequest.ReviewRoute.MANAGER_TO_DIRECTOR
    )
    assert body["permission_hints"]["can_resolve"] is False
    events = body["resolution_request_events"]
    assert len(events) == 1
    assert events[0]["event_type"] == "created"
    assert events[0]["actor_display_name"]


def test_requester_can_cancel_resolution_request_via_api(api_client):
    owner, signal, manager, _director = _setup_manager_director_signal()
    token = login(api_client, user=manager.user)

    create_response = api_client.post(
        signal_detail_url(owner.establishment_id, signal.id) + "resolution-requests/",
        {},
        format="json",
        **auth_headers(token),
    )
    request_id = create_response.json()["resolution_request"]["id"]

    response = api_client.post(
        signal_detail_url(owner.establishment_id, signal.id)
        + f"resolution-requests/{request_id}/cancel/",
        {"cancel_comment": "Finalement non"},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["resolution_request"] is None
    events = body["resolution_request_events"]
    assert len(events) == 2
    assert events[0]["event_type"] == "canceled"
    assert events[0]["actor_display_name"]
    assert events[1]["event_type"] == "created"


def test_director_can_approve_manager_request_via_api(api_client):
    owner, signal, manager, director = _setup_manager_director_signal()
    manager_token = login(api_client, user=manager.user)
    director_token = login(api_client, user=director.user)

    create_response = api_client.post(
        signal_detail_url(owner.establishment_id, signal.id) + "resolution-requests/",
        {},
        format="json",
        **auth_headers(manager_token),
    )
    request_id = create_response.json()["resolution_request"]["id"]

    response = api_client.post(
        signal_detail_url(owner.establishment_id, signal.id)
        + f"resolution-requests/{request_id}/approve/",
        {"review_comment": "OK"},
        format="json",
        **auth_headers(director_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"
    assert body["resolution_request"] is None
    events = body["resolution_request_events"]
    assert len(events) == 2
    assert events[0]["event_type"] == "approved"
    assert events[1]["event_type"] == "created"


def test_reject_then_recreate_builds_incremental_history(api_client):
    owner, signal, manager, director = _setup_manager_director_signal()
    manager_token = login(api_client, user=manager.user)
    director_token = login(api_client, user=director.user)
    base = signal_detail_url(owner.establishment_id, signal.id)

    create_response = api_client.post(
        base + "resolution-requests/",
        {},
        format="json",
        **auth_headers(manager_token),
    )
    first_id = create_response.json()["resolution_request"]["id"]

    reject_response = api_client.post(
        base + f"resolution-requests/{first_id}/reject/",
        {},
        format="json",
        **auth_headers(director_token),
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["resolution_request"] is None

    recreate_response = api_client.post(
        base + "resolution-requests/",
        {},
        format="json",
        **auth_headers(manager_token),
    )
    assert recreate_response.status_code == 201
    body = recreate_response.json()
    assert body["resolution_request"]["status"] == SignalResolutionRequest.Status.PENDING
    events = body["resolution_request_events"]
    assert len(events) >= 3
    assert events[0]["event_type"] == "created"
    assert events[0]["request_id"] == body["resolution_request"]["id"]
    assert [event["event_type"] for event in events] == ["created", "rejected", "created"]
    occurred = [event["occurred_at"] for event in events]
    assert occurred == sorted(occurred, reverse=True)
