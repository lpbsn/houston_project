from __future__ import annotations

from datetime import time, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_SCHEDULED,
    SCHEDULE_ALL_DAY_END,
    SCHEDULE_ALL_DAY_START,
)
from houston.action_plans.models import ActionPlanExecution, ActionPlanSchedule
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import (
    action_plan_execution_calendar_url,
    action_plan_execution_feed_url,
    action_plan_execution_upcoming_url,
    action_plan_planning_submit_url,
    build_assignee_payload,
    build_schedule_assignee_payload,
    build_task_payload,
    create_catalog_action_plan,
    create_execution,
    feed_query,
    recurrence_days_for_visible_today,
)
from houston.testing.auth import auth_headers, login

pytestmark = pytest.mark.django_db


def _calendar_query(*, view_mode: str, from_date, to_date) -> str:
    return (
        f"?view_mode={view_mode}"
        f"&from={from_date.isoformat()}"
        f"&to={to_date.isoformat()}"
    )


def test_create_execution_all_day_flag(
    owner_membership,
    business_unit,
):
    start_at = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_at = start_at.replace(hour=23, minute=59)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="All day create",
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        end_at=end_at,
        all_day=True,
    )
    execution.refresh_from_db()
    assert execution.all_day is True
    assert execution.start_at == start_at
    assert execution.end_at == end_at


def test_timed_midnight_span_is_not_all_day(
    owner_membership,
    business_unit,
):
    start_at = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_at = start_at.replace(hour=23, minute=59)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Timed full day",
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        end_at=end_at,
        all_day=False,
    )
    execution.refresh_from_db()
    assert execution.all_day is False


def test_planning_submit_all_day_schedule_copies_flag(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    catalog = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    today = timezone.now().date()
    payload = {
        "submission_id": str(uuid4()),
        "use_shared_chronology": True,
        "items": [
            {
                "item_id": str(uuid4()),
                "kind": "schedule",
                "assignees": [
                    {
                        "membership_id": str(staff_membership.id),
                        "business_unit_id": str(business_unit.id),
                    }
                ],
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=14)).isoformat(),
                "start_at": "09:00:00",
                "end_at": "10:00:00",
                "recurrence_days": recurrence_days_for_visible_today(),
                "all_day": True,
            }
        ],
    }
    token = login(api_client, user=owner_membership.user)
    response = api_client.post(
        action_plan_planning_submit_url(owner_membership.establishment_id, catalog.id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201, response.content
    schedule = ActionPlanSchedule.objects.get(id=response.json()["schedules"][0]["id"])
    assert schedule.all_day is True
    assert schedule.start_at == SCHEDULE_ALL_DAY_START
    assert schedule.end_at == SCHEDULE_ALL_DAY_END
    execution = schedule.executions.first()
    assert execution is not None
    assert execution.all_day is True


def test_calendar_rejects_window_over_45_days(api_client, owner_membership):
    token = login(api_client, user=owner_membership.user)
    today = timezone.now().date()
    response = api_client.get(
        action_plan_execution_calendar_url(owner_membership.establishment_id)
        + _calendar_query(
            view_mode="general",
            from_date=today,
            to_date=today + timedelta(days=46),
        ),
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_calendar_includes_intersection_and_unplanned(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    inside_start = now + timedelta(days=2)
    _, inside = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Inside window",
        tasks=[build_task_payload(task="in", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=inside_start,
        end_at=inside_start + timedelta(hours=1),
    )
    outside_start = now + timedelta(days=20)
    _, outside = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Outside window",
        tasks=[build_task_payload(task="out", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=outside_start,
        end_at=outside_start + timedelta(hours=1),
    )
    unplanned = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Unplanned",
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        status=EXECUTION_STATUS_IN_PROGRESS,
    )
    token = login(api_client, user=owner_membership.user)
    window_from = (now + timedelta(days=1)).date()
    window_to = (now + timedelta(days=3)).date()
    response = api_client.get(
        action_plan_execution_calendar_url(owner_membership.establishment_id)
        + _calendar_query(view_mode="general", from_date=window_from, to_date=window_to),
        **auth_headers(token),
    )
    assert response.status_code == 200, response.content
    body = response.json()
    item_ids = {item["action_plan_execution"]["id"] for item in body["items"]}
    unplanned_ids = {item["action_plan_execution"]["id"] for item in body["unplanned"]}
    assert str(inside.id) in item_ids
    assert str(outside.id) not in item_ids
    assert str(unplanned.id) in unplanned_ids
    assert str(unplanned.id) not in item_ids
    assert "timezone" in body
    assert "all_day" in body["items"][0]["action_plan_execution"]


def test_calendar_does_not_infer_all_day_from_sentinel_times(
    api_client,
    owner_membership,
    business_unit,
):
    start_at = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        days=1
    )
    end_at = start_at.replace(hour=23, minute=59)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Sentinel timed",
        tasks=[build_task_payload(task="t", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=start_at,
        end_at=end_at,
        all_day=False,
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_calendar_url(owner_membership.establishment_id)
        + _calendar_query(
            view_mode="general",
            from_date=start_at.date(),
            to_date=start_at.date(),
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200
    payload = next(
        item["action_plan_execution"]
        for item in response.json()["items"]
        if item["action_plan_execution"]["id"] == str(execution.id)
    )
    assert payload["all_day"] is False


def test_calendar_rbac_matches_feed_and_upcoming(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    now = timezone.now()
    _, personal = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Staff personal",
        tasks=[build_task_payload(task="p", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit),
        ],
        start_at=now + timedelta(hours=4),
        end_at=now + timedelta(hours=5),
        visible_from=now - timedelta(minutes=1),
    )
    _, other = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Owner only",
        tasks=[build_task_payload(task="o", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
        ],
        start_at=now + timedelta(hours=4),
        end_at=now + timedelta(hours=5),
        visible_from=now - timedelta(minutes=1),
    )
    token = login(api_client, user=staff_membership.user)
    from_date = now.date()
    to_date = (now + timedelta(days=2)).date()
    calendar = api_client.get(
        action_plan_execution_calendar_url(staff_membership.establishment_id)
        + _calendar_query(view_mode="personal", from_date=from_date, to_date=to_date),
        **auth_headers(token),
    )
    upcoming = api_client.get(
        action_plan_execution_upcoming_url(staff_membership.establishment_id)
        + feed_query("personal"),
        **auth_headers(token),
    )
    feed = api_client.get(
        action_plan_execution_feed_url(staff_membership.establishment_id)
        + feed_query("personal"),
        **auth_headers(token),
    )
    assert calendar.status_code == 200
    assert upcoming.status_code == 200
    assert feed.status_code == 200
    calendar_ids = {item["action_plan_execution"]["id"] for item in calendar.json()["items"]}
    upcoming_ids = {item["action_plan_execution"]["id"] for item in upcoming.json()["items"]}
    feed_ids = {item["action_plan_execution"]["id"] for item in feed.json()["items"]}
    assert str(personal.id) in calendar_ids
    assert str(other.id) not in calendar_ids
    assert str(other.id) not in upcoming_ids
    assert str(other.id) not in feed_ids
    if personal.status == EXECUTION_STATUS_SCHEDULED:
        assert str(personal.id) in upcoming_ids


def test_calendar_future_window_does_not_materialize_gap(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    catalog = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    today = timezone.now().date()
    window_from = today + timedelta(days=20)
    window_to = today + timedelta(days=22)
    schedule = create_action_plan_schedule(
        action_plan=catalog,
        actor=owner_membership,
        start_date=today,
        end_date=today + timedelta(days=40),
        start_at=time(9, 0),
        end_at=time(10, 0),
        recurrence_days=[
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
    )
    before_ids = set(
        ActionPlanExecution.objects.filter(action_plan_schedule=schedule).values_list(
            "id",
            flat=True,
        )
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_calendar_url(owner_membership.establishment_id)
        + _calendar_query(view_mode="general", from_date=window_from, to_date=window_to),
        **auth_headers(token),
    )
    assert response.status_code == 200, response.content
    created = ActionPlanExecution.objects.filter(action_plan_schedule=schedule).exclude(
        id__in=before_ids
    )
    created_dates = set(created.values_list("occurrence_date", flat=True))
    assert created_dates
    assert all(window_from <= occurrence <= window_to for occurrence in created_dates)
    gap_dates = {
        occurrence
        for occurrence in created_dates
        if today < occurrence < window_from
    }
    assert gap_dates == set()


@patch("django.db.transaction.on_commit")
def test_calendar_materialization_does_not_emit_side_effects(
    mock_on_commit,
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    catalog = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    today = timezone.now().date()
    create_action_plan_schedule(
        action_plan=catalog,
        actor=owner_membership,
        start_date=today,
        end_date=today + timedelta(days=40),
        start_at=time(9, 0),
        end_at=time(10, 0),
        recurrence_days=[
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        emit_side_effects=False,
    )
    mock_on_commit.reset_mock()
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_calendar_url(owner_membership.establishment_id)
        + _calendar_query(
            view_mode="general",
            from_date=today + timedelta(days=20),
            to_date=today + timedelta(days=21),
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200, response.content
    mock_on_commit.assert_not_called()
