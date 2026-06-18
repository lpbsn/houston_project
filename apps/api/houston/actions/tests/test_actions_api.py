from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.tests.conftest import (
    action_url,
    actions_url,
    assign_business_unit_scope,
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    create_free_action_payload,
    create_linked_action_payload,
    create_signal_v3_for_membership,
    login,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.taxonomy import (
    create_business_unit,
    hotel_maintenance_setup,
)

pytestmark = pytest.mark.django_db


def test_manager_update_due_at_only_own_created(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager, maintenance)

    token_manager = login(api_client, user=manager.user)
    own_payload = create_free_action_payload(
        membership=manager,
        responsible_business_unit=maintenance,
    )
    create_resp = api_client.post(
        actions_url(manager.establishment_id),
        own_payload,
        format="json",
        **auth_headers(token_manager),
    )
    assert create_resp.status_code == 201
    own_id = create_resp.json()["id"]

    new_due = (timezone.now() + timezone.timedelta(days=3)).isoformat()
    patch_own = api_client.patch(
        action_url(manager.establishment_id, own_id, "due-at/"),
        {"due_at": new_due},
        format="json",
        **auth_headers(token_manager),
    )
    assert patch_own.status_code == 200

    token_owner = login(api_client, user=owner.user)
    other_payload = create_free_action_payload(
        membership=owner,
        responsible_business_unit=maintenance,
        assigned_to=manager,
    )
    other_resp = api_client.post(
        actions_url(owner.establishment_id),
        other_payload,
        format="json",
        **auth_headers(token_owner),
    )
    assert other_resp.status_code == 201
    other_id = other_resp.json()["id"]

    patch_other = api_client.patch(
        action_url(manager.establishment_id, other_id, "due-at/"),
        {"due_at": new_due},
        format="json",
        **auth_headers(token_manager),
    )
    assert patch_other.status_code == 403


def test_staff_can_create_self_assigned_free_action_in_scope(api_client):
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(staff.establishment)
    assign_business_unit_scope(staff, maintenance)
    token = login(api_client, user=staff.user)
    payload = create_free_action_payload(
        membership=staff,
        responsible_business_unit=maintenance,
    )
    response = api_client.post(
        actions_url(staff.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == Action.Status.OPEN
    assert len(body["assignees"]) == 1
    assert body["assignees"][0]["membership_id"] == str(staff.id)


def test_staff_cannot_create_free_action_out_of_scope(api_client):
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(staff.establishment)
    assign_business_unit_scope(staff, hotel)
    token = login(api_client, user=staff.user)
    payload = create_free_action_payload(
        membership=staff,
        responsible_business_unit=maintenance,
    )
    response = api_client.post(
        actions_url(staff.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Not allowed to create this action."


def test_staff_cannot_create_linked_action_even_in_scope(api_client):
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(staff.establishment)
    assign_business_unit_scope(staff, maintenance)
    signal = create_signal_v3_for_membership(
        staff,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.OPEN,
    )
    token = login(api_client, user=staff.user)
    payload = create_linked_action_payload(
        membership=staff,
        signal=signal,
    )
    response = api_client.post(
        actions_url(staff.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Staff members cannot create linked actions."


def test_staff_cannot_create_free_action_assigned_to_other(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
    token = login(api_client, user=staff.user)
    payload = create_free_action_payload(
        membership=staff,
        responsible_business_unit=maintenance,
        assigned_to=other_staff,
    )
    response = api_client.post(
        actions_url(staff.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Staff members can only create actions assigned to themselves."
    )


def test_staff_cannot_create_multi_assignee_free_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
    token = login(api_client, user=staff.user)
    payload = create_free_action_payload(
        membership=staff,
        responsible_business_unit=maintenance,
        assignees=[staff, other_staff],
    )
    response = api_client.post(
        actions_url(staff.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Staff members can only create actions assigned to themselves."
    )


def test_staff_cannot_create_free_action_without_assignees(api_client):
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(staff.establishment)
    assign_business_unit_scope(staff, maintenance)
    token = login(api_client, user=staff.user)
    payload = create_free_action_payload(
        membership=staff,
        responsible_business_unit=maintenance,
    )
    payload["assignee_ids"] = []
    response = api_client.post(
        actions_url(staff.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400


def test_create_free_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    token = login(api_client, user=owner.user)
    payload = create_free_action_payload(
        membership=owner,
        responsible_business_unit=hotel,
    )
    response = api_client.post(
        actions_url(owner.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == Action.Status.OPEN
    assert body["signal_summary"] is None
    assert body["responsible_business_unit_key"] == "hotel"
    assert body["activity_subject_label"] is None
    assert body["affected_business_unit_key"] is None


def test_create_linked_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    token = login(api_client, user=owner.user)
    payload = create_linked_action_payload(membership=owner, signal=signal)
    response = api_client.post(
        actions_url(owner.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["signal_summary"]["id"] == str(signal.id)
    assert body["affected_business_unit_key"] == "hotel"
    assert body["responsible_business_unit_key"] == "maintenance"
    assert body["activity_subject_normalized_name"] == electricite.normalized_name


def test_linked_action_signal_summary_includes_urgency_and_location(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        location_text="chambre 102",
    )
    signal.urgency = Signal.Urgency.HIGH
    signal.save(update_fields=["urgency"])

    token = login(api_client, user=owner.user)
    payload = create_linked_action_payload(membership=owner, signal=signal)
    response = api_client.post(
        actions_url(owner.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    summary = response.json()["signal_summary"]
    assert summary["urgency"] == Signal.Urgency.HIGH
    assert summary["location_text"] == "chambre 102"


def test_create_rejects_legacy_module_key(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    token = login(api_client, user=owner.user)
    payload = create_free_action_payload(
        membership=owner,
        responsible_business_unit=hotel,
    )
    payload["module_key"] = "hotel"
    response = api_client.post(
        actions_url(owner.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert "legacy" in response.json()["detail"].lower()


def test_manager_affected_sees_linked_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager_hotel = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager_hotel, hotel)

    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    token_owner = login(api_client, user=owner.user)
    create_resp = api_client.post(
        actions_url(owner.establishment_id),
        create_linked_action_payload(membership=owner, signal=signal, assigned_to=staff),
        format="json",
        **auth_headers(token_owner),
    )
    assert create_resp.status_code == 201
    action_id = create_resp.json()["id"]

    token_manager = login(api_client, user=manager_hotel.user)
    detail = api_client.get(
        action_url(manager_hotel.establishment_id, action_id),
        **auth_headers(token_manager),
    )
    assert detail.status_code == 200


def test_manager_out_of_scope_cannot_see_linked_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    bar = create_business_unit(establishment=owner.establishment, key="bar", label="Bar")
    assign_business_unit_scope(outsider, bar)

    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    token_owner = login(api_client, user=owner.user)
    create_resp = api_client.post(
        actions_url(owner.establishment_id),
        create_linked_action_payload(membership=owner, signal=signal, assigned_to=staff),
        format="json",
        **auth_headers(token_owner),
    )
    action_id = create_resp.json()["id"]

    token_outsider = login(api_client, user=outsider.user)
    detail = api_client.get(
        action_url(outsider.establishment_id, action_id),
        **auth_headers(token_outsider),
    )
    assert detail.status_code == 404


def test_manager_free_action_out_of_scope_denied(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager, hotel)

    token = login(api_client, user=manager.user)
    payload = create_free_action_payload(
        membership=manager,
        responsible_business_unit=maintenance,
    )
    response = api_client.post(
        actions_url(manager.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
