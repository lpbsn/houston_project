from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from houston.action_plans.constants import (
    CATALOG_STATUS_ACTIVE,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_SCHEDULED,
    RECURRENCE_DAY_FRIDAY,
    RECURRENCE_DAY_MONDAY,
    RECURRENCE_DAY_SATURDAY,
    RECURRENCE_DAY_SUNDAY,
    RECURRENCE_DAY_THURSDAY,
    RECURRENCE_DAY_TUESDAY,
    RECURRENCE_DAY_WEDNESDAY,
    SCHEDULE_STATUS_ACTIVE,
    TASK_STATUS_PENDING,
)
from houston.action_plans.exceptions import ActionPlanValidationError
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
)
from houston.action_plans.permissions import _scope_business_unit_ids
from houston.action_plans.services import (
    ValidatedAssigneePayload,
    _award_gam04_for_created_in_progress_execution,
    _create_execution_record,
    _execution_task_snapshot_fields,
    _materialize_execution_structure,
    _resolve_merge_chronology,
    _validate_execution_has_content,
    merge_plan_task_assignees_into_validated_assignees,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.timezone_utils import (
    establishment_local_date,
    establishment_timezone,
)

logger = logging.getLogger(__name__)

MATERIALIZATION_HORIZON_DAYS = 14
READ_PATH_MATERIALIZATION_HORIZON_DAYS = 3
READ_PATH_MATERIALIZATION_STALE_MINUTES = 30
VISIBLE_FROM_OFFSET = timedelta(hours=1)

MATERIALIZATION_PATH_READ = "read_path"
MATERIALIZATION_PATH_BEAT_HORIZON = "beat_horizon"

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
    del schedule_assignee  # Identity only; schedule times are canonical.
    tz = establishment_timezone(schedule.establishment)
    occurrence_start = datetime.combine(occurrence_date, schedule.start_at, tzinfo=tz)
    occurrence_end = datetime.combine(occurrence_date, schedule.end_at, tzinfo=tz)
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
    active_only: bool = True,
) -> ActionPlanExecution | None:
    if schedule.use_shared_chronology:
        queryset = ActionPlanExecution.objects.filter(
            action_plan_schedule_id=schedule.id,
            occurrence_date=occurrence_date,
            use_shared_chronology=True,
        )
    elif schedule_assignee is None:
        return None
    else:
        queryset = ActionPlanExecution.objects.filter(
            action_plan_schedule_id=schedule.id,
            occurrence_date=occurrence_date,
            chronology_owner_membership_id=schedule_assignee.membership_id,
            use_shared_chronology=False,
        )
    if active_only:
        queryset = queryset.filter(
            status__in=(EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS),
        )
    return queryset.first()


def _execution_structure_is_complete(execution: ActionPlanExecution) -> bool:
    return execution.task_executions.exists() and execution.assignees.exists()


def _ensure_execution_structure_if_needed(
    *,
    execution: ActionPlanExecution,
    pilot_business_unit,
    plan_tasks: list,
    assignees: list[ValidatedAssigneePayload],
) -> None:
    if _execution_structure_is_complete(execution):
        return

    existing_teams = list(execution.execution_teams.all())
    if existing_teams:
        teams_by_bu_id = {team.business_unit_id: team for team in existing_teams}
        if assignees and not execution.assignees.exists():
            created_assignees = [
                ActionPlanAssignee(
                    action_plan_execution=execution,
                    execution_team=teams_by_bu_id[assignee.business_unit.id],
                    membership=assignee.membership,
                    start_at=assignee.start_at,
                    visible_from=assignee.visible_from,
                    end_at=assignee.end_at,
                )
                for assignee in assignees
            ]
            ActionPlanAssignee.objects.bulk_create(created_assignees)
            from houston.action_plans.realtime import schedule_action_plan_assignee_invalidation

            for created_assignee in created_assignees:
                schedule_action_plan_assignee_invalidation(assignee=created_assignee)
        if plan_tasks and not execution.task_executions.exists():
            ActionPlanExecutionTask.objects.bulk_create(
                [
                    ActionPlanExecutionTask(
                        action_plan_execution=execution,
                        execution_team=teams_by_bu_id[plan_task.business_unit_id],
                        action_plan_task=plan_task,
                        task=plan_task.task,
                        position=plan_task.position,
                        status=TASK_STATUS_PENDING,
                        **_execution_task_snapshot_fields(plan_task=plan_task),
                    )
                    for plan_task in plan_tasks
                ]
            )
        return

    _materialize_execution_structure(
        execution=execution,
        pilot_business_unit=pilot_business_unit,
        plan_tasks=plan_tasks,
        assignees=assignees,
    )


def _try_reactivate_canceled_execution(
    *,
    execution: ActionPlanExecution,
    schedule: ActionPlanSchedule,
) -> ActionPlanExecution | None:
    from houston.action_plans.schedule_services import (
        _can_reactivate_canceled_schedule_execution,
        reactivate_schedule_future_execution,
    )

    valid_dates = set(
        iter_occurrence_dates(
            schedule=schedule,
            from_date=schedule.start_date,
            until_date=schedule.end_date,
        )
    )
    current_membership_ids = set(
        schedule.schedule_assignees.values_list("membership_id", flat=True)
    )
    if not _can_reactivate_canceled_schedule_execution(
        execution=execution,
        schedule=schedule,
        valid_dates=valid_dates,
        current_membership_ids=current_membership_ids,
        now=timezone.now(),
    ):
        return None
    return reactivate_schedule_future_execution(execution=execution, schedule=schedule)


def _resolve_existing_schedule_execution(
    *,
    schedule: ActionPlanSchedule,
    occurrence_date: date,
    schedule_assignee: ActionPlanScheduleAssignee | None,
    action_plan: ActionPlan,
    plan_tasks: list,
    assignees: list[ValidatedAssigneePayload],
) -> ActionPlanExecution | None:
    existing = _existing_execution(
        schedule=schedule,
        occurrence_date=occurrence_date,
        schedule_assignee=schedule_assignee,
        active_only=True,
    )
    if existing is not None:
        _ensure_execution_structure_if_needed(
            execution=existing,
            pilot_business_unit=action_plan.pilot_business_unit,
            plan_tasks=plan_tasks,
            assignees=assignees,
        )
        return existing

    canceled = _existing_execution(
        schedule=schedule,
        occurrence_date=occurrence_date,
        schedule_assignee=schedule_assignee,
        active_only=False,
    )
    if canceled is not None and canceled.status == EXECUTION_STATUS_CANCELED:
        reactivated = _try_reactivate_canceled_execution(
            execution=canceled,
            schedule=schedule,
        )
        if reactivated is not None:
            _ensure_execution_structure_if_needed(
                execution=reactivated,
                pilot_business_unit=action_plan.pilot_business_unit,
                plan_tasks=plan_tasks,
                assignees=assignees,
            )
            return reactivated
    return None


def _occurrence_is_visible_for_schedule(
    *,
    schedule: ActionPlanSchedule,
    occurrence_date: date,
    resolved_now: datetime,
) -> bool:
    if schedule.use_shared_chronology:
        occurrence_start, _, _ = occurrence_datetimes_for_schedule(
            schedule=schedule,
            occurrence_date=occurrence_date,
        )
        return occurrence_start - VISIBLE_FROM_OFFSET <= resolved_now

    for schedule_assignee in schedule.schedule_assignees.all():
        occurrence_start, _, _ = occurrence_datetimes_for_schedule(
            schedule=schedule,
            occurrence_date=occurrence_date,
            schedule_assignee=schedule_assignee,
        )
        if occurrence_start - VISIBLE_FROM_OFFSET <= resolved_now:
            return True
    return False


@transaction.atomic
def materialize_execution_from_schedule(
    *,
    schedule: ActionPlanSchedule,
    occurrence_date: date,
    schedule_assignee: ActionPlanScheduleAssignee | None = None,
    emit_side_effects: bool = True,
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
    else:
        if schedule_assignee is None:
            raise ActionPlanValidationError(
                "schedule_assignee is required for individual chronology materialization.",
            )

    _assert_can_materialize_from_schedule(schedule=schedule, action_plan=action_plan)

    plan_tasks = list(
        action_plan.tasks.select_related("assigned_membership__user", "business_unit").order_by(
            "position",
            "created_at",
        )
    )
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

    chronology = _resolve_merge_chronology(
        use_shared_chronology=schedule.use_shared_chronology,
        start_at=occurrence_start,
        end_at=occurrence_end,
        visible_from=visible_from,
        validated_assignees=assignees,
    )
    assignees = merge_plan_task_assignees_into_validated_assignees(
        establishment_id=schedule.establishment_id,
        plan_tasks=plan_tasks,
        assignees=assignees,
        chronology=chronology,
    )

    _validate_execution_has_content(
        task_count=len(plan_tasks),
        assignee_count=len(assignees),
    )

    resolved = _resolve_existing_schedule_execution(
        schedule=schedule,
        occurrence_date=occurrence_date,
        schedule_assignee=schedule_assignee,
        action_plan=action_plan,
        plan_tasks=plan_tasks,
        assignees=assignees,
    )
    if resolved is not None:
        return resolved

    try:
        with transaction.atomic():
            execution = _create_execution_record(
                action_plan=action_plan,
                action_plan_schedule=schedule,
                chronology_owner_membership=source_membership,
                establishment_id=schedule.establishment_id,
                created_by=schedule.created_by,
                lifecycle_actor_membership=None,
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
            active_only=False,
        )
        if recovered is not None:
            if recovered.status == EXECUTION_STATUS_CANCELED:
                reactivated = _try_reactivate_canceled_execution(
                    execution=recovered,
                    schedule=schedule,
                )
                if reactivated is not None:
                    recovered = reactivated
            _ensure_execution_structure_if_needed(
                execution=recovered,
                pilot_business_unit=action_plan.pilot_business_unit,
                plan_tasks=plan_tasks,
                assignees=assignees,
            )
            return recovered
        raise

    _ensure_execution_structure_if_needed(
        execution=execution,
        pilot_business_unit=action_plan.pilot_business_unit,
        plan_tasks=plan_tasks,
        assignees=assignees,
    )
    if execution.status == EXECUTION_STATUS_IN_PROGRESS:
        _award_gam04_for_created_in_progress_execution(execution=execution)
    if emit_side_effects:
        from houston.action_plans.realtime import schedule_action_plan_execution_invalidation
        from houston.notifications.scheduling import (
            schedule_action_plan_execution_created_notification,
        )

        schedule_action_plan_execution_invalidation(
            execution=execution,
            reason="action_plan_execution.created",
        )
        schedule_action_plan_execution_created_notification(
            execution_id=execution.id,
            actor_membership_id=None,
        )
    return execution


def _materialize_occurrence(
    *,
    schedule: ActionPlanSchedule,
    occurrence_date: date,
    emit_side_effects: bool = True,
) -> list[ActionPlanExecution]:
    schedule = _load_schedule_for_materialization(schedule)
    if schedule.use_shared_chronology:
        return [
            materialize_execution_from_schedule(
                schedule=schedule,
                occurrence_date=occurrence_date,
                emit_side_effects=emit_side_effects,
            )
        ]

    materialized: list[ActionPlanExecution] = []
    for schedule_assignee in schedule.schedule_assignees.all():
        materialized.append(
            materialize_execution_from_schedule(
                schedule=schedule,
                occurrence_date=occurrence_date,
                schedule_assignee=schedule_assignee,
                emit_side_effects=emit_side_effects,
            )
        )
    return materialized


def materialize_schedule_occurrences_in_horizon(
    *,
    schedule: ActionPlanSchedule,
    horizon_days: int = MATERIALIZATION_HORIZON_DAYS,
    now: datetime | None = None,
    visible_only: bool = False,
    emit_side_effects: bool = True,
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
            if not _occurrence_is_visible_for_schedule(
                schedule=schedule,
                occurrence_date=occurrence_date,
                resolved_now=resolved_now,
            ):
                continue
        materialized.extend(
            _materialize_occurrence(
                schedule=schedule,
                occurrence_date=occurrence_date,
                emit_side_effects=emit_side_effects,
            )
        )

    if materialized:
        schedule.last_materialized_at = timezone.now()
        schedule.save(update_fields=["last_materialized_at", "updated_at"])
    return materialized


def _log_skipped_schedule_materialization(
    *,
    schedule: ActionPlanSchedule,
    materialization_path: str,
    exc: ActionPlanValidationError,
) -> None:
    logger.warning(
        "action_plan_schedule_materialization_skipped",
        extra={
            "materialization_path": materialization_path,
            "schedule_id": str(schedule.id),
            "establishment_id": str(schedule.establishment_id),
            "action_plan_id": str(schedule.action_plan_id),
            "exception_class": type(exc).__name__,
            "detail": str(exc)[:200],
        },
    )


def _materialize_schedule_best_effort(
    *,
    schedule: ActionPlanSchedule,
    horizon_days: int,
    now: datetime,
    visible_only: bool,
    materialization_path: str,
) -> int:
    try:
        return len(
            materialize_schedule_occurrences_in_horizon(
                schedule=schedule,
                horizon_days=horizon_days,
                now=now,
                visible_only=visible_only,
            )
        )
    except ActionPlanValidationError as exc:
        _log_skipped_schedule_materialization(
            schedule=schedule,
            materialization_path=materialization_path,
            exc=exc,
        )
        return 0


def materialize_schedules_horizon(
    *,
    establishment_id: uuid.UUID | None = None,
    horizon_days: int = MATERIALIZATION_HORIZON_DAYS,
) -> int:
    queryset = ActionPlanSchedule.objects.filter(status=SCHEDULE_STATUS_ACTIVE)
    if establishment_id is not None:
        queryset = queryset.filter(establishment_id=establishment_id)

    now = timezone.now()
    count = 0
    for schedule in queryset.select_related("establishment", "action_plan"):
        count += _materialize_schedule_best_effort(
            schedule=schedule,
            horizon_days=horizon_days,
            now=now,
            visible_only=False,
            materialization_path=MATERIALIZATION_PATH_BEAT_HORIZON,
        )
    return count


def _schedule_materialization_visibility_q(
    *,
    membership: EstablishmentMembership,
    view_mode: str,
) -> Q:
    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        return Q(establishment_id=membership.establishment_id)

    if view_mode == "personal":
        return Q(
            schedule_assignees__membership_id=membership.id,
            establishment_id=membership.establishment_id,
        )

    personal_q = Q(schedule_assignees__membership_id=membership.id)

    if membership.role == EstablishmentMembership.Role.STAFF:
        return personal_q & Q(establishment_id=membership.establishment_id)

    scope_bu_ids = _scope_business_unit_ids(membership)
    if not scope_bu_ids:
        scope_q = Q(pk__in=[])
    else:
        scope_q = Q(action_plan__pilot_business_unit_id__in=scope_bu_ids)

    return (personal_q | scope_q) & Q(establishment_id=membership.establishment_id)


def _existing_occurrence_dates_for_schedules(
    *,
    schedule_occurrence_dates: dict[uuid.UUID, list[date]],
) -> dict[uuid.UUID, set[date]]:
    schedule_ids = [
        schedule_id
        for schedule_id, occurrence_dates in schedule_occurrence_dates.items()
        if occurrence_dates
    ]
    result: dict[uuid.UUID, set[date]] = {
        schedule_id: set() for schedule_id in schedule_occurrence_dates
    }
    if not schedule_ids:
        return result

    all_dates = {
        occurrence_date
        for occurrence_dates in schedule_occurrence_dates.values()
        for occurrence_date in occurrence_dates
    }
    rows = ActionPlanExecution.objects.filter(
        action_plan_schedule_id__in=schedule_ids,
        occurrence_date__in=all_dates,
    ).values_list("action_plan_schedule_id", "occurrence_date")
    for schedule_id, occurrence_date in rows:
        result[schedule_id].add(occurrence_date)
    return result


def _visible_occurrence_dates_for_schedule(
    *,
    schedule: ActionPlanSchedule,
    occurrence_dates: list[date],
    resolved_now: datetime,
) -> list[date]:
    visible_dates: list[date] = []
    for occurrence_date in occurrence_dates:
        if _occurrence_is_visible_for_schedule(
            schedule=schedule,
            occurrence_date=occurrence_date,
            resolved_now=resolved_now,
        ):
            visible_dates.append(occurrence_date)
    return visible_dates


def _schedule_read_path_materialization_is_fresh(
    *,
    schedule: ActionPlanSchedule,
    visible_occurrence_dates: list[date],
    now: datetime,
    existing_dates: set[date] | None = None,
    stale_minutes: int = READ_PATH_MATERIALIZATION_STALE_MINUTES,
) -> bool:
    if schedule.last_materialized_at is None:
        return False
    if (now - schedule.last_materialized_at) >= timedelta(minutes=stale_minutes):
        return False
    if not visible_occurrence_dates:
        return True
    resolved_existing_dates = (
        existing_dates
        if existing_dates is not None
        else _existing_occurrence_dates_for_schedules(
            schedule_occurrence_dates={schedule.id: visible_occurrence_dates},
        ).get(schedule.id, set())
    )
    return resolved_existing_dates.issuperset(visible_occurrence_dates)


def ensure_visible_action_plan_executions_materialized(
    *,
    membership: EstablishmentMembership,
    view_mode: str = "personal",
    horizon_days: int = MATERIALIZATION_HORIZON_DAYS,
) -> int:
    now = timezone.now()
    local_today = establishment_local_date(
        establishment=membership.establishment,
        at=now,
    )
    read_horizon_days = min(horizon_days, READ_PATH_MATERIALIZATION_HORIZON_DAYS)
    visibility_q = _schedule_materialization_visibility_q(
        membership=membership,
        view_mode=view_mode,
    )
    schedules = list(
        ActionPlanSchedule.objects.filter(
            visibility_q,
            status=SCHEDULE_STATUS_ACTIVE,
        )
        .select_related("establishment", "action_plan")
        .prefetch_related("schedule_assignees")
        .distinct()
    )
    visible_occurrence_dates_by_schedule: dict[uuid.UUID, list[date]] = {}
    for schedule in schedules:
        try:
            occurrence_dates = iter_occurrence_dates(
                schedule=schedule,
                from_date=local_today,
                until_date=local_today + timedelta(days=read_horizon_days),
            )
            visible_occurrence_dates_by_schedule[schedule.id] = (
                _visible_occurrence_dates_for_schedule(
                    schedule=schedule,
                    occurrence_dates=occurrence_dates,
                    resolved_now=now,
                )
            )
        except ActionPlanValidationError as exc:
            _log_skipped_schedule_materialization(
                schedule=schedule,
                materialization_path=MATERIALIZATION_PATH_READ,
                exc=exc,
            )
            visible_occurrence_dates_by_schedule[schedule.id] = []

    existing_dates_by_schedule = _existing_occurrence_dates_for_schedules(
        schedule_occurrence_dates={
            schedule_id: visible_dates
            for schedule_id, visible_dates in visible_occurrence_dates_by_schedule.items()
            if visible_dates
        }
    )

    count = 0
    for schedule in schedules:
        try:
            visible_occurrence_dates = visible_occurrence_dates_by_schedule[schedule.id]
            existing_dates = existing_dates_by_schedule.get(schedule.id, set())
            if _schedule_read_path_materialization_is_fresh(
                schedule=schedule,
                visible_occurrence_dates=visible_occurrence_dates,
                now=now,
                existing_dates=existing_dates if visible_occurrence_dates else None,
            ):
                continue
            count += _materialize_schedule_best_effort(
                schedule=schedule,
                horizon_days=read_horizon_days,
                now=now,
                visible_only=True,
                materialization_path=MATERIALIZATION_PATH_READ,
            )
        except ActionPlanValidationError as exc:
            _log_skipped_schedule_materialization(
                schedule=schedule,
                materialization_path=MATERIALIZATION_PATH_READ,
                exc=exc,
            )
    return count
