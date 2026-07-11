from __future__ import annotations

from unittest.mock import patch

import pytest

from houston.action_plans.constants import CATALOG_STATUS_ACTIVE
from houston.action_plans.models import ActionPlan, ActionPlanTask
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.services import create_execution_from_action_plan
from houston.action_plans.tests.helpers import (
    recurrence_days_for_visible_today,
    visible_schedule_window,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def _create_catalog_plan(*, owner_membership, business_unit) -> ActionPlan:
    plan = ActionPlan.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        pilot_business_unit=business_unit,
        title="Catalog plan",
        description="Reusable",
        is_reusable=True,
        catalog_status=CATALOG_STATUS_ACTIVE,
    )
    ActionPlanTask.objects.create(
        action_plan=plan,
        business_unit=business_unit,
        task="Check stock",
        position=1,
    )
    return plan


@patch("django.db.transaction.on_commit")
def test_emit_side_effects_false_registers_no_on_commit_callbacks_for_use(mock_on_commit):
    establishment = create_establishment(name="Emit Side Effects Hotel", timezone="UTC")
    business_unit = create_business_unit(establishment=establishment, key="bar")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    staff = create_membership(establishment=establishment, role=EstablishmentMembership.Role.STAFF)
    create_membership_with_business_unit_scope(membership=staff, business_unit=business_unit)
    plan = _create_catalog_plan(owner_membership=owner, business_unit=business_unit)

    create_execution_from_action_plan(
        action_plan_id=plan.id,
        actor=owner,
        assignees=[
            {
                "membership_id": staff.id,
                "business_unit_id": business_unit.id,
            }
        ],
        emit_side_effects=False,
    )

    mock_on_commit.assert_not_called()


@patch("django.db.transaction.on_commit")
def test_emit_side_effects_false_registers_no_on_commit_callbacks_for_schedule(mock_on_commit):
    establishment = create_establishment(name="Emit Side Effects Schedule Hotel", timezone="UTC")
    business_unit = create_business_unit(establishment=establishment, key="bar")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    staff = create_membership(establishment=establishment, role=EstablishmentMembership.Role.STAFF)
    create_membership_with_business_unit_scope(membership=staff, business_unit=business_unit)
    plan = _create_catalog_plan(owner_membership=owner, business_unit=business_unit)
    window = visible_schedule_window()

    create_action_plan_schedule(
        action_plan=plan,
        actor=owner,
        start_date=window["start_date"],
        end_date=window["end_date"],
        start_at=window["start_at"],
        end_at=window["end_at"],
        recurrence_days=recurrence_days_for_visible_today(),
        assignees=[
            {
                "membership_id": staff.id,
                "business_unit_id": business_unit.id,
            }
        ],
        use_shared_chronology=False,
        emit_side_effects=False,
    )

    mock_on_commit.assert_not_called()
