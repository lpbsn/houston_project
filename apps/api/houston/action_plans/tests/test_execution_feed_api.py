from __future__ import annotations

import logging

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    SCHEDULE_STATUS_ACTIVE,
    SCHEDULE_STATUS_INACTIVE,
    TASK_STATUS_DONE,
)
from houston.action_plans.models import (
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanSchedule,
)
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.selectors import action_plan_execution_overdue
from houston.action_plans.services import deactivate_action_plan
from houston.action_plans.tests.helpers import (
    action_plan_execution_feed_url,
    action_plan_task_url,
    build_assignee_payload,
    build_schedule_assignee_payload,
    build_task_payload,
    create_execution,
    feed_execution_ids,
    feed_query,
    recurrence_days_for_visible_today,
    visible_schedule_window,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import auth_headers, login
from houston.testing.auth import build_api_membership as build_foreign_membership

pytestmark = pytest.mark.django_db


def test_action_plan_execution_feed_response_contract(api_client, owner_membership):
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
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


def test_action_plan_execution_feed_item_contract(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Feed contract",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["item_type"] == "action_plan_execution"
    payload = item["action_plan_execution"]
    assert payload["id"] == str(execution.id)
    assert payload["title"] == "Feed contract"
    assert isinstance(payload["involved_poles"], list)
    assert len(payload["involved_poles"]) >= 1
    assert "permission_hints" in payload
    assert payload["permission_hints"]["can_mark_done"] is True
    assert payload["permission_hints"]["can_pin"] is True
    assert payload["is_pinned"] is False
    assert payload["task_count"] == 1
    assert payload["treated_task_count"] == 0


def test_action_plan_execution_feed_item_task_counts(
    api_client,
    owner_membership,
    business_unit,
):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Multi-task feed",
        tasks=[
            build_task_payload(task="Task 1", business_unit=business_unit, position=1),
            build_task_payload(task="Task 2", business_unit=business_unit, position=2),
            build_task_payload(task="Task 3", business_unit=business_unit, position=3),
            build_task_payload(task="Task 4", business_unit=business_unit, position=4),
        ],
    )
    first_task = ActionPlanExecutionTask.objects.filter(
        action_plan_execution=execution,
        position=1,
    ).first()
    first_task.status = TASK_STATUS_DONE
    first_task.save(update_fields=["status", "updated_at"])

    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()["items"][0]["action_plan_execution"]
    assert payload["task_count"] == 4
    assert payload["treated_task_count"] == 1
    assert len(payload["task_executions"]) == 3


def test_action_plan_execution_feed_item_task_counts_decrement_after_mark_pending(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Unmark feed",
        tasks=[
            build_task_payload(task="Task 1", business_unit=business_unit, position=1),
            build_task_payload(task="Task 2", business_unit=business_unit, position=2),
        ],
        assignees=[
            build_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            ),
        ],
    )
    task = ActionPlanExecutionTask.objects.filter(
        action_plan_execution=execution,
        position=1,
    ).first()
    token = login(api_client, user=staff_membership.user)
    mark_done = api_client.post(
        action_plan_task_url(staff_membership.establishment_id, task.id, "mark-done/"),
        **auth_headers(token),
    )
    assert mark_done.status_code == 200

    feed_after_done = api_client.get(
        action_plan_execution_feed_url(staff_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert feed_after_done.json()["items"][0]["action_plan_execution"]["treated_task_count"] == 1

    mark_pending = api_client.post(
        action_plan_task_url(staff_membership.establishment_id, task.id, "mark-pending/"),
        **auth_headers(token),
    )
    assert mark_pending.status_code == 200

    feed_after_pending = api_client.get(
        action_plan_execution_feed_url(staff_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert feed_after_pending.json()["items"][0]["action_plan_execution"]["treated_task_count"] == 0


def test_terminal_executions_included_in_feed_ordered_after_actives(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    done = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Done execution",
        status=EXECUTION_STATUS_DONE,
        last_activity_at=now - timezone.timedelta(hours=1),
        end_at=now - timezone.timedelta(days=2),
    )
    canceled = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Canceled execution",
        status=EXECUTION_STATUS_CANCELED,
        last_activity_at=now - timezone.timedelta(hours=2),
        end_at=now - timezone.timedelta(days=1),
    )
    pending = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pending validation",
        status=EXECUTION_STATUS_PENDING_VALIDATION,
        requires_validation=True,
        last_activity_at=now,
    )
    in_progress = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Active execution",
        last_activity_at=now - timezone.timedelta(minutes=30),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert feed_execution_ids(response.json()) == [
        str(pending.id),
        str(in_progress.id),
        str(done.id),
        str(canceled.id),
    ]


def test_terminal_executions_sort_by_last_activity_desc_within_status(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    older_done = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Older done",
        status=EXECUTION_STATUS_DONE,
        last_activity_at=now - timezone.timedelta(days=2),
    )
    newer_done = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Newer done",
        status=EXECUTION_STATUS_DONE,
        last_activity_at=now - timezone.timedelta(hours=1),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert feed_execution_ids(response.json()) == [
        str(newer_done.id),
        str(older_done.id),
    ]


@pytest.mark.parametrize(
    "terminal_status",
    [EXECUTION_STATUS_DONE, EXECUTION_STATUS_CANCELED],
    ids=["done", "canceled"],
)
def test_terminal_sort_by_last_activity_overrides_end_at(
    api_client,
    owner_membership,
    business_unit,
    terminal_status,
):
    now = timezone.now()
    newer = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Newer activity terminal",
        status=terminal_status,
        last_activity_at=now - timezone.timedelta(hours=1),
        end_at=now + timezone.timedelta(days=2),
    )
    older = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Older activity terminal",
        status=terminal_status,
        last_activity_at=now - timezone.timedelta(days=2),
        end_at=now - timezone.timedelta(days=1),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert feed_execution_ids(response.json()) == [
        str(newer.id),
        str(older.id),
    ]


@pytest.mark.parametrize(
    "terminal_status",
    [EXECUTION_STATUS_DONE, EXECUTION_STATUS_CANCELED],
    ids=["done", "canceled"],
)
def test_terminal_pagination_respects_last_activity_order(
    api_client,
    owner_membership,
    business_unit,
    terminal_status,
):
    now = timezone.now()
    newer = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Newer terminal page",
        status=terminal_status,
        last_activity_at=now - timezone.timedelta(hours=1),
        end_at=now + timezone.timedelta(days=2),
    )
    older = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Older terminal page",
        status=terminal_status,
        last_activity_at=now - timezone.timedelta(days=2),
        end_at=now - timezone.timedelta(days=1),
    )
    token = login(api_client, user=owner_membership.user)
    first = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general")
        + "&page_size=1",
        **auth_headers(token),
    )
    second = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general")
        + f"&page_size=1&cursor={first.json()['next_cursor']}",
        **auth_headers(token),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert feed_execution_ids(first.json()) == [str(newer.id)]
    assert feed_execution_ids(second.json()) == [str(older.id)]


def test_terminal_executions_are_not_marked_overdue_in_feed(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    done = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Done overdue",
        status=EXECUTION_STATUS_DONE,
        end_at=now - timezone.timedelta(days=1),
    )
    canceled = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Canceled overdue",
        status=EXECUTION_STATUS_CANCELED,
        end_at=now - timezone.timedelta(days=1),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    items_by_id = {
        item["action_plan_execution"]["id"]: item["action_plan_execution"]
        for item in response.json()["items"]
    }
    assert items_by_id[str(done.id)]["is_overdue"] is False
    assert items_by_id[str(canceled.id)]["is_overdue"] is False


def test_feed_pagination_includes_terminal_executions_after_actives(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    actives = [
        create_execution(
            owner_membership,
            business_unit=business_unit,
            title=f"Active {index}",
            end_at=now + timezone.timedelta(hours=index + 1),
        )
        for index in range(2)
    ]
    done = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Done execution",
        status=EXECUTION_STATUS_DONE,
        last_activity_at=now - timezone.timedelta(hours=1),
    )
    token = login(api_client, user=owner_membership.user)
    first = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general")
        + "&page_size=2",
        **auth_headers(token),
    )
    second = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general")
        + f"&page_size=2&cursor={first.json()['next_cursor']}",
        **auth_headers(token),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    merged_ids = feed_execution_ids(first.json()) + feed_execution_ids(second.json())
    assert merged_ids == [str(execution.id) for execution in actives] + [str(done.id)]


def test_future_execution_visible_from_excluded(
    api_client,
    owner_membership,
    business_unit,
):
    create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Future execution",
        visible_from=timezone.now() + timezone.timedelta(hours=2),
    )
    visible = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Visible execution",
        visible_from=timezone.now() - timezone.timedelta(minutes=5),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert ids == {str(visible.id)}


def test_personal_feed_hides_assignee_with_future_visible_from(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Individual chronology",
        tasks=[
            build_task_payload(
                task="Individual chronology task",
                business_unit=business_unit,
                assigned_membership=staff_membership,
            )
        ],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        visible_from=timezone.now() - timezone.timedelta(minutes=5),
    )
    assignee = ActionPlanAssignee.objects.get(
        action_plan_execution=execution,
        membership=staff_membership,
    )
    assignee.visible_from = timezone.now() + timezone.timedelta(hours=2)
    assignee.save(update_fields=["visible_from", "updated_at"])

    staff_token = login(api_client, user=staff_membership.user)
    personal = api_client.get(
        action_plan_execution_feed_url(staff_membership.establishment_id) + feed_query("personal"),
        **auth_headers(staff_token),
    )
    assert personal.status_code == 200
    assert personal.json()["items"] == []

    owner_token = login(api_client, user=owner_membership.user)
    general = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(owner_token),
    )
    assert general.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in general.json()["items"]}
    assert str(execution.id) in ids


def test_staff_sees_only_assigned_executions(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    other_staff = type(staff_membership).objects.create(
        establishment=owner_membership.establishment,
        user=staff_membership.user.__class__.objects.create_user(
            username="other-staff-feed",
            email="other-staff-feed@example.com",
            password="test-pass-123",
        ),
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    from houston.testing.taxonomy import create_membership_with_business_unit_scope

    create_membership_with_business_unit_scope(
        membership=other_staff,
        business_unit=business_unit,
    )

    assigned = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Assigned to staff",
        tasks=[
            build_task_payload(
                task="Assigned to staff task",
                business_unit=business_unit,
                assigned_membership=staff_membership,
            )
        ],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Assigned to other",
        tasks=[
            build_task_payload(
                task="Assigned to other task",
                business_unit=business_unit,
                assigned_membership=other_staff,
            )
        ],
        assignees=[build_assignee_payload(membership=other_staff, business_unit=business_unit)],
    )
    token = login(api_client, user=staff_membership.user)
    for view_mode in ("personal", "general"):
        response = api_client.get(
            action_plan_execution_feed_url(staff_membership.establishment_id)
            + feed_query(view_mode),
            **auth_headers(token),
        )
        assert response.status_code == 200
        ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
        assert ids == {str(assigned.id)}


def test_manager_sees_scoped_execution_in_general_view(
    api_client,
    owner_membership,
    contributor_manager_membership,
    business_unit,
    maintenance_business_unit,
):
    maintenance_staff = type(contributor_manager_membership).objects.create(
        establishment=owner_membership.establishment,
        user=contributor_manager_membership.user.__class__.objects.create_user(
            username="maintenance-staff-feed",
            email="maintenance-staff-feed@example.com",
            password="test-pass-123",
        ),
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    from houston.testing.taxonomy import create_membership_with_business_unit_scope

    create_membership_with_business_unit_scope(
        membership=maintenance_staff,
        business_unit=maintenance_business_unit,
    )

    scoped = create_execution(
        owner_membership,
        business_unit=maintenance_business_unit,
        title="Maintenance scoped",
        assignees=[
            build_assignee_payload(
                membership=maintenance_staff,
                business_unit=maintenance_business_unit,
            )
        ],
    )
    restaurant_staff = type(maintenance_staff).objects.create(
        establishment=owner_membership.establishment,
        user=maintenance_staff.user.__class__.objects.create_user(
            username="restaurant-staff-feed",
            email="restaurant-staff-feed@example.com",
            password="test-pass-123",
        ),
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=restaurant_staff,
        business_unit=business_unit,
    )
    create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Out of manager scope",
        assignees=[
            build_assignee_payload(membership=restaurant_staff, business_unit=business_unit)
        ],
    )
    token = login(api_client, user=contributor_manager_membership.user)
    general = api_client.get(
        action_plan_execution_feed_url(contributor_manager_membership.establishment_id)
        + feed_query("general"),
        **auth_headers(token),
    )
    assert general.status_code == 200
    general_ids = {item["action_plan_execution"]["id"] for item in general.json()["items"]}
    assert str(scoped.id) in general_ids

    personal = api_client.get(
        action_plan_execution_feed_url(contributor_manager_membership.establishment_id)
        + feed_query("personal"),
        **auth_headers(token),
    )
    assert personal.status_code == 200
    personal_ids = {item["action_plan_execution"]["id"] for item in personal.json()["items"]}
    assert str(scoped.id) in personal_ids


def test_pending_validation_execution_in_feed(
    api_client,
    owner_membership,
    business_unit,
):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pending validation",
        status=EXECUTION_STATUS_PENDING_VALIDATION,
        requires_validation=True,
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()["items"][0]["action_plan_execution"]
    assert payload["id"] == str(execution.id)
    assert payload["status"] == EXECUTION_STATUS_PENDING_VALIDATION
    assert payload["requires_validation"] is True


def test_feed_pagination_cursor_is_stable(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    executions = []
    for index in range(4):
        executions.append(
            create_execution(
                owner_membership,
                business_unit=business_unit,
                title=f"Feed page {index}",
                end_at=now + timezone.timedelta(hours=index + 1),
            )
        )
    token = login(api_client, user=owner_membership.user)
    first = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general")
        + "&page_size=2",
        **auth_headers(token),
    )
    assert first.status_code == 200
    first_body = first.json()
    assert len(first_body["items"]) == 2
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]
    assert feed_execution_ids(first_body) == [
        str(executions[0].id),
        str(executions[1].id),
    ]

    second = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general")
        + f"&page_size=2&cursor={first_body['next_cursor']}",
        **auth_headers(token),
    )
    assert second.status_code == 200
    second_body = second.json()
    assert len(second_body["items"]) == 2
    assert feed_execution_ids(second_body) == [
        str(executions[2].id),
        str(executions[3].id),
    ]
    first_ids = {item["action_plan_execution"]["id"] for item in first_body["items"]}
    second_ids = {item["action_plan_execution"]["id"] for item in second_body["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_feed_sorts_overdue_before_upcoming_before_null_within_status(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    no_deadline = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Sans échéance",
    )
    upcoming = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="À venir",
        end_at=now + timezone.timedelta(days=2),
    )
    overdue = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="En retard",
        end_at=now - timezone.timedelta(hours=2),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert feed_execution_ids(response.json()) == [
        str(overdue.id),
        str(upcoming.id),
        str(no_deadline.id),
    ]


def test_feed_sorts_by_nearest_end_at_within_same_bucket(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    later_overdue = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Retard récent",
        end_at=now - timezone.timedelta(hours=1),
    )
    earlier_overdue = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Retard ancien",
        end_at=now - timezone.timedelta(hours=5),
    )
    sooner_upcoming = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Échéance proche",
        end_at=now + timezone.timedelta(hours=1),
    )
    later_upcoming = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Échéance lointaine",
        end_at=now + timezone.timedelta(days=3),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert feed_execution_ids(response.json()) == [
        str(earlier_overdue.id),
        str(later_overdue.id),
        str(sooner_upcoming.id),
        str(later_upcoming.id),
    ]


def test_feed_pending_validation_before_in_progress_globally(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    in_progress = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="En cours urgent",
        status=EXECUTION_STATUS_IN_PROGRESS,
        end_at=now + timezone.timedelta(hours=1),
    )
    pending = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="À valider plus tard",
        status=EXECUTION_STATUS_PENDING_VALIDATION,
        requires_validation=True,
        end_at=now + timezone.timedelta(days=7),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert feed_execution_ids(response.json()) == [
        str(pending.id),
        str(in_progress.id),
    ]


def test_feed_pagination_preserves_deadline_order(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    executions = [
        create_execution(
            owner_membership,
            business_unit=business_unit,
            title=f"Ordered {index}",
            end_at=now + timezone.timedelta(hours=index + 1),
        )
        for index in range(3)
    ]
    token = login(api_client, user=owner_membership.user)
    first = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general")
        + "&page_size=2",
        **auth_headers(token),
    )
    second = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general")
        + f"&page_size=2&cursor={first.json()['next_cursor']}",
        **auth_headers(token),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    merged_ids = feed_execution_ids(first.json()) + feed_execution_ids(second.json())
    assert merged_ids == [str(execution.id) for execution in executions]


def test_feed_invalid_cursor_returns_400(api_client, owner_membership):
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + feed_query("general")
        + "&cursor=not-a-valid-cursor",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_action_plan_execution_overdue_respects_as_of_reference_time(
    owner_membership,
    business_unit,
):
    now = timezone.now()
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Frontière échéance",
        end_at=now - timezone.timedelta(hours=1),
    )
    assert action_plan_execution_overdue(execution=execution, now=now) is True
    assert (
        action_plan_execution_overdue(
            execution=execution,
            now=now - timezone.timedelta(hours=2),
        )
        is False
    )


def test_feed_marks_overdue_using_request_as_of(
    api_client,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    overdue = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Retard feed",
        end_at=now - timezone.timedelta(minutes=30),
    )
    upcoming = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="À venir feed",
        end_at=now + timezone.timedelta(hours=2),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    items_by_id = {
        item["action_plan_execution"]["id"]: item["action_plan_execution"]
        for item in response.json()["items"]
    }
    assert items_by_id[str(overdue.id)]["is_overdue"] is True
    assert items_by_id[str(upcoming.id)]["is_overdue"] is False


def test_cross_establishment_feed_returns_empty(
    api_client,
    owner_membership,
    business_unit,
):
    create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Tenant scoped",
    )
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_feed_materializes_visible_schedule_execution(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=recurrence_days_for_visible_today(),
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **visible_schedule_window(),
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()

    token = login(api_client, user=staff_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(staff_membership.establishment_id) + feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


def test_feed_survives_invalid_visible_schedule(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
    caplog: pytest.LogCaptureFixture,
):
    valid_execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Valid execution",
    )
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=recurrence_days_for_visible_today(),
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **visible_schedule_window(),
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    schedule.last_materialized_at = None
    schedule.save(update_fields=["last_materialized_at", "updated_at"])

    deactivate_action_plan(action_plan=catalog_action_plan, actor=owner_membership)
    schedule.refresh_from_db()
    assert schedule.status == SCHEDULE_STATUS_INACTIVE
    ActionPlanSchedule.objects.filter(pk=schedule.pk).update(status=SCHEDULE_STATUS_ACTIVE)
    schedule.refresh_from_db()

    materialization_logger = "houston.action_plans.materialization"
    api_exceptions_logger = "houston.core.api.exceptions"
    with caplog.at_level(logging.WARNING):
        token = login(api_client, user=owner_membership.user)
        response = api_client.get(
            action_plan_execution_feed_url(owner_membership.establishment_id)
            + feed_query("general"),
            **auth_headers(token),
        )

    assert response.status_code == 200
    titles = [item["action_plan_execution"]["title"] for item in response.json()["items"]]
    assert "Valid execution" in titles
    assert str(valid_execution.id) in feed_execution_ids(response.json())

    skip_records = [
        record
        for record in caplog.records
        if record.name == materialization_logger
        and record.getMessage() == "action_plan_schedule_materialization_skipped"
    ]
    assert skip_records
    assert any(
        getattr(record, "materialization_path", None) == "read_path"
        and getattr(record, "schedule_id", None) == str(schedule.id)
        for record in skip_records
    )
    assert not any(
        record.name == api_exceptions_logger
        and record.getMessage() == "api_unhandled_exception"
        for record in caplog.records
    )


def test_action_plan_executionfeed_query_count_baseline_empty(
    api_client,
    owner_membership,
):
    token = login(api_client, user=owner_membership.user)
    url = action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query(
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


def test_action_plan_executionfeed_query_count_with_one_item(
    api_client,
    owner_membership,
    business_unit,
):
    create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Query baseline",
    )
    token = login(api_client, user=owner_membership.user)
    url = action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query(
        "general",
    )

    from houston.testing.query_baseline import (
        ACTION_PLAN_EXECUTION_FEED_ONE_ITEM_MAX_QUERIES,
        assert_query_count_at_most,
        capture_queries,
    )

    with capture_queries() as context:
        response = api_client.get(url, **auth_headers(token))

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert_query_count_at_most(
        context,
        max_queries=ACTION_PLAN_EXECUTION_FEED_ONE_ITEM_MAX_QUERIES,
        label="action_plan_execution_feed_general_one_item",
    )


def test_manager_late_scope_sees_pre_existing_execution_in_personal_view(
    api_client,
    owner_membership,
    business_unit,
    maintenance_business_unit,
):
    from houston.establishments.membership_scope import (
        MembershipScopeInput,
        MembershipScopeType,
        replace_membership_scopes,
    )
    from houston.testing.factories import create_membership
    from houston.testing.taxonomy import create_membership_with_business_unit_scope

    restaurant_staff = create_membership(
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=restaurant_staff,
        business_unit=business_unit,
    )

    pre_existing = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pre-existing restaurant execution",
        assignees=[
            build_assignee_payload(membership=restaurant_staff, business_unit=business_unit)
        ],
    )

    manager = create_membership(
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=maintenance_business_unit,
    )
    replace_membership_scopes(
        membership=manager,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
        ],
    )

    token = login(api_client, user=manager.user)
    response = api_client.get(
        action_plan_execution_feed_url(manager.establishment_id) + feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert str(pre_existing.id) in ids


def test_manager_late_scope_excludes_out_of_pole_execution_in_personal_view(
    api_client,
    owner_membership,
    business_unit,
    maintenance_business_unit,
):
    from houston.establishments.membership_scope import (
        MembershipScopeInput,
        MembershipScopeType,
        replace_membership_scopes,
    )
    from houston.testing.factories import create_membership
    from houston.testing.taxonomy import create_membership_with_business_unit_scope

    maintenance_staff = create_membership(
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=maintenance_staff,
        business_unit=maintenance_business_unit,
    )

    out_of_scope = create_execution(
        owner_membership,
        business_unit=maintenance_business_unit,
        title="Maintenance out of manager restaurant scope",
        assignees=[
            build_assignee_payload(
                membership=maintenance_staff,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    manager = create_membership(
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    replace_membership_scopes(
        membership=manager,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
        ],
    )

    token = login(api_client, user=manager.user)
    response = api_client.get(
        action_plan_execution_feed_url(manager.establishment_id) + feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert str(out_of_scope.id) not in ids


def test_staff_late_scope_does_not_see_pole_execution_without_assignment(
    api_client,
    owner_membership,
    business_unit,
):
    from houston.establishments.membership_scope import (
        MembershipScopeInput,
        MembershipScopeType,
        replace_membership_scopes,
    )
    from houston.testing.factories import create_membership
    from houston.testing.taxonomy import create_membership_with_business_unit_scope

    other_staff = create_membership(
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=other_staff,
        business_unit=business_unit,
    )

    pole_execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Restaurant execution assigned to other staff",
        tasks=[
            build_task_payload(
                task="Restaurant execution task",
                business_unit=business_unit,
                assigned_membership=other_staff,
            )
        ],
        assignees=[
            build_assignee_payload(membership=other_staff, business_unit=business_unit)
        ],
    )

    staff = create_membership(
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    replace_membership_scopes(
        membership=staff,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
        ],
    )

    token = login(api_client, user=staff.user)
    response = api_client.get(
        action_plan_execution_feed_url(staff.establishment_id) + feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert str(pole_execution.id) not in ids


def test_staff_sees_open_pole_task_execution_in_personal_feed(
    api_client,
    owner_membership,
    business_unit,
    maintenance_business_unit,
    out_of_scope_staff,
):
    open_execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Open pole task execution",
        tasks=[
            build_task_payload(task="Open pole task", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit)
        ],
    )

    token = login(api_client, user=out_of_scope_staff.user)
    response = api_client.get(
        action_plan_execution_feed_url(out_of_scope_staff.establishment_id)
        + feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert str(open_execution.id) in ids


def test_staff_does_not_see_pilot_open_pole_task_execution_in_personal_feed(
    api_client,
    owner_membership,
    business_unit,
    staff_membership,
):
    pilot_open_execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pilot open pole task execution",
        tasks=[build_task_payload(task="Open pilot pole task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit)
        ],
    )

    token = login(api_client, user=staff_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(staff_membership.establishment_id) + feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert str(pilot_open_execution.id) not in ids


def test_owner_personal_feed_includes_all_establishment_executions(
    api_client,
    owner_membership,
    business_unit,
    maintenance_business_unit,
):
    restaurant_execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Restaurant execution",
    )
    maintenance_execution = create_execution(
        owner_membership,
        business_unit=maintenance_business_unit,
        title="Maintenance execution",
    )

    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id) + feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert ids == {str(restaurant_execution.id), str(maintenance_execution.id)}


def test_mentioned_out_of_scope_staff_sees_execution_in_personal_feed(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    out_of_scope_staff,
):
    from houston.comments.services import create_action_plan_execution_comment

    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Mentioned execution",
        assignees=[
            build_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            ),
        ],
    )
    create_action_plan_execution_comment(
        author_membership=owner_membership,
        execution=execution,
        body="heads up",
        mentioned_membership_ids=[out_of_scope_staff.id],
    )

    token = login(api_client, user=out_of_scope_staff.user)
    response = api_client.get(
        action_plan_execution_feed_url(out_of_scope_staff.establishment_id)
        + feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert str(execution.id) in ids


def test_mentioned_out_of_scope_staff_does_not_see_execution_in_general_feed(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    out_of_scope_staff,
):
    from houston.comments.services import create_action_plan_execution_comment

    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Mentioned execution general hidden",
        assignees=[
            build_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            ),
        ],
    )
    create_action_plan_execution_comment(
        author_membership=owner_membership,
        execution=execution,
        body="heads up",
        mentioned_membership_ids=[out_of_scope_staff.id],
    )

    token = login(api_client, user=out_of_scope_staff.user)
    response = api_client.get(
        action_plan_execution_feed_url(out_of_scope_staff.establishment_id)
        + feed_query("general"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert str(execution.id) not in ids


def test_director_personal_feed_includes_all_establishment_executions(
    api_client,
    owner_membership,
    business_unit,
    maintenance_business_unit,
):
    from houston.testing.factories import create_membership

    director = create_membership(
        establishment=owner_membership.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    restaurant_execution = create_execution(
        director,
        business_unit=business_unit,
        title="Restaurant execution",
    )
    maintenance_execution = create_execution(
        director,
        business_unit=maintenance_business_unit,
        title="Maintenance execution",
    )

    token = login(api_client, user=director.user)
    response = api_client.get(
        action_plan_execution_feed_url(director.establishment_id) + feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert ids == {str(restaurant_execution.id), str(maintenance_execution.id)}
