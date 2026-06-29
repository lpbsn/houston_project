from __future__ import annotations

from datetime import time

import pytest
from django.db import IntegrityError
from django.utils import timezone

from houston.action_plans.constants import CATALOG_STATUS_ACTIVE
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
    ActionPlanTask,
)

pytestmark = pytest.mark.django_db


def test_action_plan_defaults(owner_membership, business_unit):
    plan = ActionPlan.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        pilot_business_unit=business_unit,
        title="One-shot plan",
    )
    assert plan.is_reusable is False
    assert plan.catalog_status is None
    assert plan.requires_validation is True


def test_action_plan_catalog_status_shape_rejects_active_when_not_reusable(
    owner_membership,
    business_unit,
):
    with pytest.raises(IntegrityError):
        ActionPlan.objects.create(
            establishment=owner_membership.establishment,
            created_by=owner_membership,
            pilot_business_unit=business_unit,
            title="Invalid catalog",
            is_reusable=False,
            catalog_status=CATALOG_STATUS_ACTIVE,
        )


def test_action_plan_catalog_status_shape_rejects_null_when_reusable(
    owner_membership,
    business_unit,
):
    with pytest.raises(IntegrityError):
        ActionPlan.objects.create(
            establishment=owner_membership.establishment,
            created_by=owner_membership,
            pilot_business_unit=business_unit,
            title="Invalid catalog",
            is_reusable=True,
            catalog_status=None,
        )


def test_action_plan_requires_pilot_business_unit(owner_membership):
    with pytest.raises(IntegrityError):
        ActionPlan.objects.create(
            establishment=owner_membership.establishment,
            created_by=owner_membership,
            pilot_business_unit=None,
            title="Missing pilot",
        )


def test_action_plan_task_position_rejects_zero(action_plan, business_unit):
    with pytest.raises(IntegrityError):
        ActionPlanTask.objects.create(
            action_plan=action_plan,
            business_unit=business_unit,
            task="Out of bounds low",
            position=0,
        )


def test_action_plan_task_position_rejects_eleven(action_plan, business_unit):
    with pytest.raises(IntegrityError):
        ActionPlanTask.objects.create(
            action_plan=action_plan,
            business_unit=business_unit,
            task="Out of bounds high",
            position=11,
        )


def test_action_plan_task_unique_position(action_plan, business_unit):
    ActionPlanTask.objects.create(
        action_plan=action_plan,
        business_unit=business_unit,
        task="First",
        position=1,
    )
    with pytest.raises(IntegrityError):
        ActionPlanTask.objects.create(
            action_plan=action_plan,
            business_unit=business_unit,
            task="Duplicate",
            position=1,
        )


def test_action_plan_schedule_time_constraints(
    action_plan,
    owner_membership,
):
    today = timezone.now().date()
    with pytest.raises(IntegrityError):
        ActionPlanSchedule.objects.create(
            action_plan=action_plan,
            establishment=action_plan.establishment,
            created_by=owner_membership,
            start_date=today,
            end_date=today,
            start_at=time(10, 0),
            end_at=time(9, 0),
        )


def test_action_plan_execution_defaults_in_progress(
    action_plan,
    owner_membership,
    business_unit,
):
    execution = ActionPlanExecution.objects.create(
        action_plan=action_plan,
        establishment=action_plan.establishment,
        created_by=owner_membership,
        title=action_plan.title,
        pilot_business_unit=business_unit,
        last_activity_at=timezone.now(),
    )
    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS


def test_action_plan_execution_team_one_pilot(
    action_plan_execution,
    business_unit,
    establishment,
):
    ActionPlanExecutionTeam.objects.create(
        action_plan_execution=action_plan_execution,
        business_unit=business_unit,
        is_pilot=True,
    )
    maintenance = business_unit.__class__.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        source=business_unit.Source.MANUAL,
        active=True,
    )
    with pytest.raises(IntegrityError):
        ActionPlanExecutionTeam.objects.create(
            action_plan_execution=action_plan_execution,
            business_unit=maintenance,
            is_pilot=True,
        )


def test_action_plan_assignee_unique_per_execution(
    action_plan_execution,
    pilot_execution_team,
    staff_membership,
):
    ActionPlanAssignee.objects.create(
        action_plan_execution=action_plan_execution,
        execution_team=pilot_execution_team,
        membership=staff_membership,
    )
    with pytest.raises(IntegrityError):
        ActionPlanAssignee.objects.create(
            action_plan_execution=action_plan_execution,
            execution_team=pilot_execution_team,
            membership=staff_membership,
        )


def test_schedule_assignee_unique_per_schedule(
    action_plan_schedule,
    staff_membership,
    business_unit,
):
    ActionPlanScheduleAssignee.objects.create(
        action_plan_schedule=action_plan_schedule,
        membership=staff_membership,
        business_unit=business_unit,
    )
    with pytest.raises(IntegrityError):
        ActionPlanScheduleAssignee.objects.create(
            action_plan_schedule=action_plan_schedule,
            membership=staff_membership,
            business_unit=business_unit,
        )


def test_schedule_assignee_time_constraints(
    action_plan_schedule,
    staff_membership,
    business_unit,
):
    with pytest.raises(IntegrityError):
        ActionPlanScheduleAssignee.objects.create(
            action_plan_schedule=action_plan_schedule,
            membership=staff_membership,
            business_unit=business_unit,
            start_at=time(10, 0),
            end_at=time(9, 0),
        )


def test_execution_task_snapshot_fields(
    action_plan,
    action_plan_execution,
    pilot_execution_team,
    business_unit,
):
    template_task = ActionPlanTask.objects.create(
        action_plan=action_plan,
        business_unit=business_unit,
        task="Inspect fridge",
        position=1,
    )
    task_execution = ActionPlanExecutionTask.objects.create(
        action_plan_execution=action_plan_execution,
        execution_team=pilot_execution_team,
        action_plan_task=template_task,
        task=template_task.task,
        position=template_task.position,
    )
    assert task_execution.task == "Inspect fridge"
    assert task_execution.position == 1
    assert task_execution.status == ActionPlanExecutionTask.Status.PENDING
