from __future__ import annotations

from unittest.mock import patch

import pytest

from houston.action_plans.constants import EXECUTION_STATUS_IN_PROGRESS
from houston.action_plans.exceptions import ActionPlanValidationError
from houston.action_plans.services import (
    create_action_plan_with_execution,
    create_observation_from_execution_task,
    skip_execution_task,
)
from houston.action_plans.tests.conftest import build_assignee_payload, build_task_payload
from houston.observations.models import Observation
from houston.signals.models import Signal

pytestmark = pytest.mark.django_db


def _execution_with_tasks(owner_membership, staff_membership, business_unit):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Observation handoff plan",
        requires_validation=False,
        tasks=[
            build_task_payload(task="Task 1", business_unit=business_unit, position=1),
            build_task_payload(task="Task 2", business_unit=business_unit, position=2),
        ],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit),
        ],
    )
    return execution


@patch("houston.observations.services._enqueue_observation_processing")
def test_observation_handoff_happy_path(
    mock_enqueue,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    task = execution.task_executions.order_by("position").first()
    signal_count_before = Signal.objects.count()

    updated = create_observation_from_execution_task(
        task_execution=task,
        actor=staff_membership,
        text="Broken equipment in kitchen area today",
    )

    observation = Observation.objects.get(id=updated.observation_id)
    assert observation.origin == Observation.Origin.ACTION_PLAN_TASK
    assert observation.action_plan_execution_id == execution.id
    assert observation.action_plan_execution_task_id == task.id
    assert updated.observation_id == observation.id
    assert updated.status == "observation_created"
    assert Signal.objects.count() == signal_count_before
    mock_enqueue.assert_not_called()


@patch("houston.observations.services._enqueue_observation_processing")
def test_observation_handoff_bidirectional_fk_invariants(
    mock_enqueue,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    task = execution.task_executions.order_by("position").first()

    updated = create_observation_from_execution_task(
        task_execution=task,
        actor=staff_membership,
        text="Broken equipment in kitchen area today",
    )
    observation = Observation.objects.get(id=updated.observation_id)

    assert observation.action_plan_execution_id == task.action_plan_execution_id
    assert observation.action_plan_execution_task_id == task.id
    assert updated.observation_id == observation.id
    mock_enqueue.assert_not_called()


@patch("houston.observations.services._enqueue_observation_processing")
def test_observation_handoff_rejects_short_text(
    mock_enqueue,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    task = execution.task_executions.order_by("position").first()
    with pytest.raises(ActionPlanValidationError, match="too short"):
        create_observation_from_execution_task(
            task_execution=task,
            actor=staff_membership,
            text="short",
        )
    mock_enqueue.assert_not_called()
    assert Observation.objects.count() == 0


@patch("houston.observations.services._enqueue_observation_processing")
def test_observation_handoff_does_not_change_global_execution_status(
    mock_enqueue,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    tasks = list(execution.task_executions.order_by("position"))
    create_observation_from_execution_task(
        task_execution=tasks[0],
        actor=staff_membership,
        text="Broken equipment in kitchen area today",
    )
    skip_execution_task(task_execution=tasks[1], actor=staff_membership)

    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS
    mock_enqueue.assert_not_called()
