from __future__ import annotations

import pytest

from houston.action_plans.constants import EXECUTION_STATUS_IN_PROGRESS
from houston.action_plans.exceptions import (
    ActionPlanPermissionError,
    ActionPlanValidationError,
)
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import (
    create_action_plan_with_execution,
    mark_execution_task_done,
    skip_execution_task,
)
from houston.action_plans.tests.conftest import build_assignee_payload, build_task_payload

pytestmark = pytest.mark.django_db


def _execution_with_tasks(
    *,
    owner_membership,
    staff_membership,
    business_unit,
    maintenance_business_unit=None,
    contributor_staff=None,
):
    tasks = [
        build_task_payload(task="Task 1", business_unit=business_unit, position=1),
        build_task_payload(task="Task 2", business_unit=business_unit, position=2),
    ]
    assignees = [
        build_assignee_payload(membership=staff_membership, business_unit=business_unit),
    ]
    if maintenance_business_unit is not None and contributor_staff is not None:
        tasks.append(
            build_task_payload(
                task="Maintenance task",
                business_unit=maintenance_business_unit,
                position=3,
            )
        )
        assignees.append(
            build_assignee_payload(
                membership=contributor_staff,
                business_unit=maintenance_business_unit,
            )
        )

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Task service plan",
        requires_validation=False,
        tasks=tasks,
        assignees=assignees,
    )
    return execution


def test_mark_done_updates_task_and_activity_without_global_status_change(
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

    mark_execution_task_done(task_execution=task, actor=staff_membership)
    execution.refresh_from_db()
    task.refresh_from_db()

    assert task.status == "done"
    assert task.completed_at is not None
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS
    assert execution.last_activity_at >= previous_activity


def test_all_tasks_done_does_not_complete_execution(
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    for task in execution.task_executions.order_by("position"):
        mark_execution_task_done(task_execution=task, actor=staff_membership)

    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS
    assert execution.marked_done_at is None


def test_skip_task_with_optional_reason(
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

    skip_execution_task(
        task_execution=task,
        actor=staff_membership,
        skipped_reason="  Not needed  ",
    )
    task.refresh_from_db()

    assert task.status == "skipped"
    assert task.skipped_reason == "Not needed"


def test_staff_cannot_execute_task_out_of_scope(
    owner_membership,
    staff_membership,
    business_unit,
    maintenance_business_unit,
    out_of_scope_staff,
):
    execution = _execution_with_tasks(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
        maintenance_business_unit=maintenance_business_unit,
        contributor_staff=out_of_scope_staff,
    )
    pilot_task = execution.task_executions.filter(
        execution_team__business_unit=business_unit,
    ).first()
    with pytest.raises(ActionPlanPermissionError):
        mark_execution_task_done(task_execution=pilot_task, actor=out_of_scope_staff)


def test_staff_non_assignee_cannot_execute_task(
    owner_membership,
    staff_membership,
    business_unit,
    out_of_scope_staff,
):
    execution = _execution_with_tasks(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    task = execution.task_executions.order_by("position").first()
    with pytest.raises(ActionPlanPermissionError):
        mark_execution_task_done(task_execution=task, actor=out_of_scope_staff)


def test_manager_can_execute_task_without_being_assignee(
    owner_membership,
    manager_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    task = execution.task_executions.order_by("position").first()

    mark_execution_task_done(task_execution=task, actor=manager_membership)
    task.refresh_from_db()
    assert task.status == "done"


def test_cannot_mark_done_when_execution_not_active(
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
    execution.status = ActionPlanExecution.Status.DONE
    execution.save(update_fields=["status", "updated_at"])

    with pytest.raises(ActionPlanPermissionError):
        mark_execution_task_done(task_execution=task, actor=staff_membership)


def test_cannot_mark_done_when_task_not_pending(
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
    mark_execution_task_done(task_execution=task, actor=staff_membership)

    with pytest.raises(ActionPlanValidationError, match="current state"):
        mark_execution_task_done(task_execution=task, actor=staff_membership)
