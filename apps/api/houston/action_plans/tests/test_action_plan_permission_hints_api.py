from __future__ import annotations

import pytest

from houston.action_plans.constants import CATALOG_STATUS_INACTIVE
from houston.action_plans.models import ActionPlan, ActionPlanTask
from houston.action_plans.permission_hints import (
    build_action_plan_detail_permission_hints,
    build_action_plan_execution_permission_hints,
    build_action_plan_list_permission_hints,
    build_action_plan_task_execution_permission_hints,
)
from houston.action_plans.services import (
    create_action_plan_with_execution,
    mark_execution_task_done,
)
from houston.action_plans.tests.helpers import (
    action_plan_execution_url,
    action_plan_url,
    action_plans_url,
    build_assignee_payload,
    build_task_payload,
)
from houston.testing.auth import auth_headers, login

pytestmark = pytest.mark.django_db


def _hints(response):
    return response.json()["permission_hints"]


def test_catalog_detail_hints_match_builder(
    api_client,
    owner_membership,
    catalog_action_plan,
):
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_url(owner_membership.establishment_id, catalog_action_plan.id),
        **auth_headers(token),
    )
    expected = build_action_plan_detail_permission_hints(
        membership=owner_membership,
        action_plan=catalog_action_plan,
    )
    assert _hints(response) == expected


@pytest.mark.parametrize("with_tasks", [True, False])
def test_inactive_catalog_hints_match_builder(
    api_client,
    owner_membership,
    business_unit,
    with_tasks,
):
    plan = ActionPlan.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        pilot_business_unit=business_unit,
        title="Inactive catalog",
        is_reusable=True,
        catalog_status=CATALOG_STATUS_INACTIVE,
    )
    if with_tasks:
        ActionPlanTask.objects.create(
            action_plan=plan,
            business_unit=business_unit,
            task="Task",
            position=1,
        )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_url(owner_membership.establishment_id, plan.id),
        **auth_headers(token),
    )
    expected = build_action_plan_detail_permission_hints(
        membership=owner_membership,
        action_plan=plan,
    )
    assert _hints(response) == expected


def test_execution_hints_match_builder(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Hints",
        requires_validation=True,
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    owner_token = login(api_client, user=owner_membership.user)
    owner_response = api_client.get(
        action_plan_execution_url(owner_membership.establishment_id, execution.id),
        **auth_headers(owner_token),
    )
    assert _hints(owner_response) == build_action_plan_execution_permission_hints(
        membership=owner_membership,
        execution=execution,
    )

    staff_token = login(api_client, user=staff_membership.user)
    staff_response = api_client.get(
        action_plan_execution_url(staff_membership.establishment_id, execution.id),
        **auth_headers(staff_token),
    )
    assert _hints(staff_response) == build_action_plan_execution_permission_hints(
        membership=staff_membership,
        execution=execution,
    )


@pytest.mark.parametrize("mark_done", [False, True], ids=["pending", "done"])
def test_task_execution_hints_match_builder(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    mark_done,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Task hints",
        requires_validation=False,
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    task = execution.task_executions.first()
    if mark_done:
        mark_execution_task_done(task_execution=task, actor=staff_membership)
        task.refresh_from_db()

    token = login(api_client, user=staff_membership.user)
    response = api_client.get(
        action_plan_execution_url(staff_membership.establishment_id, execution.id),
        **auth_headers(token),
    )
    task_hints = response.json()["task_executions"][0]["permission_hints"]
    assert task_hints == build_action_plan_task_execution_permission_hints(
        membership=staff_membership,
        task_execution=task,
    )


def test_list_item_hints_match_builder(
    api_client,
    owner_membership,
    catalog_action_plan,
):
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plans_url(owner_membership.establishment_id),
        **auth_headers(token),
    )
    item = response.json()[0]
    assert item["permission_hints"] == build_action_plan_list_permission_hints(
        membership=owner_membership,
        action_plan=catalog_action_plan,
    )
