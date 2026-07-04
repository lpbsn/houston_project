from __future__ import annotations

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
)
from houston.action_plans.models import ActionPlanAssignee, ActionPlanExecution
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import (
    action_plan_execution_feed_url,
    build_assignee_payload,
    build_schedule_assignee_payload,
    build_task_payload,
    schedule_window_from_datetime,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import auth_headers, login
from houston.testing.auth import build_api_membership as build_foreign_membership

pytestmark = pytest.mark.django_db


def _feed_query(view_mode: str) -> str:
    return f"?view_mode={view_mode}"


def _create_execution(
    owner_membership,
    *,
    business_unit,
    title: str,
    assignees=None,
    tasks=None,
    status=EXECUTION_STATUS_IN_PROGRESS,
    visible_from=None,
    last_activity_at=None,
    requires_validation=False,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title=title,
        requires_validation=requires_validation,
        tasks=tasks
        or [build_task_payload(task=f"{title} task", business_unit=business_unit)],
        assignees=assignees or [],
        visible_from=visible_from,
    )
    update_fields = ["status"]
    execution.status = status
    if last_activity_at is not None:
        execution.last_activity_at = last_activity_at
        update_fields.append("last_activity_at")
    execution.save(update_fields=update_fields + ["updated_at"])
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


def test_action_plan_execution_feed_item_contract(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Feed contract",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
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
    assert payload["title"] == "Feed contract"
    assert isinstance(payload["involved_poles"], list)
    assert len(payload["involved_poles"]) >= 1
    assert "permission_hints" in payload
    assert payload["permission_hints"]["can_mark_done"] is True


def test_terminal_executions_excluded_from_feed(
    api_client,
    owner_membership,
    business_unit,
):
    _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Done execution",
        status=EXECUTION_STATUS_DONE,
    )
    _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Canceled execution",
        status=EXECUTION_STATUS_CANCELED,
    )
    active = _create_execution(
        owner_membership,
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
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert ids == {str(active.id)}


def test_future_execution_visible_from_excluded(
    api_client,
    owner_membership,
    business_unit,
):
    _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Future execution",
        visible_from=timezone.now() + timezone.timedelta(hours=2),
    )
    visible = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Visible execution",
        visible_from=timezone.now() - timezone.timedelta(minutes=5),
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general"),
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
    execution = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Individual chronology",
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
        action_plan_execution_feed_url(staff_membership.establishment_id)
        + _feed_query("personal"),
        **auth_headers(staff_token),
    )
    assert personal.status_code == 200
    assert personal.json()["items"] == []

    owner_token = login(api_client, user=owner_membership.user)
    general = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general"),
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

    assigned = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Assigned to staff",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Assigned to other",
        assignees=[
            build_assignee_payload(membership=other_staff, business_unit=business_unit)
        ],
    )
    token = login(api_client, user=staff_membership.user)
    for view_mode in ("personal", "general"):
        response = api_client.get(
            action_plan_execution_feed_url(staff_membership.establishment_id)
            + _feed_query(view_mode),
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

    scoped = _create_execution(
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
    _create_execution(
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
        + _feed_query("general"),
        **auth_headers(token),
    )
    assert general.status_code == 200
    general_ids = {item["action_plan_execution"]["id"] for item in general.json()["items"]}
    assert str(scoped.id) in general_ids

    personal = api_client.get(
        action_plan_execution_feed_url(contributor_manager_membership.establishment_id)
        + _feed_query("personal"),
        **auth_headers(token),
    )
    assert personal.status_code == 200
    personal_ids = {item["action_plan_execution"]["id"] for item in personal.json()["items"]}
    assert str(scoped.id) not in personal_ids


def test_pending_validation_execution_in_feed(
    api_client,
    owner_membership,
    business_unit,
):
    execution = _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Pending validation",
        status=EXECUTION_STATUS_PENDING_VALIDATION,
        requires_validation=True,
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general"),
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
    for index in range(4):
        _create_execution(
            owner_membership,
            business_unit=business_unit,
            title=f"Feed page {index}",
            last_activity_at=now - timezone.timedelta(minutes=index),
        )
    token = login(api_client, user=owner_membership.user)
    first = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general")
        + "&page_size=2",
        **auth_headers(token),
    )
    assert first.status_code == 200
    first_body = first.json()
    assert len(first_body["items"]) == 2
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]

    second = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general")
        + f"&page_size=2&cursor={first_body['next_cursor']}",
        **auth_headers(token),
    )
    assert second.status_code == 200
    second_body = second.json()
    assert len(second_body["items"]) == 2
    first_ids = {item["action_plan_execution"]["id"] for item in first_body["items"]}
    second_ids = {item["action_plan_execution"]["id"] for item in second_body["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_cross_establishment_feed_returns_empty(
    api_client,
    owner_membership,
    business_unit,
):
    _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Tenant scoped",
    )
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)
    response = api_client.get(
        action_plan_execution_feed_url(owner_membership.establishment_id)
        + _feed_query("general"),
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
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    weekday_names = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]
    recurrence_days = [weekday_names[now.weekday()]]
    window = schedule_window_from_datetime(now)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=recurrence_days,
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

    token = login(api_client, user=staff_membership.user)
    response = api_client.get(
        action_plan_execution_feed_url(staff_membership.establishment_id)
        + _feed_query("personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


def test_action_plan_execution_feed_query_count_baseline_empty(
    api_client,
    owner_membership,
):
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


def test_action_plan_execution_feed_query_count_with_one_item(
    api_client,
    owner_membership,
    business_unit,
):
    _create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Query baseline",
    )
    token = login(api_client, user=owner_membership.user)
    url = action_plan_execution_feed_url(owner_membership.establishment_id) + _feed_query(
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
