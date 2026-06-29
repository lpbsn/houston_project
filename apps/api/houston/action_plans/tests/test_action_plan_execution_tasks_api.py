from __future__ import annotations

from unittest.mock import patch

import pytest

from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.conftest import (
    action_plan_task_url,
    auth_headers,
    build_assignee_payload,
    build_task_payload,
    login,
)

pytestmark = pytest.mark.django_db


def _execution_with_tasks(owner, staff, business_unit):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=business_unit.id,
        title="Task commands",
        requires_validation=False,
        tasks=[
            build_task_payload(task="Task 1", business_unit=business_unit, position=1),
            build_task_payload(task="Task 2", business_unit=business_unit, position=2),
        ],
        assignees=[build_assignee_payload(membership=staff, business_unit=business_unit)],
    )
    return execution


def test_mark_done_does_not_change_execution_status(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    task = execution.task_executions.order_by("position").first()
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        action_plan_task_url(staff_membership.establishment_id, task.id, "mark-done/"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "done"
    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS


def test_skip_transition(api_client, owner_membership, staff_membership, business_unit):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    task = execution.task_executions.order_by("position").first()
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        action_plan_task_url(staff_membership.establishment_id, task.id, "skip/"),
        {"skipped_reason": "Not needed"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS


@patch("houston.observations.services._enqueue_observation_processing")
def test_create_observation_endpoint(
    mock_enqueue,
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    task = execution.task_executions.order_by("position").first()
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        action_plan_task_url(
            staff_membership.establishment_id,
            task.id,
            "create-observation/",
        ),
        {"text": "Broken equipment in kitchen area today"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "observation_created"
    assert "raw_text" not in body
    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS
    mock_enqueue.assert_not_called()
