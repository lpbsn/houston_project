from __future__ import annotations

from houston.action_plans.constants import (
    ACTIVE_EXECUTION_STATUSES,
    CATALOG_STATUS_ACTIVE,
    CATALOG_STATUS_INACTIVE,
    TASK_STATUS_PENDING,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionTask,
)
from houston.action_plans.permissions import (
    can_cancel_action_plan_execution,
    can_execute_action_plan_task,
    can_manage_action_plan,
    can_mark_action_plan_execution_done,
    can_reopen_action_plan_execution,
    can_use_action_plan,
    can_validate_action_plan_execution,
    is_pilot_pole_assignee,
)
from houston.establishments.models import EstablishmentMembership


def _plan_task_count(action_plan: ActionPlan) -> int:
    task_count = getattr(action_plan, "task_count", None)
    if task_count is not None:
        return task_count
    return action_plan.tasks.count()


def _build_action_plan_permission_hints_core(
    *,
    membership: EstablishmentMembership,
    action_plan: ActionPlan,
) -> dict[str, bool]:
    can_manage = can_manage_action_plan(membership, action_plan)
    task_count = _plan_task_count(action_plan)
    has_tasks = task_count >= 1
    is_active = action_plan.catalog_status == CATALOG_STATUS_ACTIVE
    is_inactive = action_plan.catalog_status == CATALOG_STATUS_INACTIVE

    return {
        "can_update": can_manage,
        "can_activate": can_manage and is_inactive and has_tasks and action_plan.is_reusable,
        "can_deactivate": can_manage and is_active and action_plan.is_reusable,
        "can_use": can_use_action_plan(membership, action_plan),
    }


def build_action_plan_list_permission_hints(
    *,
    membership: EstablishmentMembership,
    action_plan: ActionPlan,
) -> dict[str, bool]:
    return _build_action_plan_permission_hints_core(
        membership=membership,
        action_plan=action_plan,
    )


def build_action_plan_detail_permission_hints(
    *,
    membership: EstablishmentMembership,
    action_plan: ActionPlan,
) -> dict[str, bool]:
    return _build_action_plan_permission_hints_core(
        membership=membership,
        action_plan=action_plan,
    )


def build_action_plan_execution_permission_hints(
    *,
    membership: EstablishmentMembership,
    execution: ActionPlanExecution,
) -> dict[str, bool]:
    is_active = execution.status in ACTIVE_EXECUTION_STATUSES
    return {
        "can_mark_done": is_active
        and can_mark_action_plan_execution_done(membership, execution),
        "can_validate": can_validate_action_plan_execution(membership, execution),
        "can_reopen": can_reopen_action_plan_execution(membership, execution),
        "can_cancel": is_active
        and can_cancel_action_plan_execution(membership, execution),
        "is_pilot_pole_assignee": is_pilot_pole_assignee(membership, execution),
    }


def build_action_plan_task_execution_permission_hints(
    *,
    membership: EstablishmentMembership,
    task_execution: ActionPlanExecutionTask,
) -> dict[str, bool]:
    execution = task_execution.action_plan_execution
    is_pending = task_execution.status == TASK_STATUS_PENDING
    is_active_execution = execution.status in ACTIVE_EXECUTION_STATUSES
    can_execute = (
        is_pending
        and is_active_execution
        and can_execute_action_plan_task(membership, task_execution)
    )
    return {
        "can_mark_done": can_execute,
        "can_skip": can_execute,
        "can_create_observation": can_execute,
    }
