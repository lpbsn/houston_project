from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass

from houston.action_plans.constants import (
    CONTRIBUTION_STATUS_DONE,
    CONTRIBUTION_STATUS_IN_PROGRESS,
    TERMINAL_TASK_STATUSES,
)
from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionTask

_CONTRIBUTION_PREFETCH = (
    "assignees__execution_team__business_unit",
    "task_executions__execution_team__business_unit",
)


@dataclass(frozen=True)
class InvolvedPoleSnapshot:
    business_unit_id: uuid.UUID
    contribution_status: str | None


def execution_with_contribution_context(*, execution_id: uuid.UUID) -> ActionPlanExecution:
    return (
        ActionPlanExecution.objects.select_related("pilot_business_unit")
        .prefetch_related(*_CONTRIBUTION_PREFETCH)
        .get(id=execution_id)
    )


def _group_tasks_by_business_unit(
    execution: ActionPlanExecution,
) -> dict[uuid.UUID, list[ActionPlanExecutionTask]]:
    tasks_by_business_unit: dict[uuid.UUID, list[ActionPlanExecutionTask]] = defaultdict(list)
    for task_execution in execution.task_executions.all():
        business_unit_id = task_execution.execution_team.business_unit_id
        tasks_by_business_unit[business_unit_id].append(task_execution)
    return tasks_by_business_unit


def _contribution_status_from_tasks(tasks: list[ActionPlanExecutionTask]) -> str:
    if all(task.status in TERMINAL_TASK_STATUSES for task in tasks):
        return CONTRIBUTION_STATUS_DONE
    return CONTRIBUTION_STATUS_IN_PROGRESS


def compute_pole_contribution_status(
    execution: ActionPlanExecution,
    business_unit_id: uuid.UUID,
) -> str | None:
    tasks_by_business_unit = _group_tasks_by_business_unit(execution)
    tasks = tasks_by_business_unit.get(business_unit_id)
    if not tasks:
        return None
    return _contribution_status_from_tasks(tasks)


def get_involved_poles(execution: ActionPlanExecution) -> list[InvolvedPoleSnapshot]:
    involved_business_unit_ids: set[uuid.UUID] = set()
    for assignee in execution.assignees.all():
        involved_business_unit_ids.add(assignee.execution_team.business_unit_id)

    tasks_by_business_unit = _group_tasks_by_business_unit(execution)
    involved_business_unit_ids.update(tasks_by_business_unit.keys())

    snapshots: list[InvolvedPoleSnapshot] = []
    for business_unit_id in sorted(involved_business_unit_ids, key=str):
        tasks = tasks_by_business_unit.get(business_unit_id)
        contribution_status = (
            _contribution_status_from_tasks(tasks) if tasks else None
        )
        snapshots.append(
            InvolvedPoleSnapshot(
                business_unit_id=business_unit_id,
                contribution_status=contribution_status,
            )
        )
    return snapshots
