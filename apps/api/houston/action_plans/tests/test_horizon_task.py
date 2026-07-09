from __future__ import annotations

import logging

import pytest
from django.utils import timezone

from houston.action_plans.constants import SCHEDULE_STATUS_ACTIVE, SCHEDULE_STATUS_INACTIVE
from houston.action_plans.models import ActionPlanExecution, ActionPlanSchedule
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.services import deactivate_action_plan
from houston.action_plans.tasks import materialize_action_plan_schedules_horizon_task
from houston.action_plans.tests.helpers import (
    build_schedule_assignee_payload,
    create_catalog_action_plan,
    schedule_window_from_datetime,
)

pytestmark = pytest.mark.django_db


def test_horizon_task_materializes_recurring_occurrences(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    schedule = create_action_plan_schedule(
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
        **schedule_window_from_datetime(now, period_days=14),
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()

    created = materialize_action_plan_schedules_horizon_task.run()
    assert created > 0
    assert ActionPlanExecution.objects.filter(action_plan_schedule=schedule).count() == created


def test_horizon_task_is_idempotent(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    schedule = create_action_plan_schedule(
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
        **schedule_window_from_datetime(now, period_days=14),
    )
    ActionPlanExecution.objects.filter(action_plan_schedule=schedule).delete()

    materialize_action_plan_schedules_horizon_task.run()
    count_after_first = ActionPlanExecution.objects.filter(
        action_plan_schedule=schedule,
    ).count()
    materialize_action_plan_schedules_horizon_task.run()
    count_after_second = ActionPlanExecution.objects.filter(
        action_plan_schedule=schedule,
    ).count()

    assert count_after_first > 0
    assert count_after_second == count_after_first


def test_horizon_task_skips_invalid_schedule_and_materializes_valid_one(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
    caplog: pytest.LogCaptureFixture,
):
    now = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    window = schedule_window_from_datetime(now, period_days=14)
    assignees = [
        build_schedule_assignee_payload(
            membership=staff_membership,
            business_unit=business_unit,
        )
    ]

    valid_schedule = create_action_plan_schedule(
        action_plan=catalog_action_plan,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
        assignees=assignees,
        use_shared_chronology=True,
        **window,
    )
    invalid_catalog_plan = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    invalid_schedule = create_action_plan_schedule(
        action_plan=invalid_catalog_plan,
        actor=owner_membership,
        recurrence_days=["monday", "wednesday", "friday"],
        assignees=assignees,
        use_shared_chronology=True,
        **window,
    )
    deactivate_action_plan(action_plan=invalid_catalog_plan, actor=owner_membership)
    invalid_schedule.refresh_from_db()
    assert invalid_schedule.status == SCHEDULE_STATUS_INACTIVE
    ActionPlanSchedule.objects.filter(pk=invalid_schedule.pk).update(status=SCHEDULE_STATUS_ACTIVE)
    invalid_schedule.refresh_from_db()

    ActionPlanExecution.objects.filter(
        action_plan_schedule_id__in=[valid_schedule.id, invalid_schedule.id],
    ).delete()

    materialization_logger = "houston.action_plans.materialization"
    with caplog.at_level(logging.WARNING, logger=materialization_logger):
        created = materialize_action_plan_schedules_horizon_task.run(
            establishment_id=str(owner_membership.establishment_id),
        )

    assert isinstance(created, int)
    assert ActionPlanExecution.objects.filter(action_plan_schedule=valid_schedule).exists()

    skip_records = [
        record
        for record in caplog.records
        if record.getMessage() == "action_plan_schedule_materialization_skipped"
    ]
    assert skip_records
    assert any(
        getattr(record, "materialization_path", None) == "beat_horizon"
        and getattr(record, "schedule_id", None) == str(invalid_schedule.id)
        for record in skip_records
    )
