from __future__ import annotations

import uuid

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from houston.actions.selectors import ExecutionFeedViewMode
from houston.checklists.constants import (
    ACTIVE_EXECUTION_STATUSES,
    ASSIGNMENT_STATUS_ACTIVE,
    CHECKLIST_BADGES,
    EXECUTION_FEED_STATUSES,
    EXECUTION_STATUS_IN_PROGRESS,
    TREATED_TASK_STATUSES,
)
from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTaskExecution,
    ChecklistTaskTemplate,
    ChecklistTemplate,
)
from houston.checklists.permissions import (
    build_checklist_visibility_scope_q,
    can_execute_checklist_tasks,
    can_manage_registered_template,
    can_view_registered_catalogue,
    checklist_execution_visible_to_membership,
    checklist_template_visible_to_membership,
)
from houston.establishments.models import EstablishmentMembership

_CHECKLIST_FEED_SELECT_RELATED = (
    "business_unit",
    "checklist_template",
    "assigned_to__user",
    "assigned_by__user",
)


def get_active_execution_for_template(
    *,
    template: ChecklistTemplate,
) -> ChecklistExecution | None:
    return (
        ChecklistExecution.objects.filter(
            checklist_template=template,
            status__in=ACTIVE_EXECUTION_STATUSES,
        )
        .order_by("-created_at")
        .first()
    )


def get_in_progress_execution_for_assignment(
    *,
    assignment: ChecklistAssignment,
) -> ChecklistExecution | None:
    return (
        assignment.executions.filter(status=EXECUTION_STATUS_IN_PROGRESS)
        .order_by("-created_at")
        .first()
    )


def registered_templates_for_catalogue(
    *,
    membership: EstablishmentMembership,
    created_by_me: bool = False,
    badge: str | None = None,
    business_unit_id: uuid.UUID | None = None,
) -> QuerySet[ChecklistTemplate]:
    if not can_view_registered_catalogue(membership):
        return ChecklistTemplate.objects.none()

    queryset = ChecklistTemplate.objects.filter(
        establishment_id=membership.establishment_id,
    ).select_related("business_unit", "created_by__user")

    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        filtered = queryset
    elif membership.role in {
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    }:
        scope_q = build_checklist_visibility_scope_q(membership=membership)
        if scope_q is None:
            return ChecklistTemplate.objects.none()
        filtered = queryset.filter(scope_q)
    else:
        return ChecklistTemplate.objects.none()

    if created_by_me:
        filtered = filtered.filter(created_by_id=membership.id)
    if badge is not None:
        if badge not in CHECKLIST_BADGES:
            return ChecklistTemplate.objects.none()
        filtered = filtered.filter(badge=badge)
    if business_unit_id is not None:
        filtered = filtered.filter(business_unit_id=business_unit_id)
    return filtered


def assignments_for_management(
    *,
    membership: EstablishmentMembership,
) -> QuerySet[ChecklistAssignment]:
    if membership.role == EstablishmentMembership.Role.STAFF:
        return ChecklistAssignment.objects.none()
    if not can_view_registered_catalogue(membership):
        return ChecklistAssignment.objects.none()

    queryset = ChecklistAssignment.objects.filter(
        establishment_id=membership.establishment_id,
    ).select_related(
        "checklist_template",
        "assigned_to__user",
        "assigned_by__user",
        "business_unit",
    )

    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        return queryset

    if membership.role == EstablishmentMembership.Role.MANAGER:
        scope_q = build_checklist_visibility_scope_q(membership=membership)
        if scope_q is None:
            return ChecklistAssignment.objects.none()
        return queryset.filter(scope_q)

    return ChecklistAssignment.objects.none()


def active_assignments_for_management(
    *,
    membership: EstablishmentMembership,
) -> QuerySet[ChecklistAssignment]:
    return assignments_for_management(membership=membership).filter(
        status=ASSIGNMENT_STATUS_ACTIVE,
    )


def get_checklist_execution_for_detail(
    *,
    membership: EstablishmentMembership,
    execution_id: uuid.UUID,
) -> ChecklistExecution | None:
    execution = (
        ChecklistExecution.objects.filter(
            id=execution_id,
            establishment_id=membership.establishment_id,
        )
        .select_related(
            "business_unit",
            "assigned_to__user",
            "assigned_by__user",
            "checklist_template",
            "checklist_assignment",
        )
        .prefetch_related("task_executions")
        .first()
    )
    if execution is None:
        return None
    if not checklist_execution_visible_to_membership(membership, execution):
        return None
    return execution


def checklist_assigned_to_me_feed_q(*, membership: EstablishmentMembership) -> Q:
    return Q(assigned_to_id=membership.id) & Q(establishment_id=membership.establishment_id)


def checklist_general_feed_visibility_q(*, membership: EstablishmentMembership) -> Q:
    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        return Q(establishment_id=membership.establishment_id)

    personal_q = Q(assigned_to_id=membership.id)

    if membership.role == EstablishmentMembership.Role.STAFF:
        return personal_q & Q(establishment_id=membership.establishment_id)

    scope_q = build_checklist_visibility_scope_q(membership=membership)
    if scope_q is None:
        return personal_q & Q(establishment_id=membership.establishment_id)
    return (personal_q | scope_q) & Q(establishment_id=membership.establishment_id)


def checklist_execution_feed_queryset(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
) -> QuerySet[ChecklistExecution]:
    now = timezone.now()
    visibility_q = (
        checklist_assigned_to_me_feed_q(membership=membership)
        if view_mode == "personal"
        else checklist_general_feed_visibility_q(membership=membership)
    )
    return (
        ChecklistExecution.objects.filter(
            visibility_q,
            status__in=EXECUTION_FEED_STATUSES,
        )
        .filter(Q(visible_from__isnull=True) | Q(visible_from__lte=now))
        .select_related(*_CHECKLIST_FEED_SELECT_RELATED)
        .annotate(
            progress_total_count=Count("task_executions"),
            progress_treated_count=Count(
                "task_executions",
                filter=Q(task_executions__status__in=TREATED_TASK_STATUSES),
            ),
        )
    )


def apply_checklist_feed_sorting(
    queryset: QuerySet[ChecklistExecution],
) -> QuerySet[ChecklistExecution]:
    return queryset.order_by("-last_activity_at", "-created_at")


def checklist_execution_overdue(*, execution: ChecklistExecution, now=None) -> bool:
    if execution.end_at is None:
        return False
    if execution.status not in EXECUTION_FEED_STATUSES:
        return False
    return execution.end_at < (now or timezone.now())


_TEMPLATE_DETAIL_SELECT_RELATED = (
    "business_unit",
    "created_by__user",
)


def get_checklist_template_for_detail(
    *,
    membership: EstablishmentMembership,
    template_id: uuid.UUID,
) -> ChecklistTemplate | None:
    template = (
        ChecklistTemplate.objects.filter(
            id=template_id,
            establishment_id=membership.establishment_id,
        )
        .select_related(*_TEMPLATE_DETAIL_SELECT_RELATED)
        .prefetch_related("task_templates")
        .first()
    )
    if template is None:
        return None
    if not checklist_template_visible_to_membership(membership, template):
        return None
    return template


def get_checklist_task_template_for_management(
    *,
    membership: EstablishmentMembership,
    task_template_id: uuid.UUID,
) -> ChecklistTaskTemplate | None:
    task_template = (
        ChecklistTaskTemplate.objects.filter(
            id=task_template_id,
            checklist_template__establishment_id=membership.establishment_id,
        )
        .select_related("checklist_template", "checklist_template__business_unit")
        .first()
    )
    if task_template is None:
        return None
    template = task_template.checklist_template
    if not can_manage_registered_template(membership, template):
        return None
    return task_template


def get_checklist_assignment_for_detail(
    *,
    membership: EstablishmentMembership,
    assignment_id: uuid.UUID,
) -> ChecklistAssignment | None:
    return assignments_for_management(membership=membership).filter(id=assignment_id).first()


def get_checklist_task_execution_for_commands(
    *,
    membership: EstablishmentMembership,
    task_execution_id: uuid.UUID,
) -> ChecklistTaskExecution | None:
    task_execution = (
        ChecklistTaskExecution.objects.filter(
            id=task_execution_id,
            checklist_execution__establishment_id=membership.establishment_id,
        )
        .select_related(
            "checklist_execution",
            "checklist_execution__business_unit",
            "checklist_execution__assigned_to__user",
        )
        .first()
    )
    if task_execution is None:
        return None
    if not can_execute_checklist_tasks(membership, task_execution.checklist_execution):
        return None
    return task_execution
