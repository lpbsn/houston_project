from __future__ import annotations

import uuid
from datetime import date, datetime, time

from django.db import transaction
from django.utils import timezone

from houston.action_plans.constants import (
    CANCEL_ORIGIN_SCHEDULE_SYNC,
    CATALOG_STATUS_ACTIVE,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    RECURRENCE_DAYS,
    SCHEDULE_STATUS_ACTIVE,
    SCHEDULE_STATUS_INACTIVE,
)
from houston.action_plans.exceptions import (
    ActionPlanConflictError,
    ActionPlanPermissionError,
    ActionPlanValidationError,
)
from houston.action_plans.materialization import (
    MATERIALIZATION_HORIZON_DAYS,
    iter_occurrence_dates,
    materialize_schedule_occurrences_in_horizon,
    occurrence_datetimes_for_schedule,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
    ActionPlanTask,
)
from houston.action_plans.permissions import (
    can_create_action_plan_schedule,
    can_manage_action_plan_schedule,
    can_use_action_plan,
    staff_catalog_action_plan_in_scope,
)
from houston.action_plans.services import (
    ValidatedAssigneePayload,
    _assert_staff_self_assignee_payload,
    _validate_actor_can_assign_poles,
    _validate_assignee_covers_business_unit,
    _validate_business_unit_in_establishment,
    _validate_execution_has_content,
    _validate_membership_in_establishment,
)
from houston.establishments.models import EstablishmentMembership

_TERMINAL_EXECUTION_STATUSES = frozenset(
    {
        EXECUTION_STATUS_DONE,
        EXECUTION_STATUS_PENDING_VALIDATION,
        EXECUTION_STATUS_CANCELED,
    }
)

_SCHEDULE_INACTIVE_PATCH_MESSAGE = "Schedule is inactive and cannot be updated."


def normalize_recurrence_days(recurrence_days) -> list[str]:
    if recurrence_days is None:
        return []
    if not isinstance(recurrence_days, list):
        raise ActionPlanValidationError("recurrence_days must be a list.")
    normalized: list[str] = []
    seen: set[str] = set()
    for day in recurrence_days:
        if not isinstance(day, str):
            raise ActionPlanValidationError("recurrence_days must contain weekday strings.")
        day_value = day.strip().lower()
        if day_value not in RECURRENCE_DAYS:
            raise ActionPlanValidationError(f"Invalid recurrence day: {day}")
        if day_value in seen:
            continue
        seen.add(day_value)
        normalized.append(day_value)
    return normalized


def normalize_recurring_recurrence_days(recurrence_days) -> list[str]:
    normalized = normalize_recurrence_days(recurrence_days)
    if not normalized:
        raise ActionPlanValidationError(
            "recurrence_days is required for recurring schedules. "
            "Use POST /action-plans/{id}/use/ for one-shot executions.",
        )
    return normalized


def _validate_schedule_window(
    *,
    start_date: date,
    end_date: date,
    start_at: time,
    end_at: time,
) -> None:
    if end_date < start_date:
        raise ActionPlanValidationError("end_date must be on or after start_date.")
    if end_at <= start_at:
        raise ActionPlanValidationError(
            "end_at must be after start_at on the same day (overnight slots are not supported).",
        )


def classify_schedule_linked_execution(
    *,
    execution: ActionPlanExecution,
    now: datetime | None = None,
) -> str:
    resolved_now = now or timezone.now()
    if execution.action_plan_schedule_id is None or execution.start_at is None:
        return "active_started"
    if execution.status in _TERMINAL_EXECUTION_STATUSES:
        return "terminal"
    if execution.status != EXECUTION_STATUS_IN_PROGRESS:
        return "terminal"
    if resolved_now >= execution.start_at:
        return "active_started"
    return "future_not_started"


def get_active_started_execution_for_schedule(
    *,
    schedule: ActionPlanSchedule,
    now: datetime | None = None,
) -> ActionPlanExecution | None:
    resolved_now = now or timezone.now()
    return (
        schedule.executions.filter(
            status=EXECUTION_STATUS_IN_PROGRESS,
            start_at__lte=resolved_now,
        )
        .only("id", "status", "start_at", "action_plan_schedule_id")
        .order_by("start_at")
        .first()
    )


def _cancel_schedule_future_execution(*, execution: ActionPlanExecution) -> None:
    now = timezone.now()
    execution.status = EXECUTION_STATUS_CANCELED
    execution.canceled_at = now
    execution.cancel_origin = CANCEL_ORIGIN_SCHEDULE_SYNC
    execution.last_activity_at = now
    execution.save(
        update_fields=[
            "status",
            "canceled_at",
            "cancel_origin",
            "last_activity_at",
            "updated_at",
        ],
    )
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation
    from houston.notifications.scheduling import (
        schedule_action_plan_execution_canceled_notification,
    )

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.canceled",
    )
    schedule_action_plan_execution_canceled_notification(
        execution_id=execution.id,
        actor_membership_id=None,
    )


def _schedule_assignee_for_execution(
    *,
    execution: ActionPlanExecution,
    schedule: ActionPlanSchedule,
) -> ActionPlanScheduleAssignee | None:
    if schedule.use_shared_chronology or execution.schedule_source_membership_id is None:
        return None
    return schedule.schedule_assignees.filter(
        membership_id=execution.schedule_source_membership_id,
    ).first()


def _effective_assignee_times(
    *,
    schedule_start_at: time,
    schedule_end_at: time,
    assignee_start_at: time | None,
    assignee_end_at: time | None,
) -> tuple[time, time]:
    effective_start = assignee_start_at if assignee_start_at is not None else schedule_start_at
    effective_end = assignee_end_at if assignee_end_at is not None else schedule_end_at
    return effective_start, effective_end


def _can_reactivate_canceled_schedule_execution(
    *,
    execution: ActionPlanExecution,
    schedule: ActionPlanSchedule,
    valid_dates: set[date],
    current_membership_ids: set[uuid.UUID],
    now: datetime,
) -> bool:
    if execution.status != EXECUTION_STATUS_CANCELED:
        return False
    if execution.cancel_origin != CANCEL_ORIGIN_SCHEDULE_SYNC:
        return False
    if execution.occurrence_date is None or execution.occurrence_date not in valid_dates:
        return False
    if execution.start_at is None or now >= execution.start_at:
        return False
    if not schedule.use_shared_chronology:
        if execution.schedule_source_membership_id is None:
            return False
        if execution.schedule_source_membership_id not in current_membership_ids:
            return False
    return True


def reactivate_schedule_future_execution(
    *,
    execution: ActionPlanExecution,
    schedule: ActionPlanSchedule,
) -> ActionPlanExecution:
    if execution.occurrence_date is None:
        return execution
    schedule_assignee = _schedule_assignee_for_execution(execution=execution, schedule=schedule)
    occurrence_start, occurrence_end, visible_from = occurrence_datetimes_for_schedule(
        schedule=schedule,
        occurrence_date=execution.occurrence_date,
        schedule_assignee=schedule_assignee,
    )
    now = timezone.now()
    execution.status = EXECUTION_STATUS_IN_PROGRESS
    execution.canceled_at = None
    execution.cancel_origin = None
    execution.start_at = occurrence_start
    execution.end_at = occurrence_end
    execution.visible_from = visible_from
    execution.last_activity_at = now
    execution.save(
        update_fields=[
            "status",
            "canceled_at",
            "cancel_origin",
            "start_at",
            "end_at",
            "visible_from",
            "last_activity_at",
            "updated_at",
        ],
    )
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.updated",
    )
    return execution


def _sync_future_execution_window(
    *,
    execution: ActionPlanExecution,
    schedule: ActionPlanSchedule,
) -> None:
    if execution.occurrence_date is None:
        return
    schedule_assignee = _schedule_assignee_for_execution(execution=execution, schedule=schedule)
    occurrence_start, occurrence_end, visible_from = occurrence_datetimes_for_schedule(
        schedule=schedule,
        occurrence_date=execution.occurrence_date,
        schedule_assignee=schedule_assignee,
    )
    now = timezone.now()
    execution.start_at = occurrence_start
    execution.end_at = occurrence_end
    execution.visible_from = visible_from
    execution.last_activity_at = now
    execution.save(
        update_fields=[
            "start_at",
            "end_at",
            "visible_from",
            "last_activity_at",
            "updated_at",
        ],
    )
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.updated",
    )


def _validate_schedule_assignee_payloads(
    *,
    establishment_id: uuid.UUID,
    assignees: list[dict],
    schedule_start_at: time,
    schedule_end_at: time,
) -> list[dict]:
    if not assignees:
        return []

    validated: list[dict] = []
    seen_membership_ids: set[uuid.UUID] = set()
    for assignee_item in assignees:
        if not isinstance(assignee_item, dict):
            raise ActionPlanValidationError("Invalid schedule assignee payload.")

        membership_id = assignee_item.get("membership_id")
        business_unit_id = assignee_item.get("business_unit_id")
        if membership_id is None or business_unit_id is None:
            raise ActionPlanValidationError(
                "Schedule assignee membership and business unit are required.",
            )

        membership = _validate_membership_in_establishment(
            establishment_id=establishment_id,
            membership_id=membership_id,
        )
        if membership.id in seen_membership_ids:
            raise ActionPlanValidationError("Duplicate schedule assignees are not allowed.")
        seen_membership_ids.add(membership.id)

        business_unit = _validate_business_unit_in_establishment(
            establishment_id=establishment_id,
            business_unit_id=business_unit_id,
        )
        _validate_assignee_covers_business_unit(
            membership=membership,
            business_unit=business_unit,
        )

        start_at = assignee_item.get("start_at")
        end_at = assignee_item.get("end_at")
        effective_start, effective_end = _effective_assignee_times(
            schedule_start_at=schedule_start_at,
            schedule_end_at=schedule_end_at,
            assignee_start_at=start_at,
            assignee_end_at=end_at,
        )
        if effective_end <= effective_start:
            raise ActionPlanValidationError(
                "Schedule assignee end_at must be after start_at.",
            )

        validated.append(
            {
                "membership": membership,
                "business_unit": business_unit,
                "start_at": start_at,
                "end_at": end_at,
            }
        )
    return validated


def _schedule_assignees_as_validated_payloads(
    validated_assignees: list[dict],
) -> list[ValidatedAssigneePayload]:
    return [
        ValidatedAssigneePayload(
            membership=item["membership"],
            business_unit=item["business_unit"],
            start_at=item.get("start_at"),
            end_at=item.get("end_at"),
        )
        for item in validated_assignees
    ]


def _resolve_staff_catalog_schedule_assignees(
    *,
    actor: EstablishmentMembership,
    pilot_business_unit,
    establishment_id: uuid.UUID,
    assignees: list[dict] | None,
    schedule_start_at: time,
    schedule_end_at: time,
) -> list[dict]:
    _assert_staff_self_assignee_payload(
        actor=actor,
        pilot_business_unit=pilot_business_unit,
        assignees=assignees,
    )
    return _validate_schedule_assignee_payloads(
        establishment_id=establishment_id,
        assignees=[
            {
                "membership_id": actor.id,
                "business_unit_id": pilot_business_unit.id,
            }
        ],
        schedule_start_at=schedule_start_at,
        schedule_end_at=schedule_end_at,
    )


def _create_schedule_assignees(
    *,
    schedule: ActionPlanSchedule,
    validated_assignees: list[dict],
) -> None:
    if not validated_assignees:
        return
    ActionPlanScheduleAssignee.objects.bulk_create(
        [
            ActionPlanScheduleAssignee(
                action_plan_schedule=schedule,
                membership=item["membership"],
                business_unit=item["business_unit"],
                start_at=item.get("start_at"),
                end_at=item.get("end_at"),
            )
            for item in validated_assignees
        ]
    )


def _replace_schedule_assignees(
    *,
    schedule: ActionPlanSchedule,
    validated_assignees: list[dict],
) -> None:
    schedule.schedule_assignees.all().delete()
    _create_schedule_assignees(schedule=schedule, validated_assignees=validated_assignees)


def _assert_action_plan_ready_for_schedule(*, action_plan: ActionPlan) -> None:
    if not action_plan.is_reusable:
        raise ActionPlanValidationError("Only reusable action plans can be scheduled.")
    if action_plan.catalog_status != CATALOG_STATUS_ACTIVE:
        raise ActionPlanValidationError("Action plan catalog entry is not active.")


@transaction.atomic
def create_action_plan_schedule(
    *,
    action_plan: ActionPlan,
    actor: EstablishmentMembership,
    start_date: date,
    end_date: date,
    start_at: time,
    end_at: time,
    recurrence_days: list[str],
    assignees: list[dict] | None = None,
    use_shared_chronology: bool = False,
) -> ActionPlanSchedule:
    if not can_create_action_plan_schedule(actor, action_plan):
        raise ActionPlanPermissionError("Not allowed to create a schedule for this action plan.")
    if not can_use_action_plan(actor, action_plan):
        raise ActionPlanPermissionError("Not allowed to use this action plan.")

    _assert_action_plan_ready_for_schedule(action_plan=action_plan)
    _validate_schedule_window(
        start_date=start_date,
        end_date=end_date,
        start_at=start_at,
        end_at=end_at,
    )
    normalized_recurrence_days = normalize_recurring_recurrence_days(recurrence_days)
    if actor.role == EstablishmentMembership.Role.STAFF:
        if not staff_catalog_action_plan_in_scope(actor, action_plan):
            raise ActionPlanPermissionError(
                "Not allowed to create a schedule for this action plan."
            )
        validated_assignees = _resolve_staff_catalog_schedule_assignees(
            actor=actor,
            pilot_business_unit=action_plan.pilot_business_unit,
            establishment_id=action_plan.establishment_id,
            assignees=assignees,
            schedule_start_at=start_at,
            schedule_end_at=end_at,
        )
    else:
        validated_assignees = _validate_schedule_assignee_payloads(
            establishment_id=action_plan.establishment_id,
            assignees=assignees or [],
            schedule_start_at=start_at,
            schedule_end_at=end_at,
        )
        _validate_actor_can_assign_poles(
            actor=actor,
            pilot_business_unit=action_plan.pilot_business_unit,
            validated_assignees=_schedule_assignees_as_validated_payloads(validated_assignees),
        )
    task_count = ActionPlanTask.objects.filter(action_plan=action_plan).count()
    _validate_execution_has_content(
        task_count=task_count,
        assignee_count=len(validated_assignees),
    )

    schedule = ActionPlanSchedule.objects.create(
        action_plan=action_plan,
        establishment_id=action_plan.establishment_id,
        created_by=actor,
        use_shared_chronology=use_shared_chronology,
        start_date=start_date,
        end_date=end_date,
        start_at=start_at,
        end_at=end_at,
        recurrence_days=normalized_recurrence_days,
        status=SCHEDULE_STATUS_ACTIVE,
    )
    _create_schedule_assignees(schedule=schedule, validated_assignees=validated_assignees)

    materialize_schedule_occurrences_in_horizon(
        schedule=schedule,
        horizon_days=MATERIALIZATION_HORIZON_DAYS,
        visible_only=True,
    )
    return schedule


def _materialize_new_schedule_occurrences(
    *,
    schedule: ActionPlanSchedule,
    now: datetime | None = None,
) -> None:
    materialize_schedule_occurrences_in_horizon(
        schedule=schedule,
        horizon_days=MATERIALIZATION_HORIZON_DAYS,
        now=now,
        visible_only=False,
    )


def _sync_schedule_executions_after_update(
    *,
    schedule: ActionPlanSchedule,
    now: datetime | None = None,
) -> None:
    resolved_now = now or timezone.now()
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

    for execution in schedule.executions.all():
        if execution.status == EXECUTION_STATUS_CANCELED:
            if _can_reactivate_canceled_schedule_execution(
                execution=execution,
                schedule=schedule,
                valid_dates=valid_dates,
                current_membership_ids=current_membership_ids,
                now=resolved_now,
            ):
                reactivate_schedule_future_execution(execution=execution, schedule=schedule)
            continue

        classification = classify_schedule_linked_execution(
            execution=execution,
            now=resolved_now,
        )
        if classification == "terminal" or classification == "active_started":
            continue
        if (
            not schedule.use_shared_chronology
            and execution.schedule_source_membership_id is not None
            and execution.schedule_source_membership_id not in current_membership_ids
        ):
            _cancel_schedule_future_execution(execution=execution)
            continue
        if execution.occurrence_date not in valid_dates:
            _cancel_schedule_future_execution(execution=execution)
            continue
        _sync_future_execution_window(execution=execution, schedule=schedule)


@transaction.atomic
def update_action_plan_schedule(
    *,
    schedule: ActionPlanSchedule,
    actor: EstablishmentMembership,
    start_date: date | None = None,
    end_date: date | None = None,
    start_at: time | None = None,
    end_at: time | None = None,
    recurrence_days: list[str] | None = None,
    assignees: list[dict] | None = None,
    use_shared_chronology: bool | None = None,
) -> ActionPlanSchedule:
    if not can_manage_action_plan_schedule(actor, schedule):
        raise ActionPlanPermissionError("Not allowed to update this schedule.")
    if schedule.status != SCHEDULE_STATUS_ACTIVE:
        raise ActionPlanValidationError(_SCHEDULE_INACTIVE_PATCH_MESSAGE)

    if use_shared_chronology is not None and schedule.executions.exists():
        raise ActionPlanValidationError(
            "use_shared_chronology cannot be changed after executions have been materialized.",
        )

    update_fields = ["updated_at"]
    next_start_date = start_date if start_date is not None else schedule.start_date
    next_end_date = end_date if end_date is not None else schedule.end_date
    next_start_at = start_at if start_at is not None else schedule.start_at
    next_end_at = end_at if end_at is not None else schedule.end_at

    if any(value is not None for value in (start_date, end_date, start_at, end_at)):
        _validate_schedule_window(
            start_date=next_start_date,
            end_date=next_end_date,
            start_at=next_start_at,
            end_at=next_end_at,
        )

    if start_date is not None:
        schedule.start_date = start_date
        update_fields.append("start_date")
    if end_date is not None:
        schedule.end_date = end_date
        update_fields.append("end_date")
    if start_at is not None:
        schedule.start_at = start_at
        update_fields.append("start_at")
    if end_at is not None:
        schedule.end_at = end_at
        update_fields.append("end_at")
    if recurrence_days is not None:
        schedule.recurrence_days = normalize_recurring_recurrence_days(recurrence_days)
        update_fields.append("recurrence_days")
    if use_shared_chronology is not None:
        schedule.use_shared_chronology = use_shared_chronology
        update_fields.append("use_shared_chronology")

    if assignees is not None:
        validated_assignees = _validate_schedule_assignee_payloads(
            establishment_id=schedule.establishment_id,
            assignees=assignees,
            schedule_start_at=next_start_at,
            schedule_end_at=next_end_at,
        )
        action_plan = schedule.action_plan
        _validate_actor_can_assign_poles(
            actor=actor,
            pilot_business_unit=action_plan.pilot_business_unit,
            validated_assignees=_schedule_assignees_as_validated_payloads(validated_assignees),
        )
        task_count = ActionPlanTask.objects.filter(action_plan=schedule.action_plan_id).count()
        _validate_execution_has_content(
            task_count=task_count,
            assignee_count=len(validated_assignees),
        )
        _replace_schedule_assignees(
            schedule=schedule,
            validated_assignees=validated_assignees,
        )

    schedule.save(update_fields=update_fields)
    _sync_schedule_executions_after_update(schedule=schedule)
    _materialize_new_schedule_occurrences(schedule=schedule)
    return schedule


@transaction.atomic
def deactivate_action_plan_schedule(
    *,
    schedule: ActionPlanSchedule,
    actor: EstablishmentMembership,
) -> ActionPlanSchedule:
    if not can_manage_action_plan_schedule(actor, schedule):
        raise ActionPlanPermissionError("Not allowed to deactivate this schedule.")

    active_execution = get_active_started_execution_for_schedule(schedule=schedule)
    if active_execution is not None:
        raise ActionPlanConflictError(
            "Cannot deactivate schedule while an execution is in progress.",
            active_execution_id=active_execution.id,
        )

    now = timezone.now()
    for execution in schedule.executions.filter(status=EXECUTION_STATUS_IN_PROGRESS):
        if classify_schedule_linked_execution(execution=execution, now=now) == (
            "future_not_started"
        ):
            _cancel_schedule_future_execution(execution=execution)

    schedule.status = SCHEDULE_STATUS_INACTIVE
    schedule.save(update_fields=["status", "updated_at"])
    return schedule
