from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.tests.conftest import (
    action_url,
    actions_url,
    assign_domain_scope,
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    create_action_payload,
    create_signal_for_membership,
    create_taxonomy,
    login,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal

pytestmark = pytest.mark.django_db


def test_manager_update_due_at_only_own_created(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    module, domain, subject = create_taxonomy(owner.establishment)
    assign_domain_scope(manager, domain)

    token_manager = login(api_client, user=manager.user)
    own_payload = create_action_payload(
        membership=manager,
        module_key=module.key,
        domain_key=domain.key,
        subject_key=subject.key,
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
    other_payload = create_action_payload(
        membership=owner,
        assigned_to=manager,
        module_key=module.key,
        domain_key=domain.key,
        subject_key=subject.key,
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


def test_staff_cannot_create_action(api_client):
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    token = login(api_client, user=staff.user)
    payload = create_action_payload(membership=staff)
    response = api_client.post(
        actions_url(staff.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 403


def test_create_free_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=owner.user)
    payload = create_action_payload(membership=owner)
    response = api_client.post(
        actions_url(owner.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["status"] == Action.Status.OPEN
    assert response.json()["signal_summary"] is None


def test_create_linked_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner)
    token = login(api_client, user=owner.user)
    payload = create_action_payload(membership=owner, signal=signal)
    response = api_client.post(
        actions_url(owner.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["signal_summary"]["id"] == str(signal.id)


def test_linked_action_signal_summary_includes_urgency(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner)
    signal.urgency = Signal.Urgency.HIGH
    signal.save(update_fields=["urgency"])

    token = login(api_client, user=owner.user)
    payload = create_action_payload(membership=owner, signal=signal)
    response = api_client.post(
        actions_url(owner.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["signal_summary"]["urgency"] == Signal.Urgency.HIGH
