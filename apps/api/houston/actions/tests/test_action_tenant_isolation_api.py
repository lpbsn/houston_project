from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.tests.conftest import (
    action_url,
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    create_free_action_payload,
    execution_feed_url,
    login,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import build_api_membership as build_foreign_membership
from houston.testing.taxonomy import hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _feed_query(view_mode: str) -> str:
    return f"?view_mode={view_mode}"


def _create_action_via_api(api_client, *, owner, staff, maintenance):
    token = login(api_client, user=owner.user)
    response = api_client.post(
        f"/api/v1/establishments/{owner.establishment_id}/actions/",
        create_free_action_payload(
            membership=owner,
            responsible_business_unit=maintenance,
            assigned_to=staff,
        ),
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201, response.json()
    return response.json()["id"]


@pytest.fixture
def cross_establishment_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action_id = _create_action_via_api(
        api_client,
        owner=owner,
        staff=staff,
        maintenance=maintenance,
    )
    foreign_token = login(api_client, user=foreign.user)
    return {
        "owner": owner,
        "foreign": foreign,
        "staff": staff,
        "maintenance": maintenance,
        "action_id": action_id,
        "foreign_token": foreign_token,
    }


def test_action_detail_cross_establishment_returns_404(api_client, cross_establishment_action):
    foreign = cross_establishment_action["foreign"]
    action_id = cross_establishment_action["action_id"]
    token = cross_establishment_action["foreign_token"]

    response = api_client.get(
        action_url(foreign.establishment_id, action_id),
        **auth_headers(token),
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "suffix",
    [
        "accept/",
        "mark-done/",
        "validate/",
        "reopen/",
        "cancel/",
    ],
)
def test_action_command_cross_establishment_returns_404(
    api_client,
    cross_establishment_action,
    suffix,
):
    foreign = cross_establishment_action["foreign"]
    action_id = cross_establishment_action["action_id"]
    token = cross_establishment_action["foreign_token"]

    response = api_client.post(
        action_url(foreign.establishment_id, action_id, suffix),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_reassign_cross_establishment_returns_404(api_client, cross_establishment_action):
    foreign = cross_establishment_action["foreign"]
    staff = cross_establishment_action["staff"]
    action_id = cross_establishment_action["action_id"]
    token = cross_establishment_action["foreign_token"]

    response = api_client.post(
        action_url(foreign.establishment_id, action_id, "reassign/"),
        {"assignee_ids": [str(staff.id)]},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_due_at_cross_establishment_returns_404(api_client, cross_establishment_action):
    foreign = cross_establishment_action["foreign"]
    action_id = cross_establishment_action["action_id"]
    token = cross_establishment_action["foreign_token"]
    new_due = (timezone.now() + timezone.timedelta(days=3)).isoformat()

    response = api_client.patch(
        action_url(foreign.establishment_id, action_id, "due-at/"),
        {"due_at": new_due},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_execution_feed_does_not_include_foreign_establishment_action(
    api_client,
    cross_establishment_action,
):
    owner = cross_establishment_action["owner"]
    foreign = cross_establishment_action["foreign"]
    action_id = cross_establishment_action["action_id"]
    token = cross_establishment_action["foreign_token"]

    owner_token = login(api_client, user=owner.user)
    owner_feed = api_client.get(
        execution_feed_url(owner.establishment_id) + _feed_query("general"),
        **auth_headers(owner_token),
    )
    assert owner_feed.status_code == 200
    owner_action_ids = {
        item["action"]["id"]
        for item in owner_feed.json()["items"]
        if item.get("item_type") == "action" and item.get("action")
    }
    assert action_id in owner_action_ids

    foreign_feed = api_client.get(
        execution_feed_url(foreign.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    assert foreign_feed.status_code == 200
    foreign_action_ids = {
        item["action"]["id"]
        for item in foreign_feed.json()["items"]
        if item.get("item_type") == "action" and item.get("action")
    }
    assert action_id not in foreign_action_ids


def test_in_progress_action_command_cross_establishment_returns_404(api_client):
    """State-specific commands still 404 when action belongs to another establishment."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action_id = _create_action_via_api(
        api_client,
        owner=owner,
        staff=staff,
        maintenance=maintenance,
    )

    staff_token = login(api_client, user=staff.user)
    accept = api_client.post(
        action_url(owner.establishment_id, action_id, "accept/"),
        **auth_headers(staff_token),
    )
    assert accept.status_code == 200
    assert accept.json()["status"] == Action.Status.IN_PROGRESS

    foreign_token = login(api_client, user=foreign.user)
    mark_done = api_client.post(
        action_url(foreign.establishment_id, action_id, "mark-done/"),
        **auth_headers(foreign_token),
    )
    assert mark_done.status_code == 404
