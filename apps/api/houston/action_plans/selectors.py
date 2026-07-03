from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from django.db.models import Exists, OuterRef, Prefetch, Q, QuerySet
from django.utils import timezone

from houston.action_plans.constants import (
    CONTRIBUTION_STATUS_DONE,
    CONTRIBUTION_STATUS_IN_PROGRESS,
    EXECUTION_FEED_STATUSES,
    TERMINAL_TASK_STATUSES,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
    ActionPlanTask,
)
from houston.action_plans.permissions import (
    _scope_business_unit_ids,
    action_plan_execution_visible_to_membership,
    action_plan_visible_to_membership,
    can_execute_action_plan_task,
    can_view_action_plan_catalog,
    can_view_action_plan_schedule,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES

ExecutionFeedViewMode = Literal["personal", "general"]

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

_EXECUTION_FEED_SELECT_RELATED = _EXECUTION_DETAIL_SELECT_RELATED
_EXECUTION_FEED_PREFETCH = _EXECUTION_DETAIL_PREFETCH


def _assignee_exists_subquery(*, membership_id: uuid.UUID):
    return ActionPlanAssignee.objects.filter(
        action_plan_execution_id=OuterRef("pk"),
        membership_id=membership_id,
    )


def _visible_assignee_exists_subquery(*, membership_id: uuid.UUID, now):
    return ActionPlanAssignee.objects.filter(
        action_plan_execution_id=OuterRef("pk"),
        membership_id=membership_id,
    ).filter(Q(visible_from__isnull=True) | Q(visible_from__lte=now))


def _scope_team_exists_subquery(*, membership: EstablishmentMembership):
    business_unit_ids = _scope_business_unit_ids(membership)
    if not business_unit_ids:
        return None
    return ActionPlanExecutionTeam.objects.filter(
        action_plan_execution_id=OuterRef("pk"),
        business_unit_id__in=business_unit_ids,
    )


def action_plan_execution_personal_feed_q(
    *,
    membership: EstablishmentMembership,
    now,
) -> Q:
    visible_assignee_exists = _visible_assignee_exists_subquery(
        membership_id=membership.id,
        now=now,
    )
    return (
        Q(created_by_id=membership.id) | Q(Exists(visible_assignee_exists))
    ) & Q(establishment_id=membership.establishment_id)


def action_plan_execution_general_feed_visibility_q(
    *,
    membership: EstablishmentMembership,
) -> Q:
    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        return Q(establishment_id=membership.establishment_id)

    assignee_exists = _assignee_exists_subquery(membership_id=membership.id)
    personal_q = Q(created_by_id=membership.id) | Q(Exists(assignee_exists))

    if membership.role == EstablishmentMembership.Role.STAFF:
        return personal_q & Q(establishment_id=membership.establishment_id)

    team_scope_exists = _scope_team_exists_subquery(membership=membership)
    if team_scope_exists is None:
        return personal_q & Q(establishment_id=membership.establishment_id)
    return (personal_q | Q(Exists(team_scope_exists))) & Q(
        establishment_id=membership.establishment_id,
    )


def action_plan_execution_feed_queryset(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
) -> QuerySet[ActionPlanExecution]:
    now = timezone.now()
    visibility_q = (
        action_plan_execution_personal_feed_q(membership=membership, now=now)
        if view_mode == "personal"
        else action_plan_execution_general_feed_visibility_q(membership=membership)
    )
    return (
        ActionPlanExecution.objects.filter(
            visibility_q,
            status__in=EXECUTION_FEED_STATUSES,
        )
        .filter(Q(visible_from__isnull=True) | Q(visible_from__lte=now))
        .select_related(*_EXECUTION_FEED_SELECT_RELATED)
        .prefetch_related(*_EXECUTION_FEED_PREFETCH)
    )


def apply_action_plan_execution_feed_sorting(
    queryset: QuerySet[ActionPlanExecution],
) -> QuerySet[ActionPlanExecution]:
    return queryset.order_by("-last_activity_at", "-created_at", "-id")


def action_plan_execution_overdue(
    *,
    execution: ActionPlanExecution,
    now=None,
) -> bool:
    if execution.end_at is None:
        return False
    if execution.status not in EXECUTION_FEED_STATUSES:
        return False
    reference_time = now or timezone.now()
    return execution.end_at < reference_time


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


_SCHEDULE_DETAIL_SELECT_RELATED = (
    "action_plan",
    "action_plan__pilot_business_unit",
    "created_by__user",
    "establishment",
)
_SCHEDULE_ASSIGNEE_PREFETCH = Prefetch(
    "schedule_assignees",
    queryset=ActionPlanScheduleAssignee.objects.select_related(
        "membership__user",
        "business_unit",
    ),
)


def get_action_plan_schedule_for_detail(
    *,
    membership: EstablishmentMembership,
    schedule_id: uuid.UUID,
) -> ActionPlanSchedule | None:
    schedule = (
        ActionPlanSchedule.objects.filter(
            id=schedule_id,
            establishment_id=membership.establishment_id,
        )
        .select_related(*_SCHEDULE_DETAIL_SELECT_RELATED)
        .prefetch_related(_SCHEDULE_ASSIGNEE_PREFETCH)
        .first()
    )
    if schedule is None:
        return None
    if not can_view_action_plan_schedule(membership, schedule):
        return None
    return schedule
