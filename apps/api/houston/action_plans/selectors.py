from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass

from django.db.models import Prefetch, QuerySet

from houston.action_plans.constants import (
    CONTRIBUTION_STATUS_DONE,
    CONTRIBUTION_STATUS_IN_PROGRESS,
    TERMINAL_TASK_STATUSES,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanTask,
)
from houston.action_plans.permissions import (
    _scope_business_unit_ids,
    action_plan_execution_visible_to_membership,
    action_plan_visible_to_membership,
    can_execute_action_plan_task,
    can_view_action_plan_catalog,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES

_CONTRIBUTION_PREFETCH = (
    "assignees__execution_team__business_unit",
    "task_executions__execution_team__business_unit",
)

_PLAN_DETAIL_SELECT_RELATED = (
    "pilot_business_unit",
    "created_by__user",
)
_PLAN_TASK_DETAIL_PREFETCH = Prefetch(
    "tasks",
    queryset=ActionPlanTask.objects.select_related("business_unit").order_by(
        "position",
        "created_at",
    ),
)

_EXECUTION_DETAIL_SELECT_RELATED = (
    "pilot_business_unit",
    "affected_business_unit",
    "responsible_business_unit",
    "activity_subject",
    "source_signal",
    "source_signal__affected_business_unit",
    "source_signal__responsible_business_unit",
    "source_signal__activity_subject",
    "created_by__user",
    "action_plan",
)
_EXECUTION_ASSIGNEE_PREFETCH = Prefetch(
    "assignees",
    queryset=ActionPlanAssignee.objects.select_related(
        "membership__user",
        "execution_team__business_unit",
    ),
)
_EXECUTION_TASK_DETAIL_PREFETCH = Prefetch(
    "task_executions",
    queryset=ActionPlanExecutionTask.objects.select_related(
        "execution_team__business_unit",
    ).order_by("position", "created_at"),
)
_EXECUTION_DETAIL_PREFETCH = (
    _EXECUTION_ASSIGNEE_PREFETCH,
    _EXECUTION_TASK_DETAIL_PREFETCH,
    "execution_teams__business_unit",
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


def catalog_action_plans_for_list(
    *,
    membership: EstablishmentMembership,
    created_by_me: bool = False,
    business_unit_id: uuid.UUID | None = None,
) -> QuerySet[ActionPlan]:
    if not can_view_action_plan_catalog(membership):
        return ActionPlan.objects.none()

    queryset = ActionPlan.objects.filter(
        establishment_id=membership.establishment_id,
        is_reusable=True,
    ).select_related("pilot_business_unit", "created_by__user")

    if membership.role in ADMIN_ROLES:
        filtered = queryset
    elif membership.role == EstablishmentMembership.Role.MANAGER:
        bu_ids = _scope_business_unit_ids(membership)
        if not bu_ids:
            return ActionPlan.objects.none()
        filtered = queryset.filter(pilot_business_unit_id__in=bu_ids)
    else:
        return ActionPlan.objects.none()

    if created_by_me:
        filtered = filtered.filter(created_by_id=membership.id)
    if business_unit_id is not None:
        filtered = filtered.filter(pilot_business_unit_id=business_unit_id)
    return filtered


def get_action_plan_for_detail(
    *,
    membership: EstablishmentMembership,
    action_plan_id: uuid.UUID,
) -> ActionPlan | None:
    action_plan = (
        ActionPlan.objects.filter(
            id=action_plan_id,
            establishment_id=membership.establishment_id,
        )
        .select_related(*_PLAN_DETAIL_SELECT_RELATED)
        .prefetch_related(_PLAN_TASK_DETAIL_PREFETCH)
        .first()
    )
    if action_plan is None:
        return None
    if not action_plan_visible_to_membership(membership, action_plan):
        return None
    return action_plan


def get_action_plan_execution_for_detail(
    *,
    membership: EstablishmentMembership,
    execution_id: uuid.UUID,
) -> ActionPlanExecution | None:
    execution = (
        ActionPlanExecution.objects.filter(
            id=execution_id,
            establishment_id=membership.establishment_id,
        )
        .select_related(*_EXECUTION_DETAIL_SELECT_RELATED)
        .prefetch_related(*_EXECUTION_DETAIL_PREFETCH)
        .first()
    )
    if execution is None:
        return None
    if not action_plan_execution_visible_to_membership(membership, execution):
        return None
    return execution


def get_action_plan_execution_task_for_command(
    *,
    membership: EstablishmentMembership,
    task_execution_id: uuid.UUID,
) -> ActionPlanExecutionTask | None:
    task_execution = (
        ActionPlanExecutionTask.objects.filter(
            id=task_execution_id,
            action_plan_execution__establishment_id=membership.establishment_id,
        )
        .select_related(
            "action_plan_execution",
            "execution_team__business_unit",
        )
        .first()
    )
    if task_execution is None:
        return None
    execution = task_execution.action_plan_execution
    if not action_plan_execution_visible_to_membership(membership, execution):
        return None
    if not can_execute_action_plan_task(membership, task_execution):
        return None
    return task_execution


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
