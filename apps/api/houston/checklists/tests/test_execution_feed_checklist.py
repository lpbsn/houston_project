from __future__ import annotations

from datetime import date, datetime, time
from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.actions.execution_feed import build_execution_feed_page
from houston.actions.models import Action
from houston.actions.services import create_action
from houston.actions.tests.conftest import (
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    execution_feed_url,
    login,
)
from houston.checklists.constants import ASSIGNMENT_STATUS_ACTIVE
from houston.checklists.materialization import materialize_execution_from_assignment
from houston.checklists.models import ChecklistAssignment, ChecklistExecution, ChecklistTemplate
from houston.checklists.selectors import checklist_execution_feed_queryset
from houston.checklists.services import (
    cancel_checklist_execution,
    create_checklist_assignment,
    create_checklist_template,
    mark_task_done,
    update_checklist_assignment,
)
from houston.checklists.tests.conftest import (
    add_task_template,
    assignment_schedule_from_datetime,
    stable_assignment_times,
    stable_future_assignment_schedule,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def _feed_query(view_mode: str) -> str:
    return f"?view_mode={view_mode}"


def _scoped_staff_on_establishment(owner, business_unit):
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=staff,
        business_unit=business_unit,
    )
    return staff


def _active_registered_template(owner, business_unit):
    template = create_checklist_template(
        establishment_id=owner.establishment_id,
        actor=owner,
        title="Opening routine",
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    return template


def test_execution_feed_includes_checklist_item(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)
    now = timezone.now()
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=stable_assignment_times(duration_hours=2)[0],
        end_at=stable_assignment_times(duration_hours=2)[1],
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)

    token = login(api_client, user=staff.user)
    response = api_client.get(
        execution_feed_url(staff.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    checklist_items = [
        item for item in response.json()["items"] if item["item_type"] == "checklist"
    ]
    assert len(checklist_items) == 1
    payload = checklist_items[0]["checklist"]
    assert payload["id"] == str(execution.id)
    assert payload["title"] == execution.template_title
    assert "raw_text" not in payload


def test_manager_sees_in_scope_checklist_assigned_to_staff_in_general_view(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    maintenance = create_business_unit(
        establishment=owner.establishment,
        key="maintenance",
        label="Maintenance",
    )
    hotel = create_business_unit(
        establishment=owner.establishment,
        key="hotel",
        label="Hôtel",
    )
    staff = _scoped_staff_on_establishment(owner, maintenance)
    other_staff = _scoped_staff_on_establishment(owner, hotel)
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=maintenance,
    )

    scoped_template = _active_registered_template(owner, maintenance)
    out_of_scope_template = _active_registered_template(owner, hotel)
    now = timezone.now()
    schedule = stable_assignment_times(duration_hours=2)
    scoped_assignment = create_checklist_assignment(
        template=scoped_template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=schedule[0],
        end_at=schedule[1],
    )
    scoped_execution = ChecklistExecution.objects.get(checklist_assignment=scoped_assignment)
    out_of_scope_assignment = create_checklist_assignment(
        template=out_of_scope_template,
        actor=owner,
        assigned_to_id=other_staff.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=schedule[0],
        end_at=schedule[1],
    )
    out_of_scope_execution = ChecklistExecution.objects.get(
        checklist_assignment=out_of_scope_assignment,
    )

    token = login(api_client, user=manager.user)
    general = api_client.get(
        execution_feed_url(manager.establishment_id) + _feed_query("general"),
        **auth_headers(token),
    )
    assert general.status_code == 200
    general_ids = {
        item["checklist"]["id"]
        for item in general.json()["items"]
        if item["item_type"] == "checklist"
    }
    assert str(scoped_execution.id) in general_ids
    assert str(out_of_scope_execution.id) not in general_ids

    personal = api_client.get(
        execution_feed_url(manager.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    assert personal.status_code == 200
    personal_ids = {
        item["checklist"]["id"]
        for item in personal.json()["items"]
        if item["item_type"] == "checklist"
    }
    assert str(scoped_execution.id) not in personal_ids


def test_execution_feed_checklist_invisible_two_hours_before_start(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)
    schedule = stable_future_assignment_schedule(start_hour=14, duration_hours=1)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        **schedule,
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=schedule["start_date"],
    )

    token = login(api_client, user=staff.user)
    response = api_client.get(
        execution_feed_url(staff.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    checklist_ids = {
        item["checklist"]["id"]
        for item in response.json()["items"]
        if item["item_type"] == "checklist" and item["checklist"] is not None
    }
    assert checklist_ids == set()


def test_execution_feed_checklist_visible_one_hour_before_start(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)
    start_at = timezone.now() + timezone.timedelta(hours=1)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        **assignment_schedule_from_datetime(start_at, duration_hours=1),
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=start_at.date(),
    )

    token = login(api_client, user=staff.user)
    response = api_client.get(
        execution_feed_url(staff.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    checklist_ids = {
        item["checklist"]["id"]
        for item in response.json()["items"]
        if item["item_type"] == "checklist" and item["checklist"] is not None
    }
    assert str(execution.id) in checklist_ids


def test_execution_feed_checklist_overdue_stays_visible(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)
    start_at = timezone.now() - timezone.timedelta(hours=3)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        **assignment_schedule_from_datetime(start_at, duration_hours=1),
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    execution.status = ChecklistExecution.Status.IN_PROGRESS
    execution.save(update_fields=["status", "updated_at"])

    token = login(api_client, user=staff.user)
    response = api_client.get(
        execution_feed_url(staff.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    checklist_items = [
        item for item in response.json()["items"] if item["item_type"] == "checklist"
    ]
    assert len(checklist_items) == 1
    assert checklist_items[0]["checklist"]["is_overdue"] is True


def test_execution_feed_checklist_disappears_when_done(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)
    now = timezone.now()
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=stable_assignment_times(duration_hours=2)[0],
        end_at=stable_assignment_times(duration_hours=2)[1],
    )
    execution = ChecklistExecution.objects.prefetch_related("task_executions").get(
        checklist_assignment=assignment,
    )
    task = execution.task_executions.first()
    mark_task_done(task_execution=task, actor=staff)

    token = login(api_client, user=staff.user)
    response = api_client.get(
        execution_feed_url(staff.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    checklist_ids = {
        item["checklist"]["id"]
        for item in response.json()["items"]
        if item["item_type"] == "checklist" and item["checklist"] is not None
    }
    assert str(execution.id) not in checklist_ids


def test_execution_feed_checklist_disappears_when_canceled(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)
    now = timezone.now()
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=stable_assignment_times(duration_hours=2)[0],
        end_at=stable_assignment_times(duration_hours=2)[1],
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    cancel_checklist_execution(execution=execution, actor=owner)

    token = login(api_client, user=staff.user)
    response = api_client.get(
        execution_feed_url(staff.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    checklist_ids = {
        item["checklist"]["id"]
        for item in response.json()["items"]
        if item["item_type"] == "checklist" and item["checklist"] is not None
    }
    assert str(execution.id) not in checklist_ids


def test_execution_feed_checklist_disappears_when_assignment_update_auto_cancels(api_client):
    from datetime import datetime, timedelta

    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)
    now = timezone.now()
    days_ahead = (0 - now.weekday()) % 7
    monday_start = datetime.combine(
        (now + timedelta(days=days_ahead)).date(),
        datetime.min.time().replace(hour=8),
        tzinfo=now.tzinfo,
    )
    tuesday_date = monday_start.date() + timedelta(days=1)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        recurrence_days=["monday", "tuesday"],
        **assignment_schedule_from_datetime(monday_start, duration_hours=2),
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=monday_start.date(),
    )
    tuesday_execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=tuesday_date,
    )

    update_checklist_assignment(
        assignment=assignment,
        actor=owner,
        recurrence_days=["monday"],
    )

    token = login(api_client, user=staff.user)
    response = api_client.get(
        execution_feed_url(staff.establishment_id) + _feed_query("personal"),
        **auth_headers(token),
    )
    checklist_ids = {
        item["checklist"]["id"]
        for item in response.json()["items"]
        if item["item_type"] == "checklist" and item["checklist"] is not None
    }
    assert str(tuesday_execution.id) not in checklist_ids


# Tuesday 2026-06-09 at 13:35 in Django active timezone (UTC in settings).
SCENARIO_NOW = timezone.make_aware(datetime(2026, 6, 9, 13, 35, 0))
OCCURRENCE_DATE = date(2026, 6, 9)
# TS-E1 query-count guard: same Tuesday, noon — independent of wall clock / weekend.
TS_E1_FIXED_NOW = timezone.make_aware(datetime(2026, 6, 9, 12, 0, 0))


def test_execution_feed_three_assignments_tuesday_scenario(api_client):
    """
      Reproduces the real-world case: Pierre (staff), personal feed, 2026-06-09 after 13:30.
      A1 and A2 (Tuesday) must appear; A3 (starts 2026-06-13, Wed/Thu) must not.
    Uses GET execution-feed (same endpoint as UI).
    """
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)

    assignment_one = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=date(2026, 6, 9),
        end_date=date(2026, 6, 10),
        start_at=time(13, 33),
        end_at=time(14, 34),
        recurrence_days=["tuesday"],
    )
    assignment_two = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=date(2026, 6, 9),
        end_date=date(2026, 6, 19),
        start_at=time(14, 30),
        end_at=time(16, 32),
        recurrence_days=["tuesday"],
    )
    assignment_three = create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=date(2026, 6, 13),
        end_date=date(2026, 6, 17),
        start_at=time(11, 30),
        end_at=time(13, 30),
        recurrence_days=["wednesday", "thursday"],
    )

    with patch.object(timezone, "now", return_value=SCENARIO_NOW):
        active_count = ChecklistAssignment.objects.filter(
            establishment_id=staff.establishment_id,
            status=ASSIGNMENT_STATUS_ACTIVE,
            checklist_template=template,
        ).count()
        assert active_count == 3

        june_ninth_executions = list(
            ChecklistExecution.objects.filter(
                establishment_id=staff.establishment_id,
                occurrence_date=OCCURRENCE_DATE,
            ).values(
                "id",
                "occurrence_date",
                "start_at",
                "end_at",
                "visible_from",
                "status",
                "assigned_to_id",
                "checklist_assignment_id",
            ),
        )
        assert len(june_ninth_executions) == 2
        june_ninth_assignment_ids = {
            row["checklist_assignment_id"] for row in june_ninth_executions
        }
        assert assignment_one.id in june_ninth_assignment_ids
        assert assignment_two.id in june_ninth_assignment_ids
        assert assignment_three.id not in june_ninth_assignment_ids

        for row in june_ninth_executions:
            assert row["status"] == ChecklistExecution.Status.ASSIGNED
            assert row["assigned_to_id"] == staff.id
            assert row["visible_from"] <= SCENARIO_NOW

        feed_qs_ids = set(
            checklist_execution_feed_queryset(
                membership=staff,
                view_mode="personal",
            ).values_list("id", flat=True),
        )
        assert len(feed_qs_ids) == 2

        merged_items, _has_more, _next_cursor = build_execution_feed_page(
            membership=staff,
            view_mode="personal",
            page_size=25,
        )
        merged_checklist_ids = {
            item.checklist.id
            for item in merged_items
            if item.item_type == "checklist" and item.checklist is not None
        }
        assert merged_checklist_ids == feed_qs_ids
        assert len(merged_checklist_ids) == 2

        token = login(api_client, user=staff.user)
        response = api_client.get(
            execution_feed_url(staff.establishment_id) + _feed_query("personal"),
            **auth_headers(token),
        )

    assert response.status_code == 200
    body = response.json()
    checklist_entries = [item for item in body["items"] if item["item_type"] == "checklist"]
    assert len(checklist_entries) == 2
    checklist_ids = {entry["checklist"]["id"] for entry in checklist_entries}
    execution_ids = {
        str(execution_id)
        for execution_id in ChecklistExecution.objects.filter(
            checklist_assignment_id__in=[assignment_one.id, assignment_two.id],
            occurrence_date=OCCURRENCE_DATE,
        ).values_list("id", flat=True)
    }
    assert checklist_ids == execution_ids

    assignment_three_execution = ChecklistExecution.objects.get(
        checklist_assignment=assignment_three,
    )
    assert str(assignment_three_execution.id) not in checklist_ids
    # Period starts 2026-06-13 (Sat); first Wed in range is 2026-06-17.
    assert assignment_three_execution.occurrence_date == date(2026, 6, 17)

    for entry in checklist_entries:
        assert entry["checklist"]["status"] in {
            ChecklistExecution.Status.ASSIGNED,
            ChecklistExecution.Status.IN_PROGRESS,
        }


def test_execution_feed_keeps_checklists_when_actions_fill_page(api_client):
    """Checklists must not be evicted from the feed when actions outrank by last_activity_at."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)

    stale = SCENARIO_NOW - timezone.timedelta(hours=5)
    with patch.object(timezone, "now", return_value=stale):
        create_checklist_assignment(
            template=template,
            actor=owner,
            assigned_to_id=staff.id,
            start_date=date(2026, 6, 9),
            end_date=date(2026, 6, 19),
            start_at=time(13, 33),
            end_at=time(14, 34),
            recurrence_days=["tuesday"],
        )
        create_checklist_assignment(
            template=template,
            actor=owner,
            assigned_to_id=staff.id,
            start_date=date(2026, 6, 9),
            end_date=date(2026, 6, 19),
            start_at=time(14, 30),
            end_at=time(16, 32),
            recurrence_days=["tuesday"],
        )
    ChecklistExecution.objects.filter(establishment_id=staff.establishment_id).update(
        last_activity_at=stale,
    )

    for index in range(30):
        action = create_action(
            establishment_id=owner.establishment_id,
            created_by=owner,
            title=f"Action {index}",
            instruction="Instruction text",
            assignee_ids=[staff.id],
            due_at=SCENARIO_NOW,
            responsible_business_unit_id=business_unit.id,
        )
        Action.objects.filter(id=action.id).update(last_activity_at=SCENARIO_NOW)

    with patch.object(timezone, "now", return_value=SCENARIO_NOW):
        feed_qs_count = checklist_execution_feed_queryset(
            membership=staff,
            view_mode="personal",
        ).count()
        assert feed_qs_count == 2

        token = login(api_client, user=staff.user)
        response = api_client.get(
            execution_feed_url(staff.establishment_id) + _feed_query("personal"),
            **auth_headers(token),
        )

    assert response.status_code == 200
    body = response.json()
    checklist_entries = [item for item in body["items"] if item["item_type"] == "checklist"]
    action_entries = [item for item in body["items"] if item["item_type"] == "action"]
    assert len(checklist_entries) == 2
    assert len(action_entries) == 23
    assert len(body["items"]) == 25
    assert body["has_more"] is True


def test_execution_feed_has_more_when_checklists_fill_page_and_actions_exist(api_client):
    """Page filled by checklists still reports has_more when actions remain (API-03)."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)

    page_size = 2
    for index in range(page_size):
        now = timezone.now()
        create_checklist_assignment(
            template=template,
            actor=owner,
            assigned_to_id=staff.id,
            start_date=now.date(),
            end_date=now.date(),
            start_at=stable_assignment_times(duration_hours=2)[0],
            end_at=stable_assignment_times(duration_hours=2)[1],
        )

    create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Overflow action",
        instruction="Instruction text",
        assignee_ids=[staff.id],
        due_at=timezone.now(),
        responsible_business_unit_id=business_unit.id,
    )

    token = login(api_client, user=staff.user)
    response = api_client.get(
        execution_feed_url(staff.establishment_id)
        + _feed_query("personal")
        + f"&page_size={page_size}",
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    checklist_entries = [item for item in body["items"] if item["item_type"] == "checklist"]
    assert len(checklist_entries) == page_size
    assert body["has_more"] is True


def test_execution_feed_checklist_query_count_baseline(api_client):
    """Phase G: personal feed with checklist; no dual count() (DB-01)."""
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)
    now = timezone.now()
    create_checklist_assignment(
        template=template,
        actor=owner,
        assigned_to_id=staff.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=stable_assignment_times(duration_hours=2)[0],
        end_at=stable_assignment_times(duration_hours=2)[1],
    )

    from houston.testing.query_baseline import (
        EXECUTION_FEED_ONE_CHECKLIST_MAX_QUERIES,
        assert_query_count_at_most,
        capture_queries,
    )

    token = login(api_client, user=staff.user)
    url = execution_feed_url(staff.establishment_id) + _feed_query("personal")
    with capture_queries() as context:
        response = api_client.get(url, **auth_headers(token))

    assert response.status_code == 200
    checklist_items = [
        item for item in response.json()["items"] if item["item_type"] == "checklist"
    ]
    assert len(checklist_items) == 1
    assert_query_count_at_most(
        context,
        max_queries=EXECUTION_FEED_ONE_CHECKLIST_MAX_QUERIES,
        label="execution_feed_personal_one_checklist",
    )


def test_execution_feed_query_count_with_twenty_visible_assignments(api_client):
    """TS-E1 / ROADMAP-15: steady-state GET with 20 visible checklist assignments."""
    from houston.checklists.materialization import (
        READ_PATH_MATERIALIZATION_HORIZON_DAYS,
        materialize_assignment_occurrences_in_horizon,
    )
    from houston.testing.query_baseline import (
        EXECUTION_FEED_TWENTY_CHECKLIST_ASSIGNMENTS_MAX_QUERIES,
        assert_query_count_at_most,
        capture_queries,
    )

    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    business_unit = create_business_unit(establishment=owner.establishment, key="restaurant")
    staff = _scoped_staff_on_establishment(owner, business_unit)
    template = _active_registered_template(owner, business_unit)

    with patch.object(timezone, "now", return_value=TS_E1_FIXED_NOW):
        schedule = assignment_schedule_from_datetime(TS_E1_FIXED_NOW, duration_hours=2)
        assignments = []
        for _index in range(20):
            assignment = create_checklist_assignment(
                template=template,
                actor=owner,
                assigned_to_id=staff.id,
                recurrence_days=["tuesday"],
                **schedule,
            )
            assignments.append(assignment)

        for assignment in assignments:
            ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
            materialize_assignment_occurrences_in_horizon(
                assignment=assignment,
                horizon_days=READ_PATH_MATERIALIZATION_HORIZON_DAYS,
                now=TS_E1_FIXED_NOW,
            )
            assignment.last_materialized_at = TS_E1_FIXED_NOW
            assignment.save(update_fields=["last_materialized_at", "updated_at"])

        assert len(assignments) == 20
        visible_count = checklist_execution_feed_queryset(
            membership=owner,
            view_mode="general",
        ).count()
        assert visible_count == 20

        token = login(api_client, user=owner.user)
        url = execution_feed_url(owner.establishment_id) + _feed_query("general")
        with capture_queries() as context:
            response = api_client.get(url, **auth_headers(token))

    assert response.status_code == 200
    checklist_items = [
        item for item in response.json()["items"] if item["item_type"] == "checklist"
    ]
    assert len(checklist_items) == 20
    assert_query_count_at_most(
        context,
        max_queries=EXECUTION_FEED_TWENTY_CHECKLIST_ASSIGNMENTS_MAX_QUERIES,
        label="execution_feed_general_twenty_checklist_assignments",
    )
