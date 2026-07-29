from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections
from django.utils import timezone

from houston.action_plans.constants import (
    CANCEL_ORIGIN_MANUAL,
    CANCEL_ORIGIN_SCHEDULE_SYNC,
    EXECUTION_LIFECYCLE_EVENT_CANCELED,
    EXECUTION_LIFECYCLE_EVENT_CREATED,
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_LIFECYCLE_EVENT_REACTIVATED,
    EXECUTION_LIFECYCLE_EVENT_REOPENED,
    EXECUTION_LIFECYCLE_EVENT_STARTED,
    EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.lifecycle_events import sanitize_lifecycle_metadata_safe
from houston.action_plans.lifecycle_promotion import promote_due_scheduled_executions
from houston.action_plans.materialization import materialize_execution_from_schedule
from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionLifecycleEvent
from houston.action_plans.schedule_services import (
    create_action_plan_schedule,
    reactivate_schedule_future_execution,
    update_action_plan_schedule,
)
from houston.action_plans.services import (
    cancel_action_plan_execution,
    create_action_plan_with_execution,
    mark_action_plan_execution_done,
    reopen_action_plan_execution,
    validate_action_plan_execution,
)
from houston.action_plans.tests.helpers import (
    build_assignee_payload,
    build_schedule_assignee_payload,
    build_task_payload,
    recurrence_days_for_visible_today,
    schedule_window_from_datetime,
    visible_schedule_window,
)

pytestmark = pytest.mark.django_db


def _lifecycle_events(*, execution: ActionPlanExecution) -> list[ActionPlanExecutionLifecycleEvent]:
    return list(
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution=execution,
        ).order_by("occurred_at", "id")
    )


def _events_of_type(
    *,
    execution: ActionPlanExecution,
    event_type: str,
) -> list[ActionPlanExecutionLifecycleEvent]:
    return [e for e in _lifecycle_events(execution=execution) if e.event_type == event_type]


def test_sanitize_lifecycle_metadata_safe_allowlist():
    assert sanitize_lifecycle_metadata_safe(
        {
            "initial_status": "scheduled",
            "cancel_origin": "manual",
            "reactivation_origin": "schedule_sync",
            "to_status": "in_progress",
            "secret_note": "drop me",
            "nested": {"a": 1},
        }
    ) == {
        "initial_status": "scheduled",
        "cancel_origin": "manual",
        "reactivation_origin": "schedule_sync",
        "to_status": "in_progress",
    }


def test_user_create_emits_created_with_actor_and_initial_status(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="User create audit",
        tasks=[build_task_payload(task="Do work", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    created_events = _events_of_type(
        execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_CREATED,
    )
    assert len(created_events) == 1
    event = created_events[0]
    assert event.actor_membership_id == owner_membership.id
    assert event.metadata_safe == {"initial_status": EXECUTION_STATUS_IN_PROGRESS}
    assert event.occurred_at == execution.created_at
    assert event.establishment_id == execution.establishment_id
    assert not _events_of_type(execution=execution, event_type=EXECUTION_LIFECYCLE_EVENT_STARTED)
    assert execution.started_at is None


def test_user_create_scheduled_records_initial_status(
    owner_membership,
    business_unit,
    staff_membership,
):
    start_at = timezone.now() + timezone.timedelta(days=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Scheduled create audit",
        start_at=start_at,
        end_at=start_at + timezone.timedelta(hours=1),
        use_shared_chronology=True,
        tasks=[build_task_payload(task="Later", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    assert execution.status == EXECUTION_STATUS_SCHEDULED
    created = _events_of_type(execution=execution, event_type=EXECUTION_LIFECYCLE_EVENT_CREATED)
    assert len(created) == 1
    assert created[0].actor_membership_id == owner_membership.id
    assert created[0].metadata_safe == {"initial_status": EXECUTION_STATUS_SCHEDULED}


def test_materialize_create_uses_null_actor_despite_created_by(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    occurrence_date = schedule.start_date
    while occurrence_date.weekday() != 0:
        occurrence_date += timezone.timedelta(days=1)

    execution = materialize_execution_from_schedule(
        schedule=schedule,
        occurrence_date=occurrence_date,
    )

    assert execution.created_by_id == schedule.created_by_id
    created = _events_of_type(execution=execution, event_type=EXECUTION_LIFECYCLE_EVENT_CREATED)
    assert len(created) == 1
    assert created[0].actor_membership_id is None
    assert created[0].metadata_safe["initial_status"] in {
        EXECUTION_STATUS_SCHEDULED,
        EXECUTION_STATUS_IN_PROGRESS,
    }

    rematerialized = materialize_execution_from_schedule(
        schedule=schedule,
        occurrence_date=occurrence_date,
    )
    assert rematerialized.id == execution.id
    assert (
        len(_events_of_type(execution=execution, event_type=EXECUTION_LIFECYCLE_EVENT_CREATED)) == 1
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_materialization_emits_single_created_event(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now)
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()
    occurrence_date = schedule.start_date
    while occurrence_date.weekday() != 0:
        occurrence_date += timezone.timedelta(days=1)
    schedule_id = schedule.id

    def _worker(_: int):
        close_old_connections()
        try:
            from houston.action_plans.models import ActionPlanSchedule

            loaded = ActionPlanSchedule.objects.get(id=schedule_id)
            return materialize_execution_from_schedule(
                schedule=loaded,
                occurrence_date=occurrence_date,
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(_worker, range(2)))

    assert results[0].id == results[1].id
    execution = results[0]
    assert (
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution=execution,
            event_type=EXECUTION_LIFECYCLE_EVENT_CREATED,
        ).count()
        == 1
    )


def test_mark_done_validate_reopen_set_current_fields_and_matching_timestamps(
    owner_membership,
    execution_with_assignee,
):
    pending = mark_action_plan_execution_done(
        execution_id=execution_with_assignee.id,
        actor_membership=owner_membership,
    )
    pending.refresh_from_db()
    marked = _events_of_type(execution=pending, event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE)
    assert len(marked) == 1
    assert pending.marked_done_by_membership_id == owner_membership.id
    assert pending.marked_done_at == marked[0].occurred_at
    assert marked[0].actor_membership_id == owner_membership.id
    assert not _events_of_type(execution=pending, event_type=EXECUTION_LIFECYCLE_EVENT_VALIDATED)

    done = validate_action_plan_execution(
        execution_id=pending.id,
        actor_membership=owner_membership,
    )
    done.refresh_from_db()
    validated = _events_of_type(execution=done, event_type=EXECUTION_LIFECYCLE_EVENT_VALIDATED)
    assert len(validated) == 1
    assert done.validated_by_membership_id == owner_membership.id
    assert done.validated_at == validated[0].occurred_at

    reopened = reopen_action_plan_execution(
        execution_id=done.id,
        actor=owner_membership,
    )
    reopened.refresh_from_db()
    reopen_events = _events_of_type(
        execution=reopened,
        event_type=EXECUTION_LIFECYCLE_EVENT_REOPENED,
    )
    assert len(reopen_events) == 1
    assert reopened.reopened_by_membership_id == owner_membership.id
    assert reopened.reopened_at == reopen_events[0].occurred_at
    assert reopened.marked_done_at is None
    assert reopened.marked_done_by_membership_id is None
    assert reopened.validated_at is None
    assert reopened.validated_by_membership_id is None
    # Prior journal rows preserved.
    assert len(_lifecycle_events(execution=reopened)) >= 4


def test_mark_done_without_validation_emits_only_marked_done(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="No validation audit",
        requires_validation=False,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )
    execution.refresh_from_db()
    assert len(_events_of_type(execution=execution, event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE)) == 1
    assert not _events_of_type(execution=execution, event_type=EXECUTION_LIFECYCLE_EVENT_VALIDATED)


def test_manual_cancel_sets_actor_and_metadata(owner_membership, execution_with_assignee):
    canceled = cancel_action_plan_execution(
        execution_id=execution_with_assignee.id,
        actor=owner_membership,
    )
    canceled.refresh_from_db()
    events = _events_of_type(execution=canceled, event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED)
    assert len(events) == 1
    assert canceled.canceled_by_membership_id == owner_membership.id
    assert canceled.canceled_at == events[0].occurred_at
    assert events[0].actor_membership_id == owner_membership.id
    assert events[0].metadata_safe == {"cancel_origin": CANCEL_ORIGIN_MANUAL}


def test_promotion_sets_started_fields_and_is_idempotent(
    owner_membership,
    business_unit,
    staff_membership,
):
    start_at = timezone.now() - timezone.timedelta(minutes=5)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Promote audit",
        start_at=start_at,
        end_at=start_at + timezone.timedelta(hours=1),
        use_shared_chronology=True,
        tasks=[build_task_payload(task="Promote me", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    # Force scheduled so promotion path runs even if create landed as in_progress.
    ActionPlanExecution.objects.filter(pk=execution.id).update(
        status=EXECUTION_STATUS_SCHEDULED,
        start_at=start_at,
        started_at=None,
        started_by_membership=None,
    )
    ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_STARTED,
    ).delete()

    promoted = promote_due_scheduled_executions(
        establishment_id=owner_membership.establishment_id,
        execution_id=execution.id,
    )
    assert promoted == 1
    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_IN_PROGRESS
    started = _events_of_type(execution=execution, event_type=EXECUTION_LIFECYCLE_EVENT_STARTED)
    assert len(started) == 1
    assert started[0].actor_membership_id is None
    assert execution.started_by_membership_id is None
    assert execution.started_at == started[0].occurred_at
    assert execution.started_at != execution.start_at

    assert (
        promote_due_scheduled_executions(
            establishment_id=owner_membership.establishment_id,
            execution_id=execution.id,
        )
        == 0
    )
    assert (
        len(_events_of_type(execution=execution, event_type=EXECUTION_LIFECYCLE_EVENT_STARTED)) == 1
    )


def test_schedule_sync_cancel_and_reactivate_to_scheduled(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    from datetime import time as dt_time

    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=recurrence_days_for_visible_today(),
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **visible_schedule_window(),
    )
    execution = schedule.executions.filter(
        status__in=[EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS]
    ).first()
    assert execution is not None

    # Future schedule window so reactivation lands on scheduled.
    schedule.start_at = dt_time(23, 0)
    schedule.end_at = dt_time(23, 30)
    schedule.save(update_fields=["start_at", "end_at", "updated_at"])

    now = timezone.now()
    execution.status = EXECUTION_STATUS_CANCELED
    execution.cancel_origin = CANCEL_ORIGIN_SCHEDULE_SYNC
    execution.canceled_at = now
    execution.canceled_by_membership = None
    execution.start_at = now + timezone.timedelta(days=2)
    execution.end_at = execution.start_at + timezone.timedelta(hours=1)
    execution.visible_from = execution.start_at - timezone.timedelta(hours=1)
    execution.started_at = timezone.now()
    execution.started_by_membership = None
    execution.save(
        update_fields=[
            "status",
            "cancel_origin",
            "canceled_at",
            "canceled_by_membership",
            "start_at",
            "end_at",
            "visible_from",
            "started_at",
            "started_by_membership",
            "updated_at",
        ]
    )
    ActionPlanExecutionLifecycleEvent.objects.create(
        action_plan_execution=execution,
        establishment_id=execution.establishment_id,
        event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
        actor_membership=None,
        occurred_at=now,
        metadata_safe={"cancel_origin": CANCEL_ORIGIN_SCHEDULE_SYNC},
    )

    # Point occurrence at a future date so recomputed start stays scheduled.
    execution.occurrence_date = timezone.now().date() + timezone.timedelta(days=5)
    execution.save(update_fields=["occurrence_date", "updated_at"])

    reactivated_execution = reactivate_schedule_future_execution(
        execution=execution,
        schedule=schedule,
    )
    reactivated_execution.refresh_from_db()
    assert reactivated_execution.status == EXECUTION_STATUS_SCHEDULED
    reactivated = _events_of_type(
        execution=reactivated_execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_REACTIVATED,
    )
    assert len(reactivated) == 1
    assert reactivated[0].actor_membership_id is None
    assert reactivated[0].metadata_safe == {
        "reactivation_origin": CANCEL_ORIGIN_SCHEDULE_SYNC,
        "to_status": EXECUTION_STATUS_SCHEDULED,
    }
    assert reactivated_execution.reactivated_at == reactivated[0].occurred_at
    assert reactivated_execution.reactivated_by_membership_id is None
    assert reactivated_execution.reopened_at is None
    assert reactivated_execution.started_at is None
    assert reactivated_execution.started_by_membership_id is None
    assert (
        len(
            _events_of_type(
                execution=reactivated_execution,
                event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
            )
        )
        == 1
    )

    before = ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution=reactivated_execution,
    ).count()
    again = reactivate_schedule_future_execution(
        execution=reactivated_execution,
        schedule=schedule,
    )
    assert again.status == EXECUTION_STATUS_SCHEDULED
    assert (
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution=reactivated_execution,
        ).count()
        == before
    )


def test_schedule_sync_cancel_via_patch_emits_canceled_event(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=recurrence_days_for_visible_today(),
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **visible_schedule_window(),
    )
    future_execution = schedule.executions.filter(
        status__in=[EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS]
    ).first()
    assert future_execution is not None
    future_execution.status = EXECUTION_STATUS_SCHEDULED
    future_execution.start_at = timezone.now() + timezone.timedelta(days=2)
    future_execution.end_at = future_execution.start_at + timezone.timedelta(hours=1)
    future_execution.visible_from = future_execution.start_at - timezone.timedelta(hours=1)
    future_execution.save(
        update_fields=["status", "start_at", "end_at", "visible_from", "updated_at"],
    )
    occurrence_date = future_execution.occurrence_date
    excluded_day = next(
        day
        for weekday, day in enumerate(
            ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
        )
        if weekday != occurrence_date.weekday()
    )

    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        recurrence_days=[excluded_day],
    )
    future_execution.refresh_from_db()
    assert future_execution.status == EXECUTION_STATUS_CANCELED
    canceled_events = _events_of_type(
        execution=future_execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
    )
    assert len(canceled_events) == 1
    assert canceled_events[0].actor_membership_id is None
    assert canceled_events[0].metadata_safe == {
        "cancel_origin": CANCEL_ORIGIN_SCHEDULE_SYNC,
    }
    assert future_execution.canceled_at == canceled_events[0].occurred_at


def test_reactivate_directly_to_in_progress_without_started_event(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    from datetime import time as dt_time

    schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=recurrence_days_for_visible_today(),
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **visible_schedule_window(),
    )
    # Ensure recomputed occurrence start is always in the past at reactivation time.
    past_hour = (timezone.now() - timezone.timedelta(hours=2)).time().replace(
        second=0,
        microsecond=0,
    )
    end_hour = (timezone.now() - timezone.timedelta(hours=1)).time().replace(
        second=0,
        microsecond=0,
    )
    if end_hour <= past_hour:
        past_hour = dt_time(0, 0)
        end_hour = dt_time(1, 0)
    schedule.start_at = past_hour
    schedule.end_at = end_hour
    schedule.save(update_fields=["start_at", "end_at", "updated_at"])

    execution = schedule.executions.filter(
        status__in=[EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS]
    ).first()
    assert execution is not None

    now = timezone.now()
    execution.status = EXECUTION_STATUS_CANCELED
    execution.cancel_origin = CANCEL_ORIGIN_SCHEDULE_SYNC
    execution.canceled_at = now
    execution.canceled_by_membership = None
    # Guard-friendly future start_at; occurrence_date stays today so reactivation
    # recomputes a due window → in_progress.
    execution.start_at = now + timezone.timedelta(days=2)
    execution.end_at = execution.start_at + timezone.timedelta(hours=1)
    execution.visible_from = execution.start_at - timezone.timedelta(hours=1)
    execution.started_at = None
    execution.started_by_membership = None
    execution.save(
        update_fields=[
            "status",
            "cancel_origin",
            "canceled_at",
            "canceled_by_membership",
            "start_at",
            "end_at",
            "visible_from",
            "started_at",
            "started_by_membership",
            "updated_at",
        ]
    )
    ActionPlanExecutionLifecycleEvent.objects.create(
        action_plan_execution=execution,
        establishment_id=execution.establishment_id,
        event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
        actor_membership=None,
        occurred_at=now,
        metadata_safe={"cancel_origin": CANCEL_ORIGIN_SCHEDULE_SYNC},
    )

    reactivated = reactivate_schedule_future_execution(
        execution=execution,
        schedule=schedule,
    )
    reactivated.refresh_from_db()
    assert reactivated.status == EXECUTION_STATUS_IN_PROGRESS
    events = _events_of_type(
        execution=reactivated,
        event_type=EXECUTION_LIFECYCLE_EVENT_REACTIVATED,
    )
    assert len(events) == 1
    assert events[0].metadata_safe["to_status"] == EXECUTION_STATUS_IN_PROGRESS
    assert reactivated.reactivated_at == events[0].occurred_at
    assert not _events_of_type(
        execution=reactivated,
        event_type=EXECUTION_LIFECYCLE_EVENT_STARTED,
    )
    assert reactivated.started_at is None
    assert reactivated.reopened_at is None
