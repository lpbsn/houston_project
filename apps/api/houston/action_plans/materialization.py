from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.action_plans.constants import (
    CATALOG_STATUS_ACTIVE,
    RECURRENCE_DAY_FRIDAY,
    RECURRENCE_DAY_MONDAY,
    RECURRENCE_DAY_SATURDAY,
    RECURRENCE_DAY_SUNDAY,
    RECURRENCE_DAY_THURSDAY,
    RECURRENCE_DAY_TUESDAY,
    RECURRENCE_DAY_WEDNESDAY,
    SCHEDULE_STATUS_ACTIVE,
)
from houston.action_plans.exceptions import ActionPlanValidationError
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
)
from houston.action_plans.services import (
    ValidatedAssigneePayload,
    _create_execution_record,
    _materialize_execution_structure,
    _validate_execution_has_content,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.timezone_utils import (
    establishment_local_date,
    establishment_timezone,
)

MATERIALIZATION_HORIZON_DAYS = 14
READ_PATH_MATERIALIZATION_HORIZON_DAYS = 3
READ_PATH_MATERIALIZATION_STALE_MINUTES = 30
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


def _recurrence_weekdays(schedule: ActionPlanSchedule) -> set[int]:
    return {_RECURRENCE_DAY_TO_WEEKDAY[day] for day in schedule.recurrence_days}


def iter_occurrence_dates(
    *,
    schedule: ActionPlanSchedule,
    from_date: date,
    until_date: date,
) -> list[date]:
    if not schedule.recurrence_days:
        raise ActionPlanValidationError("recurrence_days is required for schedule materialization.")

    start_bound = max(from_date, schedule.start_date)
    end_bound = min(until_date, schedule.end_date)
    if start_bound > end_bound:
        return []

    weekdays = _recurrence_weekdays(schedule)
    dates: list[date] = []
    current = start_bound
    while current <= end_bound:
        if current.weekday() in weekdays:
            dates.append(current)
        current += timedelta(days=1)
    return dates


def occurrence_datetimes_for_schedule(
    *,
    schedule: ActionPlanSchedule,
    occurrence_date: date,
    schedule_assignee: ActionPlanScheduleAssignee | None = None,
) -> tuple[datetime, datetime, datetime]:
    tz = establishment_timezone(schedule.establishment)
    start_time: time = schedule.start_at
    end_time: time = schedule.end_at
    if schedule_assignee is not None:
        if schedule_assignee.start_at is not None:
            start_time = schedule_assignee.start_at
        if schedule_assignee.end_at is not None:
            end_time = schedule_assignee.end_at

    occurrence_start = datetime.combine(occurrence_date, start_time, tzinfo=tz)
    occurrence_end = datetime.combine(occurrence_date, end_time, tzinfo=tz)
    visible_from = occurrence_start - VISIBLE_FROM_OFFSET
    return occurrence_start, occurrence_end, visible_from


def _schedule_assignee_to_validated_payload(
    *,
    schedule: ActionPlanSchedule,
    schedule_assignee: ActionPlanScheduleAssignee,
    occurrence_date: date,
) -> ValidatedAssigneePayload:
    occurrence_start, occurrence_end, visible_from = occurrence_datetimes_for_schedule(
        schedule=schedule,
        occurrence_date=occurrence_date,
        schedule_assignee=schedule_assignee,
    )
    return ValidatedAssigneePayload(
        membership=schedule_assignee.membership,
        business_unit=schedule_assignee.business_unit,
        start_at=occurrence_start,
        visible_from=visible_from,
        end_at=occurrence_end,
    )


def _assert_can_materialize_from_schedule(
    *,
    schedule: ActionPlanSchedule,
    action_plan: ActionPlan,
) -> None:
    if schedule.status != SCHEDULE_STATUS_ACTIVE:
        raise ActionPlanValidationError("Schedule is not active.")
    if not schedule.recurrence_days:
        raise ActionPlanValidationError("Schedule recurrence is required.")
    if action_plan.is_reusable and action_plan.catalog_status != CATALOG_STATUS_ACTIVE:
        raise ActionPlanValidationError("Action plan catalog entry is not active.")
    if schedule.establishment_id != action_plan.establishment_id:
        raise ActionPlanValidationError("Schedule establishment does not match action plan.")


def _load_schedule_for_materialization(schedule: ActionPlanSchedule) -> ActionPlanSchedule:
    return (
        ActionPlanSchedule.objects.select_related(
            "establishment",
            "action_plan",
            "action_plan__pilot_business_unit",
            "action_plan__affected_business_unit",
            "action_plan__responsible_business_unit",
            "action_plan__activity_subject",
            "created_by",
        )
        .prefetch_related(
            "schedule_assignees__membership",
            "schedule_assignees__business_unit",
            "action_plan__tasks__business_unit",
        )
        .get(pk=schedule.pk)
    )


def _existing_execution(
    *,
    schedule: ActionPlanSchedule,
    occurrence_date: date,
    schedule_assignee: ActionPlanScheduleAssignee | None,
) -> ActionPlanExecution | None:
    if schedule.use_shared_chronology:
        return ActionPlanExecution.objects.filter(
            action_plan_schedule_id=schedule.id,
            occurrence_date=occurrence_date,
            use_shared_chronology=True,
        ).first()
    if schedule_assignee is None:
        return None
    return ActionPlanExecution.objects.filter(
        action_plan_schedule_id=schedule.id,
        occurrence_date=occurrence_date,
        schedule_source_membership_id=schedule_assignee.membership_id,
        use_shared_chronology=False,
    ).first()


@transaction.atomic
def materialize_execution_from_schedule(
    *,
    schedule: ActionPlanSchedule,
    occurrence_date: date,
    schedule_assignee: ActionPlanScheduleAssignee | None = None,
) -> ActionPlanExecution:
    if occurrence_date is None:
        raise ActionPlanValidationError("occurrence_date is required for schedule executions.")

    schedule = _load_schedule_for_materialization(schedule)
    action_plan = schedule.action_plan

    if schedule.use_shared_chronology:
        if schedule_assignee is not None:
            raise ActionPlanValidationError(
                "schedule_assignee is not used for shared chronology materialization.",
            )
        existing = _existing_execution(
            schedule=schedule,
            occurrence_date=occurrence_date,
            schedule_assignee=None,
        )
        if existing is not None:
            return existing
    else:
        if schedule_assignee is None:
            raise ActionPlanValidationError(
                "schedule_assignee is required for individual chronology materialization.",
            )
        existing = _existing_execution(
            schedule=schedule,
            occurrence_date=occurrence_date,
            schedule_assignee=schedule_assignee,
        )
        if existing is not None:
            return existing

    _assert_can_materialize_from_schedule(schedule=schedule, action_plan=action_plan)

    plan_tasks = list(action_plan.tasks.order_by("position", "created_at"))
    schedule_assignees = list(schedule.schedule_assignees.all())
    if schedule.use_shared_chronology:
        assignees = [
            _schedule_assignee_to_validated_payload(
                schedule=schedule,
                schedule_assignee=item,
                occurrence_date=occurrence_date,
            )
            for item in schedule_assignees
        ]
        occurrence_start, occurrence_end, visible_from = occurrence_datetimes_for_schedule(
            schedule=schedule,
            occurrence_date=occurrence_date,
        )
        source_membership = None
    else:
        assignees = [
            _schedule_assignee_to_validated_payload(
                schedule=schedule,
                schedule_assignee=schedule_assignee,
                occurrence_date=occurrence_date,
            )
        ]
        occurrence_start, occurrence_end, visible_from = occurrence_datetimes_for_schedule(
            schedule=schedule,
            occurrence_date=occurrence_date,
            schedule_assignee=schedule_assignee,
        )
        source_membership = schedule_assignee.membership

    _validate_execution_has_content(
        task_count=len(plan_tasks),
        assignee_count=len(assignees),
    )

    try:
        with transaction.atomic():
            execution = _create_execution_record(
                action_plan=action_plan,
                action_plan_schedule=schedule,
                schedule_source_membership=source_membership,
                establishment_id=schedule.establishment_id,
                created_by=schedule.created_by,
                pilot_business_unit=action_plan.pilot_business_unit,
                title=action_plan.title,
                description=action_plan.description,
                requires_validation=action_plan.requires_validation,
                use_shared_chronology=schedule.use_shared_chronology,
                start_at=occurrence_start,
                end_at=occurrence_end,
                visible_from=visible_from,
                occurrence_date=occurrence_date,
                affected_business_unit=action_plan.affected_business_unit,
                responsible_business_unit=action_plan.responsible_business_unit,
                activity_subject=action_plan.activity_subject,
            )
    except IntegrityError:
        recovered = _existing_execution(
            schedule=schedule,
            occurrence_date=occurrence_date,
            schedule_assignee=schedule_assignee,
        )
        if recovered is not None:
            return recovered
        raise

    _materialize_execution_structure(
        execution=execution,
        pilot_business_unit=action_plan.pilot_business_unit,
        plan_tasks=plan_tasks,
        assignees=assignees,
    )
    return execution


def _materialize_occurrence(
    *,
    schedule: ActionPlanSchedule,
    occurrence_date: date,
) -> list[ActionPlanExecution]:
    schedule = _load_schedule_for_materialization(schedule)
    if schedule.use_shared_chronology:
        return [
            materialize_execution_from_schedule(
                schedule=schedule,
                occurrence_date=occurrence_date,
            )
        ]

    materialized: list[ActionPlanExecution] = []
    for schedule_assignee in schedule.schedule_assignees.all():
        materialized.append(
            materialize_execution_from_schedule(
                schedule=schedule,
                occurrence_date=occurrence_date,
                schedule_assignee=schedule_assignee,
            )
        )
    return materialized


def materialize_schedule_occurrences_in_horizon(
    *,
    schedule: ActionPlanSchedule,
    horizon_days: int = MATERIALIZATION_HORIZON_DAYS,
    now: datetime | None = None,
    visible_only: bool = False,
) -> list[ActionPlanExecution]:
    if schedule.status != SCHEDULE_STATUS_ACTIVE:
        return []

    current = establishment_local_date(
        establishment=schedule.establishment,
        at=now or timezone.now(),
    )
    until_date = current + timedelta(days=horizon_days)
    materialized: list[ActionPlanExecution] = []
    resolved_now = now or timezone.now()

    for occurrence_date in iter_occurrence_dates(
        schedule=schedule,
        from_date=current,
        until_date=until_date,
    ):
        if visible_only:
            occurrence_start, _, _ = occurrence_datetimes_for_schedule(
                schedule=schedule,
                occurrence_date=occurrence_date,
            )
            if occurrence_start - VISIBLE_FROM_OFFSET > resolved_now:
                continue
        materialized.extend(
            _materialize_occurrence(
                schedule=schedule,
                occurrence_date=occurrence_date,
            )
        )

    if materialized:
        schedule.last_materialized_at = timezone.now()
        schedule.save(update_fields=["last_materialized_at", "updated_at"])
    return materialized


def materialize_schedules_horizon(
    *,
    establishment_id: uuid.UUID | None = None,
    horizon_days: int = MATERIALIZATION_HORIZON_DAYS,
) -> int:
    queryset = ActionPlanSchedule.objects.filter(status=SCHEDULE_STATUS_ACTIVE)
    if establishment_id is not None:
        queryset = queryset.filter(establishment_id=establishment_id)

    count = 0
    for schedule in queryset.select_related("establishment", "action_plan"):
        count += len(
            materialize_schedule_occurrences_in_horizon(
                schedule=schedule,
                horizon_days=horizon_days,
            )
        )
    return count


def ensure_visible_action_plan_executions_materialized(
    *,
    membership: EstablishmentMembership,
    view_mode: str = "personal",
    horizon_days: int = MATERIALIZATION_HORIZON_DAYS,
) -> int:
    """Lot 5 hook — not wired in Lot 4."""
    del membership, view_mode, horizon_days
    return 0
