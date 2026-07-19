from __future__ import annotations

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    CATALOG_STATUS_ACTIVE,
    CATALOG_STATUS_INACTIVE,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
    SCHEDULE_STATUS_ACTIVE,
    SCHEDULE_STATUS_INACTIVE,
)
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.services import activate_action_plan, deactivate_action_plan
from houston.action_plans.tests.helpers import (
    build_schedule_assignee_payload,
    create_catalog_action_plan,
    recurrence_days_for_visible_today,
    visible_schedule_window,
)

pytestmark = pytest.mark.django_db


def _create_schedule(owner_membership, catalog_action_plan, staff_membership, business_unit):
    return create_action_plan_schedule(
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


def test_deactivate_catalog_cascades_all_active_schedules(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    schedule_one = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    schedule_two = _create_schedule(
        owner_membership,
        catalog_action_plan,
        staff_membership,
        business_unit,
    )
    future_execution = schedule_one.executions.filter(
        status__in=[EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS],
    ).first()
    if future_execution is not None:
        future_execution.start_at = timezone.now() + timezone.timedelta(days=2)
        future_execution.end_at = future_execution.start_at + timezone.timedelta(hours=1)
        future_execution.visible_from = future_execution.start_at - timezone.timedelta(hours=1)
        future_execution.save(
            update_fields=["start_at", "end_at", "visible_from", "updated_at"],
        )

    deactivate_action_plan(action_plan=catalog_action_plan, actor=owner_membership)

    catalog_action_plan.refresh_from_db()
    schedule_one.refresh_from_db()
    schedule_two.refresh_from_db()
    assert catalog_action_plan.catalog_status == CATALOG_STATUS_INACTIVE
    assert schedule_one.status == SCHEDULE_STATUS_INACTIVE
    assert schedule_two.status == SCHEDULE_STATUS_INACTIVE
    if future_execution is not None:
        future_execution.refresh_from_db()
        assert future_execution.status == EXECUTION_STATUS_CANCELED


def test_deactivate_catalog_with_active_started_execution(
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
    active_execution = schedule.executions.filter(
        status__in=[EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS],
    ).first()
    assert active_execution is not None
    active_execution.status = EXECUTION_STATUS_IN_PROGRESS
    active_execution.start_at = timezone.now() - timezone.timedelta(minutes=5)
    active_execution.end_at = timezone.now() + timezone.timedelta(hours=1)
    active_execution.visible_from = active_execution.start_at - timezone.timedelta(hours=1)
    active_execution.save(
        update_fields=["status", "start_at", "end_at", "visible_from", "updated_at"],
    )

    deactivate_action_plan(action_plan=catalog_action_plan, actor=owner_membership)

    catalog_action_plan.refresh_from_db()
    schedule.refresh_from_db()
    active_execution.refresh_from_db()
    assert catalog_action_plan.catalog_status == CATALOG_STATUS_INACTIVE
    assert schedule.status == SCHEDULE_STATUS_INACTIVE
    assert active_execution.status == EXECUTION_STATUS_IN_PROGRESS


def test_deactivate_catalog_preserves_overdue_scheduled_execution(
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
    overdue = schedule.executions.filter(
        status__in=[EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS],
    ).first()
    assert overdue is not None
    overdue.status = EXECUTION_STATUS_SCHEDULED
    overdue.start_at = timezone.now() - timezone.timedelta(minutes=5)
    overdue.end_at = timezone.now() + timezone.timedelta(hours=1)
    overdue.visible_from = overdue.start_at - timezone.timedelta(hours=1)
    overdue.save(
        update_fields=["status", "start_at", "end_at", "visible_from", "updated_at"],
    )

    deactivate_action_plan(action_plan=catalog_action_plan, actor=owner_membership)

    catalog_action_plan.refresh_from_db()
    schedule.refresh_from_db()
    overdue.refresh_from_db()
    assert catalog_action_plan.catalog_status == CATALOG_STATUS_INACTIVE
    assert schedule.status == SCHEDULE_STATUS_INACTIVE
    assert overdue.status == EXECUTION_STATUS_SCHEDULED


def test_deactivate_catalog_preserves_terminal_executions(
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
    done_execution = schedule.executions.filter(
        status__in=[EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS],
    ).first()
    assert done_execution is not None
    done_execution.status = EXECUTION_STATUS_DONE
    done_execution.save(update_fields=["status", "updated_at"])

    pending_validation_execution = schedule.executions.filter(
        status=EXECUTION_STATUS_IN_PROGRESS,
    ).first()
    if (
        pending_validation_execution is not None
        and pending_validation_execution.id != done_execution.id
    ):
        pending_validation_execution.status = EXECUTION_STATUS_PENDING_VALIDATION
        pending_validation_execution.save(update_fields=["status", "updated_at"])

    deactivate_action_plan(action_plan=catalog_action_plan, actor=owner_membership)

    done_execution.refresh_from_db()
    assert done_execution.status == EXECUTION_STATUS_DONE
    if (
        pending_validation_execution is not None
        and pending_validation_execution.id != done_execution.id
    ):
        pending_validation_execution.refresh_from_db()
        assert pending_validation_execution.status == EXECUTION_STATUS_PENDING_VALIDATION


def test_activate_catalog_does_not_reactivate_schedules(
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

    deactivate_action_plan(action_plan=catalog_action_plan, actor=owner_membership)
    activate_action_plan(action_plan=catalog_action_plan, actor=owner_membership)

    catalog_action_plan.refresh_from_db()
    schedule.refresh_from_db()
    assert catalog_action_plan.catalog_status == CATALOG_STATUS_ACTIVE
    assert schedule.status == SCHEDULE_STATUS_INACTIVE


def test_deactivate_catalog_cascades_across_multiple_catalog_plans(
    owner_membership,
    staff_membership,
    business_unit,
):
    first_plan = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    second_plan = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    first_schedule = _create_schedule(
        owner_membership,
        first_plan,
        staff_membership,
        business_unit,
    )
    second_schedule = _create_schedule(
        owner_membership,
        second_plan,
        staff_membership,
        business_unit,
    )

    deactivate_action_plan(action_plan=first_plan, actor=owner_membership)

    first_plan.refresh_from_db()
    second_plan.refresh_from_db()
    first_schedule.refresh_from_db()
    second_schedule.refresh_from_db()
    assert first_plan.catalog_status == CATALOG_STATUS_INACTIVE
    assert first_schedule.status == SCHEDULE_STATUS_INACTIVE
    assert second_plan.catalog_status == CATALOG_STATUS_ACTIVE
    assert second_schedule.status == SCHEDULE_STATUS_ACTIVE
