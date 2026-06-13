from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.services import create_action
from houston.actions.tests.conftest import (
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    execution_feed_url,
    login,
)
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.services import create_checklist_assignment, create_checklist_template
from houston.checklists.tests.conftest import add_task_template, stable_assignment_times
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def _feed_query(view_mode: str, **params: str | int) -> str:
    query = f"?view_mode={view_mode}"
    for key, value in params.items():
        query += f"&{key}={value}"
    return query


def _scoped_staff(owner, business_unit):
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=staff,
        business_unit=business_unit,
    )
    return staff


def _active_template(owner, business_unit):
    template = create_checklist_template(
        establishment_id=owner.establishment_id,
        actor=owner,
        title="Routine",
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    return template


def _create_action(owner, *, assigned_to, business_unit, title: str):
    return create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title=title,
        instruction="Instruction text",
        assigned_to_id=assigned_to.id,
        due_at=timezone.now(),
        responsible_business_unit_id=business_unit.id,
    )


def _item_ids(body: dict) -> list[str]:
    ids: list[str] = []
    for item in body["items"]:
        if item["item_type"] == "action":
            ids.append(item["action"]["id"])
        else:
            ids.append(item["checklist"]["id"])
    return ids


def _assert_has_more_implies_cursor(body: dict) -> None:
    if body["has_more"]:
        assert body["next_cursor"] is not None


def test_execution_feed_invalid_cursor_returns_validation_error(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=owner.user)
    response = api_client.get(
        execution_feed_url(owner.establishment_id)
        + _feed_query("general", cursor="not-valid"),
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_execution_feed_action_only_pagination(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff(owner, business_unit)
    for index in range(15):
        _create_action(
            owner,
            assigned_to=staff,
            business_unit=business_unit,
            title=f"Action {index}",
        )

    token = login(api_client, user=staff.user)
    page_size = 10
    page_one = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size),
        **auth_headers(token),
    )
    assert page_one.status_code == 200
    body_one = page_one.json()
    assert len(body_one["items"]) == page_size
    assert all(item["item_type"] == "action" for item in body_one["items"])
    _assert_has_more_implies_cursor(body_one)
    assert body_one["has_more"] is True

    page_two = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size, cursor=body_one["next_cursor"]),
        **auth_headers(token),
    )
    assert page_two.status_code == 200
    body_two = page_two.json()
    assert len(body_two["items"]) == 5
    assert set(_item_ids(body_one)).isdisjoint(set(_item_ids(body_two)))


def test_execution_feed_checklist_only_pagination(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff(owner, business_unit)
    template = _active_template(owner, business_unit)
    now = timezone.now()
    for _ in range(5):
        create_checklist_assignment(
            template=template,
            actor=owner,
            assigned_to_id=staff.id,
            start_date=now.date(),
            end_date=now.date(),
            start_at=stable_assignment_times(duration_hours=2)[0],
            end_at=stable_assignment_times(duration_hours=2)[1],
        )

    token = login(api_client, user=staff.user)
    page_size = 2
    page_one = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size),
        **auth_headers(token),
    )
    body_one = page_one.json()
    assert len(body_one["items"]) == page_size
    assert all(item["item_type"] == "checklist" for item in body_one["items"])
    _assert_has_more_implies_cursor(body_one)

    page_two = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size, cursor=body_one["next_cursor"]),
        **auth_headers(token),
    )
    body_two = page_two.json()
    assert len(body_two["items"]) == page_size
    assert set(_item_ids(body_one)).isdisjoint(set(_item_ids(body_two)))


def test_execution_feed_mixed_pagination(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff(owner, business_unit)
    template = _active_template(owner, business_unit)
    now = timezone.now()
    for _ in range(2):
        create_checklist_assignment(
            template=template,
            actor=owner,
            assigned_to_id=staff.id,
            start_date=now.date(),
            end_date=now.date(),
            start_at=stable_assignment_times(duration_hours=2)[0],
            end_at=stable_assignment_times(duration_hours=2)[1],
        )
    for index in range(30):
        action = _create_action(
            owner,
            assigned_to=staff,
            business_unit=business_unit,
            title=f"Action {index}",
        )
        Action.objects.filter(id=action.id).update(last_activity_at=now)

    token = login(api_client, user=staff.user)
    page_size = 25
    page_one = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size),
        **auth_headers(token),
    )
    body_one = page_one.json()
    checklist_count = sum(1 for item in body_one["items"] if item["item_type"] == "checklist")
    action_count = sum(1 for item in body_one["items"] if item["item_type"] == "action")
    assert checklist_count == 2
    assert action_count == 23
    _assert_has_more_implies_cursor(body_one)

    page_two = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size, cursor=body_one["next_cursor"]),
        **auth_headers(token),
    )
    body_two = page_two.json()
    assert all(item["item_type"] == "action" for item in body_two["items"])
    assert len(body_two["items"]) == 7
    assert set(_item_ids(body_one)).isdisjoint(set(_item_ids(body_two)))


def test_execution_feed_exact_page_size_checklists_transitions_to_action_start(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff(owner, business_unit)
    template = _active_template(owner, business_unit)
    now = timezone.now()
    page_size = 2
    for _ in range(page_size):
        create_checklist_assignment(
            template=template,
            actor=owner,
            assigned_to_id=staff.id,
            start_date=now.date(),
            end_date=now.date(),
            start_at=stable_assignment_times(duration_hours=2)[0],
            end_at=stable_assignment_times(duration_hours=2)[1],
        )
    action = _create_action(
        owner,
        assigned_to=staff,
        business_unit=business_unit,
        title="Overflow action",
    )

    token = login(api_client, user=staff.user)
    page_one = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size),
        **auth_headers(token),
    )
    body_one = page_one.json()
    assert len(body_one["items"]) == page_size
    assert all(item["item_type"] == "checklist" for item in body_one["items"])
    assert body_one["has_more"] is True
    assert body_one["next_cursor"] is not None

    page_two = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size, cursor=body_one["next_cursor"]),
        **auth_headers(token),
    )
    body_two = page_two.json()
    assert len(body_two["items"]) == 1
    assert body_two["items"][0]["item_type"] == "action"
    assert body_two["items"][0]["action"]["id"] == str(action.id)


def test_execution_feed_action_phase_start_returns_first_action(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff(owner, business_unit)
    template = _active_template(owner, business_unit)
    now = timezone.now()
    page_size = 2
    for _ in range(3):
        create_checklist_assignment(
            template=template,
            actor=owner,
            assigned_to_id=staff.id,
            start_date=now.date(),
            end_date=now.date(),
            start_at=stable_assignment_times(duration_hours=2)[0],
            end_at=stable_assignment_times(duration_hours=2)[1],
        )
    first_action = _create_action(
        owner,
        assigned_to=staff,
        business_unit=business_unit,
        title="First action",
    )
    _create_action(
        owner,
        assigned_to=staff,
        business_unit=business_unit,
        title="Second action",
    )

    token = login(api_client, user=staff.user)
    page_one = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size),
        **auth_headers(token),
    )
    body_one = page_one.json()
    assert body_one["has_more"] is True

    page_two = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size, cursor=body_one["next_cursor"]),
        **auth_headers(token),
    )
    body_two = page_two.json()
    action_ids = [item["action"]["id"] for item in body_two["items"] if item["item_type"] == "action"]
    assert str(first_action.id) in action_ids
    assert set(_item_ids(body_one)).isdisjoint(set(action_ids))


def test_execution_feed_stable_tie_breaker_by_id(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff(owner, business_unit)
    shared_time = timezone.now()
    created_actions = []
    for index in range(4):
        action = _create_action(
            owner,
            assigned_to=staff,
            business_unit=business_unit,
            title=f"Tied action {index}",
        )
        Action.objects.filter(id=action.id).update(
            last_activity_at=shared_time,
            created_at=shared_time,
        )
        created_actions.append(action)

    token = login(api_client, user=staff.user)
    page_size = 2
    page_one = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal", page_size=page_size),
        **auth_headers(token),
    )
    page_two = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query(
            "personal",
            page_size=page_size,
            cursor=page_one.json()["next_cursor"],
        ),
        **auth_headers(token),
    )
    all_ids = _item_ids(page_one.json()) + _item_ids(page_two.json())
    assert len(all_ids) == len(set(all_ids))
    assert len(all_ids) == 4


def test_execution_feed_pagination_personal_general_regression(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    assigned = _create_action(
        owner,
        assigned_to=staff,
        business_unit=business_unit,
        title="Assigned action",
    )
    token = login(api_client, user=staff.user)
    for view_mode in ("personal", "general"):
        response = api_client.get(
            execution_feed_url(staff.establishment_id) + _feed_query(view_mode, page_size=10),
            **auth_headers(token),
        )
        assert response.status_code == 200
        ids = {item["action"]["id"] for item in response.json()["items"]}
        assert str(assigned.id) in ids


@pytest.mark.parametrize("page_size", [10])
def test_execution_feed_has_more_implies_next_cursor(api_client, page_size):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff(owner, business_unit)
    for index in range(12):
        _create_action(
            owner,
            assigned_to=staff,
            business_unit=business_unit,
            title=f"Action {index}",
        )

    token = login(api_client, user=staff.user)
    cursor = None
    seen_ids: set[str] = set()
    for _ in range(3):
        query = _feed_query("personal", page_size=page_size)
        if cursor is not None:
            query += f"&cursor={cursor}"
        response = api_client.get(
            execution_feed_url(staff.establishment_id) + query,
            **auth_headers(token),
        )
        body = response.json()
        _assert_has_more_implies_cursor(body)
        page_ids = set(_item_ids(body))
        assert page_ids.isdisjoint(seen_ids)
        seen_ids |= page_ids
        if not body["has_more"]:
            break
        cursor = body["next_cursor"]
    assert len(seen_ids) == 12
