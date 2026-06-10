from __future__ import annotations

import pytest

from houston.actions.models import Action
from houston.actions.tests.conftest import (
    action_url,
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    create_free_action_payload,
    login,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.factories import build_membership
from houston.testing.taxonomy import hotel_maintenance_setup

pytestmark = pytest.mark.django_db


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


def test_assignee_lifecycle_accept_mark_done_validate(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
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

    mark_done = api_client.post(
        action_url(owner.establishment_id, action_id, "mark-done/"),
        **auth_headers(staff_token),
    )
    assert mark_done.status_code == 200
    assert mark_done.json()["status"] == Action.Status.PENDING_VALIDATION

    owner_token = login(api_client, user=owner.user)
    validate = api_client.post(
        action_url(owner.establishment_id, action_id, "validate/"),
        **auth_headers(owner_token),
    )
    assert validate.status_code == 200
    assert validate.json()["status"] == Action.Status.DONE
    hints = validate.json()["permission_hints"]
    assert hints["can_validate"] is False
    assert hints["can_reopen"] is True


def test_staff_cannot_accept_action_assigned_to_peer(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action_id = _create_action_via_api(
        api_client,
        owner=owner,
        staff=staff,
        maintenance=maintenance,
    )

    token = login(api_client, user=other_staff.user)
    response = api_client.post(
        action_url(owner.establishment_id, action_id, "accept/"),
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_owner_can_reopen_and_cancel(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action_id = _create_action_via_api(
        api_client,
        owner=owner,
        staff=staff,
        maintenance=maintenance,
    )

    staff_token = login(api_client, user=staff.user)
    api_client.post(
        action_url(owner.establishment_id, action_id, "accept/"),
        **auth_headers(staff_token),
    )
    api_client.post(
        action_url(owner.establishment_id, action_id, "mark-done/"),
        **auth_headers(staff_token),
    )

    owner_token = login(api_client, user=owner.user)
    reopen = api_client.post(
        action_url(owner.establishment_id, action_id, "reopen/"),
        **auth_headers(owner_token),
    )
    assert reopen.status_code == 200
    assert reopen.json()["status"] == Action.Status.REOPENED

    cancel = api_client.post(
        action_url(owner.establishment_id, action_id, "cancel/"),
        **auth_headers(owner_token),
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == Action.Status.CANCELED


def test_owner_can_reassign_open_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action_id = _create_action_via_api(
        api_client,
        owner=owner,
        staff=staff,
        maintenance=maintenance,
    )

    owner_token = login(api_client, user=owner.user)
    response = api_client.post(
        action_url(owner.establishment_id, action_id, "reassign/"),
        {"assigned_to": str(other_staff.id)},
        format="json",
        **auth_headers(owner_token),
    )
    assert response.status_code == 200
    assert response.json()["assigned_to_display_name"] == other_staff.user.username


def test_foreign_establishment_returns_not_found(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action_id = _create_action_via_api(
        api_client,
        owner=owner,
        staff=staff,
        maintenance=maintenance,
    )

    token = login(api_client, user=foreign.user)
    response = api_client.post(
        action_url(foreign.establishment_id, action_id, "accept/"),
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_staff_cannot_accept_after_action_is_done(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action_id = _create_action_via_api(
        api_client,
        owner=owner,
        staff=staff,
        maintenance=maintenance,
    )

    staff_token = login(api_client, user=staff.user)
    api_client.post(
        action_url(owner.establishment_id, action_id, "accept/"),
        **auth_headers(staff_token),
    )
    api_client.post(
        action_url(owner.establishment_id, action_id, "mark-done/"),
        **auth_headers(staff_token),
    )
    owner_token = login(api_client, user=owner.user)
    api_client.post(
        action_url(owner.establishment_id, action_id, "validate/"),
        **auth_headers(owner_token),
    )

    response = api_client.post(
        action_url(owner.establishment_id, action_id, "accept/"),
        **auth_headers(staff_token),
    )
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
