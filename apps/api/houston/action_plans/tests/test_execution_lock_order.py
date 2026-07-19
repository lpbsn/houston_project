from __future__ import annotations

from unittest.mock import patch

import pytest

from houston.action_plans import services
from houston.action_plans.constants import EXECUTION_STATUS_IN_PROGRESS
from houston.action_plans.services import (
    create_action_plan_with_execution,
    mark_execution_task_done,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload

pytestmark = pytest.mark.django_db


def _execution_with_tasks(*, owner_membership, staff_membership, business_unit):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Lock order plan",
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


def test_mark_execution_task_done_locks_execution_then_task(
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    task = execution.task_executions.order_by("position").first()
    previous_activity = execution.last_activity_at
    lock_order: list[str] = []

    lock_execution = services._lock_execution_for_write
    lock_task = services._lock_execution_task_after_execution

    def record_execution(*, execution_id):
        lock_order.append("execution")
        return lock_execution(execution_id=execution_id)

    def record_task(*, execution, task_execution_id):
        lock_order.append("task")
        return lock_task(execution=execution, task_execution_id=task_execution_id)

    with (
        patch.object(services, "_lock_execution_for_write", side_effect=record_execution),
        patch.object(
            services,
            "_lock_execution_task_after_execution",
            side_effect=record_task,
        ),
    ):
        mark_execution_task_done(task_execution=task, actor=staff_membership)

    assert lock_order == ["execution", "task"]

    execution.refresh_from_db()
    task.refresh_from_db()
    assert task.status == "done"
    assert task.completed_at is not None
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS
    assert execution.last_activity_at >= previous_activity
