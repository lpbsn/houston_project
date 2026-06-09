from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.checklists.constants import (
    ASSIGNMENT_STATUS_ACTIVE,
    EXECUTION_SOURCE_ASSIGNMENT,
    EXECUTION_STATUS_ASSIGNED,
    RECURRENCE_DAY_FRIDAY,
    RECURRENCE_DAY_MONDAY,
    RECURRENCE_DAY_SATURDAY,
    RECURRENCE_DAY_SUNDAY,
    RECURRENCE_DAY_THURSDAY,
    RECURRENCE_DAY_TUESDAY,
    RECURRENCE_DAY_WEDNESDAY,
    TEMPLATE_STATUS_ACTIVE,
)
from houston.checklists.exceptions import ChecklistValidationError
from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTaskExecution,
    ChecklistTemplate,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.timezone_utils import (
    establishment_local_date,
    establishment_timezone,
)

MATERIALIZATION_HORIZON_DAYS = 14
VISIBLE_FROM_OFFSET = timedelta(hours=1)

_RECURRENCE_DAY_TO_WEEKDAY = {
    RECURRENCE_DAY_MONDAY: 0,
    RECURRENCE_DAY_TUESDAY: 1,
    RECURRENCE_DAY_WEDNESDAY: 2,
    RECURRENCE_DAY_THURSDAY: 3,
    RECURRENCE_DAY_FRIDAY: 4,
    RECURRENCE_DAY_SATURDAY: 5,
    RECURRENCE_DAY_SUNDAY: 6,
}


def _is_one_shot_assignment(assignment: ChecklistAssignment) -> bool:
    return not assignment.recurrence_days


def _recurrence_weekdays(assignment: ChecklistAssignment) -> set[int]:
    return {_RECURRENCE_DAY_TO_WEEKDAY[day] for day in assignment.recurrence_days}


def _occurrence_datetimes(
    *,
    assignment: ChecklistAssignment,
    occurrence_date: date,
) -> tuple[datetime, datetime]:
    tz = establishment_timezone(assignment.establishment)
    occurrence_start = datetime.combine(occurrence_date, assignment.start_at, tzinfo=tz)
    occurrence_end = datetime.combine(occurrence_date, assignment.end_at, tzinfo=tz)
    return occurrence_start, occurrence_end


def _iter_occurrence_dates(
    *,
    assignment: ChecklistAssignment,
    from_date: date,
    until_date: date,
) -> list[date]:
    start_bound = max(from_date, assignment.start_date)
    end_bound = min(until_date, assignment.end_date)
    if start_bound > end_bound:
        return []

    if _is_one_shot_assignment(assignment):
        occurrence_date = assignment.start_date
        if start_bound <= occurrence_date <= end_bound:
            return [occurrence_date]
        return []

    weekdays = _recurrence_weekdays(assignment)
    dates: list[date] = []
    current = start_bound
    while current <= end_bound:
        if current.weekday() in weekdays:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def _first_occurrence_date(assignment: ChecklistAssignment) -> date:
    dates = _iter_occurrence_dates(
        assignment=assignment,
        from_date=assignment.start_date,
        until_date=assignment.end_date,
    )
    if not dates:
        raise ChecklistValidationError("No occurrence matches the assignment schedule.")
    return dates[0]


def _create_task_execution_snapshots(
    *,
    execution: ChecklistExecution,
    template: ChecklistTemplate,
) -> list[ChecklistTaskExecution]:
    task_templates = list(
        template.task_templates.order_by("position", "created_at"),
    )
    return ChecklistTaskExecution.objects.bulk_create(
        [
            ChecklistTaskExecution(
                checklist_execution=execution,
                checklist_task_template=task_template,
                task=task_template.task,
                position=task_template.position,
                status=ChecklistTaskExecution.Status.PENDING,
            )
            for task_template in task_templates
        ]
    )


def _assert_can_materialize_from_assignment(
    *,
    assignment: ChecklistAssignment,
    template: ChecklistTemplate,
) -> None:
    if assignment.status != ASSIGNMENT_STATUS_ACTIVE:
        raise ChecklistValidationError("Assignment is not active.")
    if template.status != TEMPLATE_STATUS_ACTIVE:
        raise ChecklistValidationError("Template is not active.")
    if not template.task_templates.exists():
        raise ChecklistValidationError("Checklist template must have at least one task.")


@transaction.atomic
def materialize_execution_from_assignment(
    *,
    assignment: ChecklistAssignment,
    occurrence_date: date,
) -> ChecklistExecution:
    if occurrence_date is None:
        raise ChecklistValidationError("occurrence_date is required for assignment executions.")

    existing = ChecklistExecution.objects.filter(
        checklist_assignment=assignment,
        occurrence_date=occurrence_date,
    ).first()
    if existing is not None:
        return existing

    if assignment.checklist_template_id is None:
        raise ChecklistValidationError("Assignment has no checklist template.")

    template = (
        ChecklistTemplate.objects.filter(id=assignment.checklist_template_id)
        .prefetch_related("task_templates")
        .first()
    )
    if template is None:
        raise ChecklistValidationError("Invalid checklist template.")

    _assert_can_materialize_from_assignment(assignment=assignment, template=template)

    if assignment.establishment_id != template.establishment_id:
        raise ChecklistValidationError("Assignment establishment does not match template.")
    if assignment.business_unit_id != template.business_unit_id:
        raise ChecklistValidationError("Assignment business unit does not match template.")
    if assignment.assigned_to.establishment_id != assignment.establishment_id:
        raise ChecklistValidationError("Assignee does not belong to this establishment.")
    if assignment.assigned_by.establishment_id != assignment.establishment_id:
        raise ChecklistValidationError("Assigner does not belong to this establishment.")

    occurrence_start_at, occurrence_end_at = _occurrence_datetimes(
        assignment=assignment,
        occurrence_date=occurrence_date,
    )
    visible_from = occurrence_start_at - VISIBLE_FROM_OFFSET
    now = timezone.now()

    try:
        execution = ChecklistExecution.objects.create(
            checklist_template=template,
            checklist_assignment=assignment,
            execution_source=EXECUTION_SOURCE_ASSIGNMENT,
            establishment_id=assignment.establishment_id,
            assigned_to=assignment.assigned_to,
            assigned_by=assignment.assigned_by,
            business_unit_id=assignment.business_unit_id,
            template_title=template.title,
            template_description=template.description,
            start_at=occurrence_start_at,
            visible_from=visible_from,
            end_at=occurrence_end_at,
            occurrence_date=occurrence_date,
            status=EXECUTION_STATUS_ASSIGNED,
            last_activity_at=now,
        )
    except IntegrityError:
        return ChecklistExecution.objects.get(
            checklist_assignment=assignment,
            occurrence_date=occurrence_date,
        )

    _create_task_execution_snapshots(execution=execution, template=template)
    return execution


def materialize_assignment_occurrences_in_horizon(
    *,
    assignment: ChecklistAssignment,
    horizon_days: int = MATERIALIZATION_HORIZON_DAYS,
    now: datetime | None = None,
) -> list[ChecklistExecution]:
    if assignment.status != ASSIGNMENT_STATUS_ACTIVE:
        return []
    if assignment.checklist_template_id is None:
        return []

    current = establishment_local_date(
        establishment=assignment.establishment,
        at=now or timezone.now(),
    )
    until_date = current + timedelta(days=horizon_days)
    materialized: list[ChecklistExecution] = []
    for occurrence_date in _iter_occurrence_dates(
        assignment=assignment,
        from_date=current,
        until_date=until_date,
    ):
        materialized.append(
            materialize_execution_from_assignment(
                assignment=assignment,
                occurrence_date=occurrence_date,
            )
        )
    if materialized:
        assignment.last_materialized_at = timezone.now()
        assignment.save(update_fields=["last_materialized_at", "updated_at"])
    return materialized


def materialize_assignments_horizon(
    *,
    establishment_id: uuid.UUID | None = None,
    horizon_days: int = MATERIALIZATION_HORIZON_DAYS,
) -> int:
    queryset = ChecklistAssignment.objects.filter(status=ASSIGNMENT_STATUS_ACTIVE)
    if establishment_id is not None:
        queryset = queryset.filter(establishment_id=establishment_id)

    count = 0
    for assignment in queryset.select_related("checklist_template", "establishment"):
        count += len(
            materialize_assignment_occurrences_in_horizon(
                assignment=assignment,
                horizon_days=horizon_days,
            )
        )
    return count


def ensure_visible_executions_materialized(
    *,
    membership: EstablishmentMembership,
    horizon_days: int = MATERIALIZATION_HORIZON_DAYS,
) -> int:
    now = timezone.now()
    local_today = establishment_local_date(
        establishment=membership.establishment,
        at=now,
    )
    assignments = ChecklistAssignment.objects.filter(
        establishment_id=membership.establishment_id,
        status=ASSIGNMENT_STATUS_ACTIVE,
    )
    count = 0
    for assignment in assignments.select_related("checklist_template", "establishment"):
        for occurrence_date in _iter_occurrence_dates(
            assignment=assignment,
            from_date=local_today,
            until_date=local_today + timedelta(days=horizon_days),
        ):
            occurrence_start_at, _ = _occurrence_datetimes(
                assignment=assignment,
                occurrence_date=occurrence_date,
            )
            if occurrence_start_at - VISIBLE_FROM_OFFSET <= now:
                materialize_execution_from_assignment(
                    assignment=assignment,
                    occurrence_date=occurrence_date,
                )
                count += 1
    return count
