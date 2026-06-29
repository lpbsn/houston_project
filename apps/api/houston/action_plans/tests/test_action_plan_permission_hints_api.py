from __future__ import annotations

import pytest

from houston.action_plans.constants import CATALOG_STATUS_INACTIVE
from houston.action_plans.models import ActionPlan, ActionPlanTask
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.conftest import (
    action_plan_execution_url,
    action_plan_url,
    action_plans_url,
    auth_headers,
    build_assignee_payload,
    build_task_payload,
    login,
)

pytestmark = pytest.mark.django_db


def _hints(response):
    return response.json()["permission_hints"]


def test_catalog_detail_hints_for_owner(
    api_client,
    owner_membership,
    catalog_action_plan,
):
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_url(owner_membership.establishment_id, catalog_action_plan.id),
        **auth_headers(token),
    )
    hints = _hints(response)
    assert hints["can_update"] is True
    assert hints["can_use"] is True
    assert hints["can_deactivate"] is True


def test_inactive_catalog_can_activate_hint(
    api_client,
    owner_membership,
    business_unit,
):
    plan = ActionPlan.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        pilot_business_unit=business_unit,
        title="Inactive",
        is_reusable=True,
        catalog_status=CATALOG_STATUS_INACTIVE,
    )
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
    hints = _hints(response)
    assert hints["can_activate"] is True
    assert hints["can_use"] is False


def test_execution_hints_align_with_rbac(
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
    owner_hints = _hints(owner_response)
    assert owner_hints["can_mark_done"] is True
    assert owner_hints["can_cancel"] is True

    staff_token = login(api_client, user=staff_membership.user)
    staff_response = api_client.get(
        action_plan_execution_url(staff_membership.establishment_id, execution.id),
        **auth_headers(staff_token),
    )
    staff_hints = _hints(staff_response)
    assert staff_hints["can_mark_done"] is True
    assert staff_hints["is_pilot_pole_assignee"] is True
    assert staff_hints["can_validate"] is False


def test_task_execution_hints_on_detail(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
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
    token = login(api_client, user=staff_membership.user)
    response = api_client.get(
        action_plan_execution_url(staff_membership.establishment_id, execution.id),
        **auth_headers(token),
    )
    task_hints = response.json()["task_executions"][0]["permission_hints"]
    assert task_hints["can_mark_done"] is True
    assert task_hints["can_skip"] is True
    assert task_hints["can_create_observation"] is True


def test_list_item_includes_permission_hints(
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
    assert "permission_hints" in item
    assert item["permission_hints"]["can_use"] is True
