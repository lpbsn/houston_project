from __future__ import annotations

from datetime import time

import pytest
from django.utils import timezone

from houston.action_plans.constants import CATALOG_STATUS_ACTIVE
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionTeam,
    ActionPlanSchedule,
    ActionPlanTask,
)
from houston.action_plans.services import create_action_plan_with_execution
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
    create_minimal_v3_signal,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def establishment():
    return create_establishment(name="Action Plan Hotel", timezone="UTC")


@pytest.fixture
def business_unit(establishment):
    return create_business_unit(establishment=establishment, key="restaurant")


@pytest.fixture
def maintenance_business_unit(establishment):
    return create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
    )


@pytest.fixture
def owner_membership(establishment):
    return create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )


@pytest.fixture
def staff_membership(establishment, business_unit):
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    return membership


@pytest.fixture
def manager_membership(establishment, business_unit):
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    return membership


@pytest.fixture
def out_of_scope_staff(establishment, maintenance_business_unit):
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=maintenance_business_unit,
    )
    return membership


@pytest.fixture
def signal(owner_membership):
    return create_minimal_v3_signal(
        owner_membership,
        title="Leaky pipe",
        status=Signal.Status.OPEN,
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
def catalog_action_plan(owner_membership, business_unit):
    plan = ActionPlan.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        pilot_business_unit=business_unit,
        title="Catalog plan",
        description="Reusable plan",
        is_reusable=True,
        catalog_status=CATALOG_STATUS_ACTIVE,
    )
    ActionPlanTask.objects.create(
        action_plan=plan,
        business_unit=business_unit,
        task="Check inventory",
        position=1,
    )
    return plan


@pytest.fixture
def inactive_catalog_action_plan(owner_membership, business_unit):
    return ActionPlan.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        pilot_business_unit=business_unit,
        title="Inactive catalog plan",
        is_reusable=True,
        catalog_status="inactive",
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


def build_assignee_payload(*, membership, business_unit) -> dict:
    return {
        "membership_id": membership.id,
        "business_unit_id": business_unit.id,
    }


def build_task_payload(*, task: str, business_unit, position: int = 1) -> dict:
    return {
        "task": task,
        "business_unit_id": business_unit.id,
        "position": position,
    }


@pytest.fixture
def execution_with_assignee(owner_membership, business_unit, staff_membership):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Assigned plan",
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    return execution
