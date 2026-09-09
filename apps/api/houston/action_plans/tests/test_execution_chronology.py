from __future__ import annotations

import importlib
from datetime import timedelta

import pytest
from django.apps import apps as django_apps
from django.utils import timezone

from houston.action_plans.exceptions import ActionPlanValidationError
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import (
    create_action_plan_with_execution,
    create_execution_from_action_plan,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload

pytestmark = pytest.mark.django_db

_backfill_mod = importlib.import_module(
    "houston.action_plans.migrations.0016_backfill_execution_start_at_when_end_at"
)
backfill_execution_start_at_when_end_at = (
    _backfill_mod.backfill_execution_start_at_when_end_at
)


def test_create_rejects_end_at_without_start_at(owner_membership, business_unit):
    with pytest.raises(
        ActionPlanValidationError,
        match="End datetime requires a start datetime",
    ):
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="End without start",
            tasks=[build_task_payload(task="Task", business_unit=business_unit)],
            assignees=[
                build_assignee_payload(
                    membership=owner_membership,
                    business_unit=business_unit,
                )
            ],
            use_shared_chronology=True,
            start_at=None,
            end_at=timezone.now() + timedelta(hours=2),
        )


def test_create_allows_undated_execution(owner_membership, business_unit):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Undated",
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit)
        ],
        use_shared_chronology=True,
        start_at=None,
        end_at=None,
    )
    assert execution.start_at is None
    assert execution.end_at is None


def test_create_allows_start_and_end(owner_membership, business_unit):
    start_at = timezone.now() + timedelta(hours=1)
    end_at = start_at + timedelta(hours=1)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Windowed",
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit)
        ],
        use_shared_chronology=True,
        start_at=start_at,
        end_at=end_at,
    )
    assert execution.start_at == start_at
    assert execution.end_at == end_at


def test_catalog_use_rejects_end_at_without_start_at(
    owner_membership,
    catalog_action_plan,
):
    with pytest.raises(
        ActionPlanValidationError,
        match="End datetime requires a start datetime",
    ):
        create_execution_from_action_plan(
            action_plan_id=catalog_action_plan.id,
            actor=owner_membership,
            assignees=[],
            use_shared_chronology=True,
            start_at=None,
            end_at=timezone.now() + timedelta(hours=2),
        )


def test_backfill_sets_start_at_from_created_at_when_before_end_at(
    action_plan,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    created_at = now - timedelta(days=2)
    end_at = now + timedelta(hours=1)
    execution = ActionPlanExecution.objects.create(
        action_plan=action_plan,
        establishment=action_plan.establishment,
        created_by=owner_membership,
        title=action_plan.title,
        description=action_plan.description,
        pilot_business_unit=business_unit,
        requires_validation=False,
        last_activity_at=now,
        use_shared_chronology=True,
        start_at=None,
        end_at=end_at,
    )
    ActionPlanExecution.objects.filter(pk=execution.pk).update(created_at=created_at)

    backfill_execution_start_at_when_end_at(django_apps, None)

    execution.refresh_from_db()
    assert execution.start_at == execution.created_at
    assert execution.end_at == end_at


def test_backfill_leaves_inverted_created_at_unplanned(
    action_plan,
    owner_membership,
    business_unit,
):
    now = timezone.now()
    created_at = now
    end_at = now - timedelta(days=1)
    execution = ActionPlanExecution.objects.create(
        action_plan=action_plan,
        establishment=action_plan.establishment,
        created_by=owner_membership,
        title=action_plan.title,
        description=action_plan.description,
        pilot_business_unit=business_unit,
        requires_validation=False,
        last_activity_at=now,
        use_shared_chronology=True,
        start_at=None,
        end_at=end_at,
    )
    ActionPlanExecution.objects.filter(pk=execution.pk).update(created_at=created_at)

    backfill_execution_start_at_when_end_at(django_apps, None)

    execution.refresh_from_db()
    assert execution.start_at is None
    assert execution.end_at == end_at
