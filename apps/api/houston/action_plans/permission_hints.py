from __future__ import annotations

from houston.action_plans.constants import (
    ACTIVE_EXECUTION_STATUSES,
    CATALOG_STATUS_ACTIVE,
    CATALOG_STATUS_INACTIVE,
    EXECUTION_STATUS_SCHEDULED,
    SCHEDULE_STATUS_ACTIVE,
    TASK_STATUS_DONE,
    TASK_STATUS_PENDING,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanSchedule,
)
from houston.action_plans.permissions import (
    can_cancel_action_plan_execution,
    can_cancel_scheduled_action_plan_execution,
    can_create_action_plan_schedule,
    can_delete_action_plan_template,
    can_execute_action_plan_task,
    can_manage_action_plan,
    can_manage_action_plan_schedule,
    can_mark_action_plan_execution_done,
    can_reopen_action_plan_execution,
    can_update_action_plan_execution_content,
    can_use_action_plan,
    can_validate_action_plan_execution,
    is_pilot_pole_assignee,
)
from houston.action_plans.schedule_services import get_active_started_execution_for_schedule
from houston.establishments.models import EstablishmentMembership


def _build_action_plan_permission_hints_core(
    *,
    membership: EstablishmentMembership,
    action_plan: ActionPlan,
) -> dict[str, bool]:
    can_manage = can_manage_action_plan(membership, action_plan)
    is_active = action_plan.catalog_status == CATALOG_STATUS_ACTIVE
    is_inactive = action_plan.catalog_status == CATALOG_STATUS_INACTIVE

    return {
        "can_update": can_manage,
        "can_activate": can_manage and is_inactive and action_plan.is_reusable,
        "can_deactivate": can_manage and is_active and action_plan.is_reusable,
        "can_delete": can_delete_action_plan_template(membership, action_plan),
        "can_use": can_use_action_plan(membership, action_plan),
        "can_schedule": can_create_action_plan_schedule(membership, action_plan),
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
    in_feed: bool = False,
) -> dict[str, bool]:
    is_active = execution.status in ACTIVE_EXECUTION_STATUSES
    is_scheduled = execution.status == EXECUTION_STATUS_SCHEDULED
    if is_scheduled:
        can_cancel = can_cancel_scheduled_action_plan_execution(membership, execution)
    else:
        can_cancel = is_active and can_cancel_action_plan_execution(membership, execution)
    return {
        "can_mark_done": is_active and can_mark_action_plan_execution_done(membership, execution),
        "can_validate": can_validate_action_plan_execution(membership, execution),
        "can_reopen": can_reopen_action_plan_execution(membership, execution),
        "can_cancel": can_cancel,
        "can_update": can_update_action_plan_execution_content(membership, execution),
        "is_pilot_pole_assignee": is_pilot_pole_assignee(membership, execution),
        "can_pin": in_feed and not is_scheduled,
    }


def read_only_action_plan_execution_permission_hints() -> dict[str, bool]:
    return {
        "can_mark_done": False,
        "can_validate": False,
        "can_reopen": False,
        "can_cancel": False,
        "can_update": False,
        "is_pilot_pole_assignee": False,
        "can_pin": False,
    }


def read_only_action_plan_task_execution_permission_hints() -> dict[str, bool]:
    return {
        "can_mark_done": False,
        "can_unmark_done": False,
        "can_skip": False,
        "can_create_observation": False,
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
    is_done = task_execution.status == TASK_STATUS_DONE
    can_unmark_done = (
        is_done
        and is_active_execution
        and can_execute_action_plan_task(membership, task_execution)
    )
    return {
        "can_mark_done": can_execute,
        "can_unmark_done": can_unmark_done,
        "can_skip": can_execute,
        "can_create_observation": can_execute,
    }


def build_action_plan_schedule_permission_hints(
    *,
    membership: EstablishmentMembership,
    schedule: ActionPlanSchedule,
) -> dict[str, bool]:
    can_manage = can_manage_action_plan_schedule(membership, schedule)
    has_active_started = get_active_started_execution_for_schedule(schedule=schedule) is not None
    return {
        "can_update": can_manage and schedule.status == SCHEDULE_STATUS_ACTIVE,
        "can_deactivate": can_manage
        and schedule.status == SCHEDULE_STATUS_ACTIVE
        and not has_active_started,
    }
