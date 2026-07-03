from __future__ import annotations

import pytest
from django.utils import timezone

from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.tasks import materialize_action_plan_schedules_horizon_task
from houston.action_plans.tests.conftest import (
    build_schedule_assignee_payload,
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
