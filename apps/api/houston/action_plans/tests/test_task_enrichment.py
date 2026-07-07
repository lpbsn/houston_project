from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.action_plans.models import ActionPlanAssignee, ActionPlanExecutionTask, ActionPlanTask
from houston.action_plans.services import (
    create_action_plan_with_execution,
    create_execution_from_action_plan,
    replace_action_plan_tasks,
)
from houston.action_plans.tests.helpers import (
    action_plan_url,
    api_task_payload,
    build_task_payload,
    create_catalog_action_plan,
)
from houston.testing.auth import auth_headers, login

pytestmark = pytest.mark.django_db


def test_execution_task_snapshot_enriched_fields(
    action_plan,
    action_plan_execution,
    pilot_execution_team,
    business_unit,
    staff_membership,
):
    deadline = timezone.now() + timedelta(days=1)
    template_task = ActionPlanTask.objects.create(
        action_plan=action_plan,
        business_unit=business_unit,
        task="Inspect fridge",
        description="Check all shelves",
        deadline_at=deadline,
        assigned_membership=staff_membership,
        position=1,
    )
    task_execution = ActionPlanExecutionTask.objects.create(
        action_plan_execution=action_plan_execution,
        execution_team=pilot_execution_team,
        action_plan_task=template_task,
        task=template_task.task,
        description=template_task.description,
        deadline_at=template_task.deadline_at,
        assigned_membership=template_task.assigned_membership,
        assigned_display_name="Staff User",
        position=template_task.position,
    )
    assert task_execution.description == "Check all shelves"
    assert task_execution.deadline_at == deadline
    assert task_execution.assigned_membership_id == staff_membership.id
    assert task_execution.assigned_display_name == "Staff User"


def test_create_execution_merges_task_assignee_into_plan_assignees(
    owner_membership,
    business_unit,
    staff_membership,
    manager_membership,
):
    deadline = timezone.now() + timedelta(days=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Merge assignee plan",
        tasks=[
            build_task_payload(
                task="Task with assignee",
                business_unit=business_unit,
                assigned_membership=staff_membership,
                description="Do it",
                deadline_at=deadline,
            )
        ],
        assignees=[],
        use_shared_chronology=True,
        start_at=timezone.now(),
        end_at=timezone.now() + timedelta(hours=2),
        visible_from=timezone.now() - timedelta(hours=1),
    )

    assignees = ActionPlanAssignee.objects.filter(action_plan_execution=execution)
    assert assignees.count() == 1
    assert assignees.get().membership_id == staff_membership.id

    task_execution = ActionPlanExecutionTask.objects.get(action_plan_execution=execution)
    assert task_execution.description == "Do it"
    assert task_execution.deadline_at == deadline
    assert task_execution.assigned_membership_id == staff_membership.id
    assert task_execution.assigned_display_name


def test_staff_use_does_not_merge_task_assignee_into_plan_assignees(
    owner_membership,
    staff_membership,
    business_unit,
    manager_membership,
):
    plan = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    ActionPlanTask.objects.filter(action_plan=plan).delete()
    ActionPlanTask.objects.create(
        action_plan=plan,
        business_unit=business_unit,
        task="Staff-visible task",
        assigned_membership=manager_membership,
        position=1,
    )

    execution = create_execution_from_action_plan(
        action_plan_id=plan.id,
        actor=staff_membership,
        assignees=[],
    )

    assignees = ActionPlanAssignee.objects.filter(action_plan_execution=execution)
    assert assignees.count() == 1
    assert assignees.get().membership_id == staff_membership.id

    task_execution = ActionPlanExecutionTask.objects.get(action_plan_execution=execution)
    assert task_execution.assigned_membership_id == manager_membership.id


def test_use_catalog_plan_merges_task_assignee(
    owner_membership,
    business_unit,
    staff_membership,
):
    plan = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    ActionPlanTask.objects.filter(action_plan=plan).delete()
    ActionPlanTask.objects.create(
        action_plan=plan,
        business_unit=business_unit,
        task="Catalog task",
        assigned_membership=staff_membership,
        position=1,
    )

    execution = create_execution_from_action_plan(
        action_plan_id=plan.id,
        actor=owner_membership,
        assignees=[],
    )

    assert ActionPlanAssignee.objects.filter(action_plan_execution=execution).count() == 1
    assert (
        ActionPlanAssignee.objects.get(action_plan_execution=execution).membership_id
        == staff_membership.id
    )


def test_replace_action_plan_tasks(owner_membership, business_unit, staff_membership):
    plan = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    deadline = timezone.now() + timedelta(days=3)

    replace_action_plan_tasks(
        action_plan=plan,
        actor=owner_membership,
        tasks=[
            build_task_payload(
                task="Updated task",
                business_unit=business_unit,
                description="Updated description",
                deadline_at=deadline,
                assigned_membership=staff_membership,
            )
        ],
    )

    task = ActionPlanTask.objects.get(action_plan=plan)
    assert task.task == "Updated task"
    assert task.description == "Updated description"
    assert task.deadline_at == deadline
    assert task.assigned_membership_id == staff_membership.id


def test_patch_catalog_plan_tasks_via_api(
    api_client, owner_membership, business_unit, staff_membership
):
    plan = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    deadline = timezone.now() + timedelta(days=1)
    token = login(api_client, user=owner_membership.user)

    response = api_client.patch(
        action_plan_url(owner_membership.establishment_id, plan.id),
        {
            "tasks": [
                api_task_payload(
                    task="Patched task",
                    business_unit=business_unit,
                    description="Patched description",
                    deadline_at=deadline,
                    assigned_membership=staff_membership,
                )
            ]
        },
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 200
    task_payload = response.json()["tasks"][0]
    assert task_payload["task"] == "Patched task"
    assert task_payload["description"] == "Patched description"
    assert task_payload["assigned_membership_id"] == str(staff_membership.id)
    assert task_payload["assigned_display_name"]
