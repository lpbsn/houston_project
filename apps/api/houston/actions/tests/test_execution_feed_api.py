from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.services import create_action
from houston.actions.tests.conftest import (
    assign_domain_scope,
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    execution_feed_url,
    login,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.tests.conftest import create_taxonomy

pytestmark = pytest.mark.django_db


def _feed_query(view_mode: str) -> str:
    return f"?view_mode={view_mode}"


def _create_action_for(owner, *, assigned_to, module, domain, subject, title: str):
    return create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title=title,
        instruction="Instruction text",
        assigned_to_id=assigned_to.id,
        due_at=timezone.now() + timezone.timedelta(days=2),
        module_key=module.key,
        domain_key=domain.key,
        subject_key=subject.key,
    )


def test_execution_feed_response_contract(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=owner.user)
    response = api_client.get(
        execution_feed_url(owner.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "next_cursor" in body
    assert "has_more" in body


@pytest.mark.parametrize("query", ["", "?view_mode=invalid", "?view_mode="])
def test_execution_feed_requires_valid_view_mode(api_client, query):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=owner.user)
    response = api_client.get(
        execution_feed_url(owner.establishment_id) + query,
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_staff_sees_only_assigned_actions(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    module, domain, subject = create_taxonomy(owner.establishment)
    assign_domain_scope(staff, domain)

    assigned = _create_action_for(
        owner,
        assigned_to=staff,
        module=module,
        domain=domain,
        subject=subject,
        title="Assigned to staff",
    )
    _create_action_for(
        owner,
        assigned_to=other_staff,
        module=module,
        domain=domain,
        subject=subject,
        title="Assigned to other",
    )

    token = login(api_client, user=staff.user)
    for view_mode in ("personal", "general"):
        response = api_client.get(
            execution_feed_url(staff.establishment_id) + _feed_query(view_mode),
            **auth_headers(token),
        )
        assert response.status_code == 200
        ids = {item["action"]["id"] for item in response.json()["items"]}
        assert str(assigned.id) in ids
        assert len(ids) == 1


def test_staff_does_not_see_in_scope_unassigned_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    module, domain, subject = create_taxonomy(owner.establishment)
    assign_domain_scope(staff, domain)

    in_scope_unassigned = _create_action_for(
        owner,
        assigned_to=other,
        module=module,
        domain=domain,
        subject=subject,
        title="In scope not assigned",
    )

    token = login(api_client, user=staff.user)
    for view_mode in ("personal", "general"):
        response = api_client.get(
            execution_feed_url(staff.establishment_id) + _feed_query(view_mode),
            **auth_headers(token),
        )
        assert response.status_code == 200
        ids = {item["action"]["id"] for item in response.json()["items"]}
        assert str(in_scope_unassigned.id) not in ids


def test_manager_sees_action_in_scope_only_in_general_view(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    module, domain, subject = create_taxonomy(owner.establishment)
    assign_domain_scope(manager, domain)

    scoped_action = _create_action_for(
        owner,
        assigned_to=staff,
        module=module,
        domain=domain,
        subject=subject,
        title="Scoped for manager",
    )

    token = login(api_client, user=manager.user)
    general = api_client.get(
        execution_feed_url(manager.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    assert general.status_code == 200
    general_ids = {item["action"]["id"] for item in general.json()["items"]}
    assert str(scoped_action.id) in general_ids

    personal = api_client.get(
        execution_feed_url(manager.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    assert personal.status_code == 200
    personal_ids = {item["action"]["id"] for item in personal.json()["items"]}
    assert str(scoped_action.id) not in personal_ids


def test_manager_sees_own_created_action_in_personal_view(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    module, domain, subject = create_taxonomy(owner.establishment)
    assign_domain_scope(manager, domain)

    created_by_manager = create_action(
        establishment_id=owner.establishment_id,
        created_by=manager,
        title="Created by manager",
        instruction="Instruction text",
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=2),
        module_key=module.key,
        domain_key=domain.key,
        subject_key=subject.key,
    )

    token = login(api_client, user=manager.user)
    for view_mode in ("personal", "general"):
        response = api_client.get(
            execution_feed_url(manager.establishment_id) + _feed_query(view_mode),
            **auth_headers(token),
        )
        assert response.status_code == 200
        ids = {item["action"]["id"] for item in response.json()["items"]}
        assert str(created_by_manager.id) in ids


def test_owner_general_includes_unassigned_third_party_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    module, domain, subject = create_taxonomy(owner.establishment)

    third_party = _create_action_for(
        owner,
        assigned_to=staff,
        module=module,
        domain=domain,
        subject=subject,
        title="Not involving owner",
    )

    token = login(api_client, user=owner.user)
    general = api_client.get(
        execution_feed_url(owner.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    assert general.status_code == 200
    assert str(third_party.id) in {item["action"]["id"] for item in general.json()["items"]}

    personal = api_client.get(
        execution_feed_url(owner.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    assert personal.status_code == 200
    assert str(third_party.id) not in {item["action"]["id"] for item in personal.json()["items"]}


def test_detail_shows_done_action_not_in_feed(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    module, domain, subject = create_taxonomy(owner.establishment)
    action = _create_action_for(
        owner,
        assigned_to=staff,
        module=module,
        domain=domain,
        subject=subject,
        title="Will complete",
    )
    from houston.actions.services import accept_action, mark_action_done, validate_action

    action = accept_action(action=action)
    action = mark_action_done(action=action)
    action = validate_action(action=action)

    token = login(api_client, user=staff.user)
    feed = api_client.get(
        execution_feed_url(staff.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    feed_ids = {item["action"]["id"] for item in feed.json()["items"]}
    assert str(action.id) not in feed_ids

    detail = api_client.get(
        f"/api/v1/establishments/{staff.establishment_id}/actions/{action.id}/",
        **auth_headers(token),
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == Action.Status.DONE
