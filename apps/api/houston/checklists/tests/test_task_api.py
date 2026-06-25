from __future__ import annotations

from unittest.mock import patch

import pytest

from houston.actions.models import Action
from houston.actions.tests.conftest import auth_headers, login
from houston.checklists.models import ChecklistExecution
from houston.checklists.tests.conftest import (
    assignment_api_payload,
    checklist_task_execution_url,
    checklist_template_url,
    checklist_templates_url,
)
from houston.signals.models import Signal

pytestmark = pytest.mark.django_db


def _assigned_execution_with_tasks(api_client, owner, staff, business_unit):
    token = login(api_client, user=owner.user)
    template = api_client.post(
        checklist_templates_url(owner.establishment_id),
        {
            "title": "Routine",
            "business_unit_id": str(business_unit.id),
        },
        format="json",
        **auth_headers(token),
    )
    assert template.status_code == 201
    for position, task_label in enumerate(["Task 1", "Task 2"], start=1):
        task = api_client.post(
            checklist_template_url(owner.establishment_id, template.json()["id"], "tasks/"),
            {"task": task_label, "position": position},
            format="json",
            **auth_headers(token),
        )
        assert task.status_code == 201
    activate = api_client.post(
        checklist_template_url(owner.establishment_id, template.json()["id"], "activate/"),
        **auth_headers(token),
    )
    assert activate.status_code == 200
    assignment = api_client.post(
        checklist_template_url(owner.establishment_id, template.json()["id"], "assignments/"),
        assignment_api_payload(staff.id),
        format="json",
        **auth_headers(token),
    )
    assert assignment.status_code == 201
    execution = ChecklistExecution.objects.prefetch_related("task_executions").get(
        checklist_assignment_id=assignment.json()["id"],
    )
    staff_token = login(api_client, user=staff.user)
    return execution, staff_token


def test_mark_done_transition(api_client, owner_membership, staff_membership, business_unit):
    execution, token = _assigned_execution_with_tasks(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    task = execution.task_executions.order_by("position").first()
    response = api_client.post(
        checklist_task_execution_url(
            staff_membership.establishment_id,
            task.id,
            "mark-done/",
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "done"
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.IN_PROGRESS


def test_skip_transition(api_client, owner_membership, staff_membership, business_unit):
    execution, token = _assigned_execution_with_tasks(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    task = execution.task_executions.order_by("position").first()
    response = api_client.post(
        checklist_task_execution_url(
            staff_membership.establishment_id,
            task.id,
            "skip/",
        ),
        {"skipped_reason": "Not needed"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
    assert response.json()["skipped_reason"] == "Not needed"


@patch("houston.observations.services._enqueue_observation_processing")
def test_create_observation_endpoint_no_raw_text_no_direct_signal_action(
    mock_enqueue,
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution, token = _assigned_execution_with_tasks(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    task = execution.task_executions.order_by("position").first()
    action_count = Action.objects.count()
    signal_count = Signal.objects.count()
    response = api_client.post(
        checklist_task_execution_url(
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
    assert body["observation_id"] is not None
    assert Action.objects.count() == action_count
    assert Signal.objects.count() == signal_count
    mock_enqueue.assert_not_called()


@patch("houston.observations.services._enqueue_observation_processing")
def test_checklist_create_observation_rejects_second_submit_on_same_task(
    mock_enqueue,
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution, token = _assigned_execution_with_tasks(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    task = execution.task_executions.order_by("position").first()
    url = checklist_task_execution_url(
        staff_membership.establishment_id,
        task.id,
        "create-observation/",
    )
    payload = {"text": "Broken equipment in kitchen area today"}

    first_response = api_client.post(
        url,
        payload,
        format="json",
        **auth_headers(token),
    )
    assert first_response.status_code == 201
    assert first_response.json()["status"] == "observation_created"
    mock_enqueue.assert_not_called()

    second_response = api_client.post(
        url,
        {"text": "Another attempt on the same checklist task."},
        format="json",
        **auth_headers(token),
    )
    assert second_response.status_code == 400
    assert second_response.json()["code"] == "validation_error"


def test_create_observation_rejects_short_text(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution, token = _assigned_execution_with_tasks(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    task = execution.task_executions.order_by("position").first()
    response = api_client.post(
        checklist_task_execution_url(
            staff_membership.establishment_id,
            task.id,
            "create-observation/",
        ),
        {"text": "short"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
