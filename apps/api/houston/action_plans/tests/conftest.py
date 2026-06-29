from __future__ import annotations

from datetime import time

import pytest
from django.utils import timezone

from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
    ActionPlanTask,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db


@pytest.fixture
def establishment():
    return create_establishment(name="Action Plan Hotel", timezone="UTC")


@pytest.fixture
def business_unit(establishment):
    return create_business_unit(establishment=establishment, key="restaurant")


@pytest.fixture
def owner_membership(establishment):
    return create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )


@pytest.fixture
def staff_membership(establishment, business_unit):
    return create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )


@pytest.fixture
def action_plan(owner_membership, business_unit):
    return ActionPlan.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        pilot_business_unit=business_unit,
        title="Daily opening",
        description="Open the restaurant",
    )


@pytest.fixture
def action_plan_schedule(action_plan, owner_membership):
    today = timezone.now().date()
    return ActionPlanSchedule.objects.create(
        action_plan=action_plan,
        establishment=action_plan.establishment,
        created_by=owner_membership,
        start_date=today,
        end_date=today,
        start_at=time(8, 0),
        end_at=time(10, 0),
    )


@pytest.fixture
def action_plan_execution(action_plan, owner_membership, business_unit):
    now = timezone.now()
    return ActionPlanExecution.objects.create(
        action_plan=action_plan,
        establishment=action_plan.establishment,
        created_by=owner_membership,
        title=action_plan.title,
        description=action_plan.description,
        pilot_business_unit=business_unit,
        requires_validation=action_plan.requires_validation,
        last_activity_at=now,
    )


@pytest.fixture
def pilot_execution_team(action_plan_execution, business_unit):
    return ActionPlanExecutionTeam.objects.create(
        action_plan_execution=action_plan_execution,
        business_unit=business_unit,
        is_pilot=True,
    )
