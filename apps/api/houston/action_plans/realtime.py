from __future__ import annotations

from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
)
from houston.realtime.broadcast import schedule_establishment_invalidation


def schedule_action_plan_invalidation(*, action_plan: ActionPlan, reason: str) -> None:
    schedule_establishment_invalidation(
        establishment_id=action_plan.establishment_id,
        subject_type="action_plan",
        reason=reason,
        entity_id=action_plan.id,
    )


def schedule_action_plan_execution_invalidation(
    *,
    execution: ActionPlanExecution,
    reason: str,
) -> None:
    schedule_establishment_invalidation(
        establishment_id=execution.establishment_id,
        subject_type="action_plan_execution",
        reason=reason,
        entity_id=execution.id,
    )


def schedule_action_plan_execution_task_invalidation(
    *,
    task: ActionPlanExecutionTask,
) -> None:
    execution = task.action_plan_execution
    schedule_establishment_invalidation(
        establishment_id=execution.establishment_id,
        subject_type="action_plan_execution_task",
        reason="action_plan_execution_task.updated",
        entity_id=task.id,
    )


def schedule_action_plan_assignee_invalidation(*, assignee: ActionPlanAssignee) -> None:
    schedule_establishment_invalidation(
        establishment_id=assignee.action_plan_execution.establishment_id,
        subject_type="action_plan_assignee",
        reason="action_plan_assignee.updated",
        entity_id=assignee.id,
    )
