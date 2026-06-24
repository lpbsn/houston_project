from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.services import create_action
from houston.actions.tests.conftest import (
    assign_business_unit_scope,
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    execution_feed_url,
    login,
)
from houston.establishments.models import BusinessUnit, EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)

pytestmark = pytest.mark.django_db


def _feed_query(view_mode: str) -> str:
    return f"?view_mode={view_mode}"


def _hotel_maintenance_setup(establishment):
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
    )
    maintenance = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.TRANSVERSAL,
    )
    electricite = create_activity_subject(
        establishment=establishment,
        business_unit=maintenance,
        label="Électricité",
    )
    return hotel, maintenance, electricite


def _create_free_action_for(
    owner,
    *,
    assigned_to,
    responsible_business_unit,
    title: str,
):
    return create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title=title,
        instruction="Instruction text",
        assignee_ids=[assigned_to.id],
        due_at=timezone.now() + timezone.timedelta(days=2),
        responsible_business_unit_id=responsible_business_unit.id,
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
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, hotel)

    assigned = _create_free_action_for(
        owner,
        assigned_to=staff,
        responsible_business_unit=hotel,
        title="Assigned to staff",
    )
    _create_free_action_for(
        owner,
        assigned_to=other_staff,
        responsible_business_unit=hotel,
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
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, hotel)

    in_scope_unassigned = _create_free_action_for(
        owner,
        assigned_to=other,
        responsible_business_unit=hotel,
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


def test_manager_sees_free_action_in_responsible_scope_only_in_general_view(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager, maintenance)

    scoped_action = _create_free_action_for(
        owner,
        assigned_to=staff,
        responsible_business_unit=maintenance,
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


def test_manager_sees_linked_action_via_affected_scope(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager_hotel = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager_hotel, hotel)

    from houston.actions.tests.conftest import create_signal_v3_for_membership

    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    linked = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked scoped",
        instruction="Work",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )

    token = login(api_client, user=manager_hotel.user)
    response = api_client.get(
        execution_feed_url(manager_hotel.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    item = response.json()["items"][0]["action"]
    assert item["id"] == str(linked.id)
    assert item["affected_business_unit_key"] == "hotel"
    assert item["responsible_business_unit_key"] == "maintenance"


def test_manager_sees_own_created_action_in_personal_view(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager, maintenance)

    created_by_manager = create_action(
        establishment_id=owner.establishment_id,
        created_by=manager,
        title="Created by manager",
        instruction="Instruction text",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=2),
        responsible_business_unit_id=maintenance.id,
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


def test_owner_personal_includes_action_they_created_even_when_assigned_to_staff(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)

    third_party = _create_free_action_for(
        owner,
        assigned_to=staff,
        responsible_business_unit=hotel,
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
    assert str(third_party.id) in {item["action"]["id"] for item in personal.json()["items"]}


def test_detail_shows_done_action_not_in_feed(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    action = _create_free_action_for(
        owner,
        assigned_to=staff,
        responsible_business_unit=hotel,
        title="Will complete",
    )
    from houston.actions.services import accept_action, mark_action_done, validate_action

    action = accept_action(action_id=action.id, accepted_by=staff)
    action = mark_action_done(action_id=action.id, actor_membership=staff)
    action = validate_action(action_id=action.id, actor_membership=owner)

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


def test_multi_assignee_action_appears_once_in_feed(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff_a = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    staff_b = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)

    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Shared task",
        instruction="Instruction text",
        assignee_ids=[staff_a.id, staff_b.id],
        due_at=timezone.now() + timezone.timedelta(days=2),
        responsible_business_unit_id=hotel.id,
    )

    for staff in (staff_a, staff_b):
        token = login(api_client, user=staff.user)
        response = api_client.get(
            execution_feed_url(staff.establishment_id) + _feed_query("personal"),
            **auth_headers(token),
        )
        assert response.status_code == 200
        action_ids = [item["action"]["id"] for item in response.json()["items"]]
        assert action_ids.count(str(action.id)) == 1


def test_execution_feed_query_count_baseline_empty(api_client):
    """Phase G: empty feed without dual count(); scoped materialization (DB-01)."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=owner.user)
    url = execution_feed_url(owner.establishment_id) + _feed_query("general")

    from houston.testing.query_baseline import (
        EXECUTION_FEED_EMPTY_MAX_QUERIES,
        assert_query_count_at_most,
        capture_queries,
    )

    with capture_queries() as context:
        response = api_client.get(url, **auth_headers(token))

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert_query_count_at_most(
        context,
        max_queries=EXECUTION_FEED_EMPTY_MAX_QUERIES,
        label="execution_feed_general_empty",
    )


def test_execution_feed_query_count_with_three_actions(api_client):
    """Post ACT-01: permission hints should not N+1 assignee exists queries."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    for index in range(3):
        _create_free_action_for(
            owner,
            assigned_to=staff,
            responsible_business_unit=hotel,
            title=f"Feed query action {index}",
        )

    token = login(api_client, user=owner.user)
    url = execution_feed_url(owner.establishment_id) + _feed_query("general")

    from houston.testing.query_baseline import (
        EXECUTION_FEED_THREE_ACTIONS_MAX_QUERIES,
        assert_query_count_at_most,
        capture_queries,
    )

    with capture_queries() as context:
        response = api_client.get(url, **auth_headers(token))

    assert response.status_code == 200
    action_items = [item for item in response.json()["items"] if item["item_type"] == "action"]
    assert len(action_items) == 3
    assert_query_count_at_most(
        context,
        max_queries=EXECUTION_FEED_THREE_ACTIONS_MAX_QUERIES,
        label="execution_feed_general_three_actions",
    )


FEED_PERMISSION_HINT_KEYS = frozenset(
    {
        "can_accept",
        "can_mark_done",
        "can_validate",
        "can_reopen",
        "can_cancel",
        "can_reassign",
        "can_update_due_at",
        "is_assignee",
        "accepted_by_me",
    }
)


def test_execution_feed_action_item_includes_permission_hints(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = _hotel_maintenance_setup(owner.establishment)
    _create_free_action_for(
        owner,
        assigned_to=staff,
        responsible_business_unit=hotel,
        title="Feed hints action",
    )

    token = login(api_client, user=staff.user)
    response = api_client.get(
        execution_feed_url(staff.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    action_items = [item for item in response.json()["items"] if item["item_type"] == "action"]
    assert len(action_items) == 1
    hints = action_items[0]["action"]["permission_hints"]
    assert set(hints.keys()) == FEED_PERMISSION_HINT_KEYS
    assert hints["is_assignee"] is True
    assert hints["can_accept"] is True
    assert hints["accepted_by_me"] is False
