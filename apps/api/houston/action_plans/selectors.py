from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Exists, OuterRef, Prefetch, Q, QuerySet, Subquery
from django.utils import timezone

from houston.action_plans.constants import (
    CATALOG_STATUS_ACTIVE,
    CONTRIBUTION_STATUS_DONE,
    CONTRIBUTION_STATUS_IN_PROGRESS,
    EXECUTION_FEED_STATUSES,
    TERMINAL_TASK_STATUSES,
    ExecutionFeedViewMode,
)
from houston.action_plans.feed_cursor import (
    DEADLINE_BUCKET_OVERDUE,
    action_plan_execution_feed_order_by,
    action_plan_execution_feed_sort_case_expressions,
    execution_deadline_bucket,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionFeedPin,
    ActionPlanExecutionTask,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
    ActionPlanTask,
)
from houston.action_plans.permissions import (
    _scope_business_unit_ids,
    action_plan_cross_pole_tasks_exist_subquery,
    action_plan_execution_readable_to_membership,
    action_plan_execution_visible_to_membership,
    action_plan_visible_to_membership,
    can_execute_action_plan_task,
    can_view_action_plan_catalog,
    can_view_action_plan_schedule,
)
from houston.comments.models import CommentMention
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES

_CONTRIBUTION_PREFETCH = (
    "assignees__execution_team__business_unit",
    "task_executions__execution_team__business_unit",
)

_PLAN_DETAIL_SELECT_RELATED = (
    "pilot_business_unit",
    "pilot_business_unit__catalog_business_unit",
    "created_by__user",
)
_PLAN_TASK_DETAIL_PREFETCH = Prefetch(
    "tasks",
    queryset=ActionPlanTask.objects.select_related(
        "business_unit",
        "business_unit__catalog_business_unit",
        "assigned_membership__user",
    ).order_by(
        "position",
        "created_at",
    ),
)

_EXECUTION_DETAIL_SELECT_RELATED = (
    "pilot_business_unit",
    "pilot_business_unit__catalog_business_unit",
    "affected_business_unit",
    "affected_business_unit__catalog_business_unit",
    "responsible_business_unit",
    "responsible_business_unit__catalog_business_unit",
    "activity_subject",
    "activity_subject__catalog_activity_subject",
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
        "execution_team__business_unit__catalog_business_unit",
    ),
)
_EXECUTION_TASK_DETAIL_PREFETCH = Prefetch(
    "task_executions",
    queryset=ActionPlanExecutionTask.objects.select_related(
        "execution_team__business_unit",
        "execution_team__business_unit__catalog_business_unit",
    ).order_by("position", "created_at"),
)
_EXECUTION_DETAIL_PREFETCH = (
    _EXECUTION_ASSIGNEE_PREFETCH,
    _EXECUTION_TASK_DETAIL_PREFETCH,
    "execution_teams__business_unit",
    "execution_teams__business_unit__catalog_business_unit",
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
    ).select_related(
        "pilot_business_unit",
        "pilot_business_unit__catalog_business_unit",
        "created_by__user",
    )

    if membership.role in ADMIN_ROLES:
        filtered = queryset
    elif membership.role == EstablishmentMembership.Role.MANAGER:
        bu_ids = _scope_business_unit_ids(membership)
        if not bu_ids:
            return ActionPlan.objects.none()
        filtered = queryset.filter(pilot_business_unit_id__in=bu_ids)
    elif membership.role == EstablishmentMembership.Role.STAFF:
        bu_ids = _scope_business_unit_ids(membership)
        if not bu_ids:
            return ActionPlan.objects.none()
        cross_pole_tasks = action_plan_cross_pole_tasks_exist_subquery()
        filtered = (
            queryset.filter(
                pilot_business_unit_id__in=bu_ids,
                catalog_status=CATALOG_STATUS_ACTIVE,
            )
            .annotate(has_cross_pole_tasks=cross_pole_tasks)
            .filter(has_cross_pole_tasks=False)
        )
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
    if not action_plan_execution_readable_to_membership(membership, execution):
        return None
    return execution


def linked_action_plan_executions_for_signal_detail(
    *,
    membership: EstablishmentMembership,
    signal,
) -> list[ActionPlanExecution]:
    queryset = (
        ActionPlanExecution.objects.filter(
            establishment_id=membership.establishment_id,
            source_signal_id=signal.id,
        )
        .select_related(
            "pilot_business_unit",
            "pilot_business_unit__catalog_business_unit",
        )
        .order_by("-last_activity_at", "-created_at")
    )
    return [
        execution
        for execution in queryset
        if action_plan_execution_visible_to_membership(membership, execution)
    ]


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
        contribution_status = _contribution_status_from_tasks(tasks) if tasks else None
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
    "action_plan__pilot_business_unit__catalog_business_unit",
    "created_by__user",
    "establishment",
)
_SCHEDULE_ASSIGNEE_PREFETCH = Prefetch(
    "schedule_assignees",
    queryset=ActionPlanScheduleAssignee.objects.select_related(
        "membership__user",
        "business_unit",
        "business_unit__catalog_business_unit",
    ),
)


_EXECUTION_FEED_SELECT_RELATED = (
    "pilot_business_unit",
    "pilot_business_unit__catalog_business_unit",
    "source_signal__affected_business_unit",
    "source_signal__responsible_business_unit",
    "source_signal__activity_subject",
    "created_by__user",
)
_EXECUTION_FEED_TASK_PREFETCH = Prefetch(
    "task_executions",
    queryset=ActionPlanExecutionTask.objects.select_related(
        "execution_team__business_unit",
        "execution_team__business_unit__catalog_business_unit",
    ).order_by("position", "created_at"),
)
_EXECUTION_FEED_ASSIGNEE_PREFETCH = Prefetch(
    "assignees",
    queryset=ActionPlanAssignee.objects.select_related(
        "membership__user",
        "execution_team__business_unit",
        "execution_team__business_unit__catalog_business_unit",
    ),
)
_EXECUTION_FEED_PREFETCH = (
    _EXECUTION_FEED_ASSIGNEE_PREFETCH,
    _EXECUTION_FEED_TASK_PREFETCH,
    "execution_teams__business_unit",
)


def _assignee_visible_to_membership_now_q(
    *,
    membership: EstablishmentMembership,
    now,
) -> Exists:
    return Exists(
        ActionPlanAssignee.objects.filter(
            action_plan_execution_id=OuterRef("pk"),
            membership_id=membership.id,
        ).filter(Q(visible_from__isnull=True) | Q(visible_from__lte=now))
    )


def _is_assigned_to_membership_q(*, membership: EstablishmentMembership) -> Exists:
    return Exists(
        ActionPlanAssignee.objects.filter(
            action_plan_execution_id=OuterRef("pk"),
            membership_id=membership.id,
        )
    )


def _has_open_pole_task_in_member_scopes_q(*, membership: EstablishmentMembership) -> Exists:
    scope_bu_ids = _scope_business_unit_ids(membership)
    if not scope_bu_ids:
        return Exists(ActionPlanExecutionTask.objects.none())
    return Exists(
        ActionPlanExecutionTask.objects.filter(
            action_plan_execution_id=OuterRef("pk"),
            assigned_membership_id__isnull=True,
            execution_team__business_unit_id__in=scope_bu_ids,
        ).exclude(
            execution_team__business_unit_id=OuterRef("pilot_business_unit_id"),
        )
    )


def _mentioned_on_execution_q(*, membership: EstablishmentMembership) -> Exists:
    return Exists(
        CommentMention.objects.filter(
            mentioned_membership_id=membership.id,
            comment__action_plan_execution_id=OuterRef("pk"),
            comment__establishment_id=membership.establishment_id,
        )
    )


def action_plan_execution_personal_feed_q(
    *,
    membership: EstablishmentMembership,
) -> Q:
    now = timezone.now()
    assigned_visible = _assignee_visible_to_membership_now_q(membership=membership, now=now)
    personal_q = Q(created_by_id=membership.id) | assigned_visible | _mentioned_on_execution_q(
        membership=membership,
    )

    if membership.role == EstablishmentMembership.Role.MANAGER:
        scope_bu_ids = _scope_business_unit_ids(membership)
        if scope_bu_ids:
            personal_q |= Q(execution_teams__business_unit_id__in=scope_bu_ids)

    if membership.role == EstablishmentMembership.Role.STAFF:
        personal_q |= _has_open_pole_task_in_member_scopes_q(membership=membership)

    return personal_q & Q(establishment_id=membership.establishment_id)


def action_plan_execution_general_feed_visibility_q(
    *,
    membership: EstablishmentMembership,
) -> Q:
    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        return Q(establishment_id=membership.establishment_id)

    personal_q = Q(created_by_id=membership.id) | _is_assigned_to_membership_q(
        membership=membership,
    )

    if membership.role == EstablishmentMembership.Role.STAFF:
        return personal_q & Q(establishment_id=membership.establishment_id)

    scope_bu_ids = _scope_business_unit_ids(membership)
    if not scope_bu_ids:
        scope_q = Q(pk__in=[])
    else:
        scope_q = Q(execution_teams__business_unit_id__in=scope_bu_ids)

    return (personal_q | scope_q) & Q(establishment_id=membership.establishment_id)


def action_plan_execution_feed_queryset(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
) -> QuerySet[ActionPlanExecution]:
    now = timezone.now()
    visibility_q = (
        action_plan_execution_personal_feed_q(membership=membership)
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
        .distinct()
    )


def action_plan_execution_pinnable_by_membership(
    membership: EstablishmentMembership,
    execution: ActionPlanExecution,
) -> bool:
    if execution.establishment_id != membership.establishment_id:
        return False
    for view_mode in ("personal", "general"):
        if action_plan_execution_feed_queryset(
            membership=membership,
            view_mode=view_mode,  # type: ignore[arg-type]
        ).filter(pk=execution.pk).exists():
            return True
    return False


def annotate_action_plan_execution_feed_pins(
    queryset: QuerySet[ActionPlanExecution],
    *,
    membership: EstablishmentMembership,
) -> QuerySet[ActionPlanExecution]:
    pin_filter = ActionPlanExecutionFeedPin.objects.filter(
        membership_id=membership.id,
        action_plan_execution_id=OuterRef("pk"),
    )
    return queryset.annotate(
        is_feed_pinned=Exists(pin_filter),
        feed_pinned_at=Subquery(pin_filter.values("pinned_at")[:1]),
    )


def annotate_action_plan_execution_feed_sort_keys(
    queryset: QuerySet[ActionPlanExecution],
    *,
    membership: EstablishmentMembership,
    as_of: datetime,
) -> QuerySet[ActionPlanExecution]:
    status_rank, deadline_bucket, feed_sort_end_at = (
        action_plan_execution_feed_sort_case_expressions(as_of)
    )
    return annotate_action_plan_execution_feed_pins(
        queryset,
        membership=membership,
    ).annotate(
        status_rank=status_rank,
        deadline_bucket=deadline_bucket,
        feed_sort_end_at=feed_sort_end_at,
    )


def apply_action_plan_execution_feed_sorting(
    queryset: QuerySet[ActionPlanExecution],
    *,
    membership: EstablishmentMembership,
    as_of=None,
) -> QuerySet[ActionPlanExecution]:
    effective_as_of = as_of or timezone.now()
    return annotate_action_plan_execution_feed_sort_keys(
        queryset,
        membership=membership,
        as_of=effective_as_of,
    ).order_by(*action_plan_execution_feed_order_by())


def action_plan_execution_overdue(
    *,
    execution: ActionPlanExecution,
    now=None,
) -> bool:
    effective_as_of = now or timezone.now()
    return (
        execution_deadline_bucket(
            end_at=execution.end_at,
            status=execution.status,
            as_of=effective_as_of,
        )
        == DEADLINE_BUCKET_OVERDUE
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
