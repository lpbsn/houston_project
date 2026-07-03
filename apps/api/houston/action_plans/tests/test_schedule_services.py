from __future__ import annotations

from datetime import time

import pytest
from django.utils import timezone

from houston.action_plans.constants import EXECUTION_STATUS_CANCELED, EXECUTION_STATUS_DONE
from houston.action_plans.exceptions import ActionPlanConflictError, ActionPlanValidationError
from houston.action_plans.schedule_services import (
    create_action_plan_schedule,
    deactivate_action_plan_schedule,
    update_action_plan_schedule,
)
from houston.action_plans.tests.conftest import (
    build_schedule_assignee_payload,
    schedule_window_from_datetime,
)

pytestmark = pytest.mark.django_db


def _create_schedule(owner_membership, catalog_action_plan, staff_membership, business_unit):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now)
    return create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
        assignees=[
            build_schedule_assignee_payload(
                membership=staff_membership,
                business_unit=business_unit,
            )
        ],
        use_shared_chronology=True,
        **window,
    )


def test_update_cancels_future_execution_outside_recurrence(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    future_execution = schedule.executions.filter(status="in_progress").first()
    assert future_execution is not None
    future_execution.start_at = timezone.now() + timezone.timedelta(days=2)
    future_execution.end_at = future_execution.start_at + timezone.timedelta(hours=1)
    future_execution.visible_from = future_execution.start_at - timezone.timedelta(hours=1)
    future_execution.save(
        update_fields=["start_at", "end_at", "visible_from", "updated_at"],
    )
    occurrence_date = future_execution.occurrence_date

    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        recurrence_days=["tuesday"],
    )

    future_execution.refresh_from_db()
    assert future_execution.status == EXECUTION_STATUS_CANCELED

    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
    )
    still_valid = schedule.executions.filter(
        occurrence_date=occurrence_date,
        status=EXECUTION_STATUS_CANCELED,
    ).exists()
    assert still_valid


def test_update_syncs_future_window_without_changing_occurrence_date(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    future_execution = (
        schedule.executions.filter(status="in_progress", start_at__gt=timezone.now())
        .order_by("occurrence_date")
        .first()
    )
    if future_execution is None:
        future_execution = schedule.executions.filter(status="in_progress").first()
        future_execution.start_at = timezone.now() + timezone.timedelta(days=2)
        future_execution.end_at = future_execution.start_at + timezone.timedelta(hours=1)
        future_execution.visible_from = future_execution.start_at - timezone.timedelta(hours=1)
        future_execution.save(
            update_fields=["start_at", "end_at", "visible_from", "updated_at"],
        )

    original_occurrence_date = future_execution.occurrence_date
    update_action_plan_schedule(
        schedule=schedule,
        actor=owner_membership,
        start_at=time(10, 0),
        end_at=time(11, 0),
    )

    future_execution.refresh_from_db()
    assert future_execution.occurrence_date == original_occurrence_date
    assert future_execution.start_at.hour == 10


def test_update_use_shared_chronology_forbidden_after_materialization(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    assert schedule.executions.exists()

    with pytest.raises(ActionPlanValidationError):
        update_action_plan_schedule(
            schedule=schedule,
            actor=owner_membership,
            use_shared_chronology=False,
        )


def test_deactivate_blocks_active_started_execution(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    active = schedule.executions.filter(status="in_progress").first()
    active.start_at = timezone.now() - timezone.timedelta(minutes=5)
    active.end_at = timezone.now() + timezone.timedelta(hours=1)
    active.visible_from = active.start_at - timezone.timedelta(hours=1)
    active.save(update_fields=["start_at", "end_at", "visible_from", "updated_at"])

    with pytest.raises(ActionPlanConflictError) as exc_info:
        deactivate_action_plan_schedule(schedule=schedule, actor=owner_membership)
    assert exc_info.value.active_execution_id == active.id


def test_deactivate_cancels_future_preserves_terminal(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    done = schedule.executions.filter(status="in_progress").first()
    done.status = EXECUTION_STATUS_DONE
    done.save(update_fields=["status", "updated_at"])

    future = schedule.executions.filter(status="in_progress").exclude(id=done.id).first()
    if future is not None:
        future.start_at = timezone.now() + timezone.timedelta(days=2)
        future.end_at = future.start_at + timezone.timedelta(hours=1)
        future.visible_from = future.start_at - timezone.timedelta(hours=1)
        future.save(update_fields=["start_at", "end_at", "visible_from", "updated_at"])

    deactivate_action_plan_schedule(schedule=schedule, actor=owner_membership)

    done.refresh_from_db()
    assert done.status == EXECUTION_STATUS_DONE
    if future is not None:
        future.refresh_from_db()
        assert future.status == EXECUTION_STATUS_CANCELED
