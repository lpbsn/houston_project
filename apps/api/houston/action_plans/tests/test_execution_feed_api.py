from __future__ import annotations

from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    RECURRENCE_DAYS,
)
from houston.action_plans.models import ActionPlanAssignee, ActionPlanExecution
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.conftest import (
    action_plan_execution_feed_url,
    auth_headers,
    build_assignee_payload,
    build_schedule_assignee_payload,
    build_task_payload,
    login,
    schedule_window_from_datetime,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import build_api_membership as build_foreign_membership
from houston.testing.factories import create_membership
from houston.testing.taxonomy import create_membership_with_business_unit_scope

pytestmark = pytest.mark.django_db


def _feed_query(view_mode: str, **extra) -> str:
    params = [f"view_mode={view_mode}"]
    for key, value in extra.items():
        params.append(f"{key}={value}")
    return "?" + "&".join(params)


def _execution_ids(body: dict) -> set[str]:
    return {
        item["action_plan_execution"]["id"]
        for item in body["items"]
        if item["item_type"] == "action_plan_execution"
    }


def _create_visible_execution(
    *,
    owner,
    staff,
    business_unit,
    title: str = "Feed execution",
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=business_unit.id,
        title=title,
        requires_validation=False,
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=staff, business_unit=business_unit)],
    )
    return execution


def test_action_plan_execution_feed_response_contract(api_client, owner_membership):
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "next_cursor" in body
    assert "has_more" in body


@pytest.mark.parametrize("query", ["", "?view_mode=invalid", "?view_mode="])
def test_action_plan_execution_feed_requires_valid_view_mode(
    api_client,
    owner_membership,
    query,
):
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + query,
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_feed_item_type_and_involved_poles_always_present(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = ActionPlanExecution.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        title="Solo execution",
        description="No assignees or tasks",
        pilot_business_unit=business_unit,
        status=EXECUTION_STATUS_IN_PROGRESS,
        last_activity_at=timezone.now(),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["item_type"] == "action_plan_execution"
    payload = item["action_plan_execution"]
    assert payload["id"] == str(execution.id)
    assert payload["involved_poles"] == []
    assert "permission_hints" in payload


def test_terminal_executions_excluded_from_feed(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    done_execution = _create_visible_execution(
        owner=owner_membership,
        staff=staff_membership,
        business_unit=business_unit,
        title="Done execution",
    )
    done_execution.status = EXECUTION_STATUS_DONE
    done_execution.save(update_fields=["status", "updated_at"])

    active_execution = _create_visible_execution(
        owner=owner_membership,
        staff=staff_membership,
        business_unit=business_unit,
        title="Active execution",
    )

    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = _execution_ids(response.json())
    assert str(active_execution.id) in ids
    assert str(done_execution.id) not in ids


def test_execution_visible_from_in_future_excluded(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _create_visible_execution(
        owner=owner_membership,
        staff=staff_membership,
        business_unit=business_unit,
    )
    execution.visible_from = timezone.now() + timezone.timedelta(hours=2)
    execution.save(update_fields=["visible_from", "updated_at"])

    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert str(execution.id) not in _execution_ids(response.json())


def test_personal_feed_excludes_assignee_with_future_visible_from(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _create_visible_execution(
        owner=owner_membership,
        staff=staff_membership,
        business_unit=business_unit,
        title="Individual chronology",
    )
    execution.visible_from = timezone.now() - timezone.timedelta(hours=2)
    execution.save(update_fields=["visible_from", "updated_at"])

    assignee = ActionPlanAssignee.objects.get(
        action_plan_execution_id=execution.id,
        membership_id=staff_membership.id,
    )
    assignee.visible_from = timezone.now() + timezone.timedelta(hours=2)
    assignee.save(update_fields=["visible_from", "updated_at"])

    staff_token = login(api_client, user=staff_membership.user)
    personal = api_client.get(
        action_plan_execution_feed_url(staff_membership.establishment_id)
        + _feed_query("personal"),
        **auth_headers(staff_token),
    )
    assert personal.status_code == 200
    assert str(execution.id) not in _execution_ids(personal.json())

    owner_token = login(api_client, user=owner_membership.user)
    general = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general"),
        **auth_headers(owner_token),
    )
    assert general.status_code == 200
    assert str(execution.id) in _execution_ids(general.json())


def test_staff_sees_only_assigned_executions(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    other_staff = create_membership(
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=other_staff,
        business_unit=business_unit,
    )

    assigned = _create_visible_execution(
        owner=owner_membership,
        staff=staff_membership,
        business_unit=business_unit,
        title="Assigned",
    )
    other = _create_visible_execution(
        owner=owner_membership,
        staff=other_staff,
        business_unit=business_unit,
        title="Other staff",
    )

    token = login(api_client, user=staff_membership.user)
    for view_mode in ("personal", "general"):
        response = api_client.get(
            action_plan_execution_feed_url(staff_membership.establishment_id)
            + _feed_query(view_mode),
            **auth_headers(token),
        )
        assert response.status_code == 200
        ids = _execution_ids(response.json())
        assert str(assigned.id) in ids
        assert str(other.id) not in ids


def test_manager_sees_scoped_execution_in_general_only(
    api_client,
    owner_membership,
    manager_membership,
    staff_membership,
    business_unit,
):
    scoped = _create_visible_execution(
        owner=owner_membership,
        staff=staff_membership,
        business_unit=business_unit,
        title="Restaurant scoped",
    )

    token = login(api_client, user=manager_membership.user)
    general = api_client.get(
        action_plan_execution_feed_url(manager_membership.establishment_id)
        + _feed_query("general"),
        **auth_headers(token),
    )
    assert general.status_code == 200
    assert str(scoped.id) in _execution_ids(general.json())

    personal = api_client.get(
        action_plan_execution_feed_url(manager_membership.establishment_id)
        + _feed_query("personal"),
        **auth_headers(token),
    )
    assert personal.status_code == 200
    assert str(scoped.id) not in _execution_ids(personal.json())


def test_manager_general_feed_materializes_cross_pole_schedule_with_scoped_task(
    api_client,
    owner_membership,
    contributor_manager_membership,
    cross_pole_catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, period_days=14)
    schedule = create_action_plan_schedule(
        action_plan=cross_pole_catalog_action_plan,
        actor=owner_membership,
        recurrence_days=sorted(RECURRENCE_DAYS),
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    schedule.last_materialized_at = None
    schedule.save(update_fields=["last_materialized_at", "updated_at"])

    assert not ActionPlanExecution.objects.filter(action_plan_schedule=schedule).exists()

    token = login(api_client, user=contributor_manager_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(contributor_manager_membership.establishment_id)
        + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert _execution_ids(response.json())
    assert ActionPlanExecution.objects.filter(action_plan_schedule=schedule).exists()


def test_feed_pagination_cursor(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    executions = []
    base_time = timezone.now()
    for index in range(3):
        _, execution = create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title=f"Execution {index}",
            requires_validation=False,
            tasks=[build_task_payload(task=f"Task {index}", business_unit=business_unit)],
            assignees=[
                build_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        )
        execution.last_activity_at = base_time - timezone.timedelta(minutes=index)
        execution.save(update_fields=["last_activity_at", "updated_at"])
        executions.append(execution)

    token = login(api_client, user=owner_membership.user)
    first = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general", page_size=2),
        **auth_headers(token),
    )
    assert first.status_code == 200
    first_body = first.json()
    assert len(first_body["items"]) == 2
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]

    second = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general", page_size=2, cursor=first_body["next_cursor"]),
        **auth_headers(token),
    )
    assert second.status_code == 200
    second_body = second.json()
    assert len(second_body["items"]) == 1
    assert second_body["has_more"] is False

    first_ids = _execution_ids(first_body)
    second_ids = _execution_ids(second_body)
    assert first_ids.isdisjoint(second_ids)
    assert first_ids | second_ids == {str(item.id) for item in executions}


def test_feed_cross_establishment_returns_empty_items(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _create_visible_execution(
        owner=owner_membership,
        staff=staff_membership,
        business_unit=business_unit,
    )
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)
    response = api_client.get(
        action_plan_execution_feed_url(foreign.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert _execution_ids(response.json()) == set()
    assert str(execution.id) not in _execution_ids(response.json())


@patch("houston.action_plans.execution_feed.ensure_visible_action_plan_executions_materialized")
def test_feed_get_invokes_read_path_materialization(
    mock_ensure,
    api_client,
    owner_membership,
):
    mock_ensure.return_value = 0
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    mock_ensure.assert_called_once()


def test_action_plan_execution_feed_query_count_baseline_empty(api_client, owner_membership):
    token = login(api_client, user=owner_membership.user)
    url = action_plan_execution_feed_url(owner_membership.establishment_id) + _feed_query(
        "general",
    )

    from houston.testing.query_baseline import (
        ACTION_PLAN_EXECUTION_FEED_EMPTY_MAX_QUERIES,
        assert_query_count_at_most,
        capture_queries,
    )

    with capture_queries() as context:
        response = api_client.get(url, **auth_headers(token))

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert_query_count_at_most(
        context,
        max_queries=ACTION_PLAN_EXECUTION_FEED_EMPTY_MAX_QUERIES,
        label="action_plan_execution_feed_general_empty",
    )


def test_action_plan_execution_feed_query_count_with_three_executions(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    for index in range(3):
        _create_visible_execution(
            owner=owner_membership,
            staff=staff_membership,
            business_unit=business_unit,
            title=f"Baseline {index}",
        )

    token = login(api_client, user=owner_membership.user)
    url = action_plan_execution_feed_url(owner_membership.establishment_id) + _feed_query(
        "general",
    )

    from houston.testing.query_baseline import (
        ACTION_PLAN_EXECUTION_FEED_THREE_ITEMS_MAX_QUERIES,
        assert_query_count_at_most,
        capture_queries,
    )

    with capture_queries() as context:
        response = api_client.get(url, **auth_headers(token))

    assert response.status_code == 200
    assert len(response.json()["items"]) == 3
    assert_query_count_at_most(
        context,
        max_queries=ACTION_PLAN_EXECUTION_FEED_THREE_ITEMS_MAX_QUERIES,
        label="action_plan_execution_feed_general_three_items",
    )
