from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.action_plans.exceptions import (
    ActionPlanPermissionError,
    ActionPlanStaleExecutionError,
    ActionPlanStateError,
    ActionPlanValidationError,
)
from houston.action_plans.execution_update import update_action_plan_execution
from houston.action_plans.models import ActionPlanAssignee, ActionPlanExecutionTask
from houston.action_plans.permissions import can_update_action_plan_execution_content
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def _scoped_membership(*, establishment, role, business_unit):
    membership = create_membership(establishment=establishment, role=role)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    return membership


def _create_in_progress_execution(*, owner, pilot_bu, assignees=None, tasks=None, **kwargs):
    _plan, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=pilot_bu.id,
        title=kwargs.get("title", "Execution"),
        description=kwargs.get("description", ""),
        requires_validation=kwargs.get("requires_validation", False),
        tasks=tasks
        or [build_task_payload(task="Task one", business_unit=pilot_bu)],
        assignees=assignees
        or [build_assignee_payload(membership=owner, business_unit=pilot_bu)],
        use_shared_chronology=kwargs.get("use_shared_chronology", True),
        start_at=kwargs.get("start_at", timezone.now() - timedelta(hours=1)),
        end_at=kwargs.get("end_at"),
    )
    return execution


def test_can_update_hint_roles():
    establishment = create_establishment()
    pilot = create_business_unit(establishment=establishment, key="pilot")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    manager = _scoped_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        business_unit=pilot,
    )
    staff = _scoped_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        business_unit=pilot,
    )
    execution = _create_in_progress_execution(owner=owner, pilot_bu=pilot)
    assert can_update_action_plan_execution_content(owner, execution) is True
    assert can_update_action_plan_execution_content(manager, execution) is True
    assert can_update_action_plan_execution_content(staff, execution) is False

    staff_execution = _create_in_progress_execution(
        owner=staff,
        pilot_bu=pilot,
        assignees=[build_assignee_payload(membership=staff, business_unit=pilot)],
        requires_validation=False,
    )
    assert can_update_action_plan_execution_content(staff, staff_execution) is True


def test_update_title_and_reject_stale():
    establishment = create_establishment()
    pilot = create_business_unit(establishment=establishment, key="pilot")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    execution = _create_in_progress_execution(owner=owner, pilot_bu=pilot)
    updated = update_action_plan_execution(
        execution_id=execution.id,
        actor=owner,
        expected_updated_at=execution.updated_at,
        title="Updated title",
    )
    assert updated.title == "Updated title"
    with pytest.raises(ActionPlanStaleExecutionError):
        update_action_plan_execution(
            execution_id=execution.id,
            actor=owner,
            expected_updated_at=execution.updated_at,
            title="Again",
        )


def test_update_rejects_non_in_progress():
    establishment = create_establishment()
    pilot = create_business_unit(establishment=establishment, key="pilot")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    execution = _create_in_progress_execution(owner=owner, pilot_bu=pilot)
    execution.status = execution.Status.DONE
    execution.save(update_fields=["status", "updated_at"])
    with pytest.raises(ActionPlanStateError):
        update_action_plan_execution(
            execution_id=execution.id,
            actor=owner,
            expected_updated_at=execution.updated_at,
            title="Nope",
        )


def test_remove_assignee_unassigns_pending_keeps_treated():
    establishment = create_establishment()
    pilot = create_business_unit(establishment=establishment, key="pilot")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    staff = _scoped_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        business_unit=pilot,
    )
    execution = _create_in_progress_execution(
        owner=owner,
        pilot_bu=pilot,
        assignees=[
            build_assignee_payload(membership=owner, business_unit=pilot),
            build_assignee_payload(membership=staff, business_unit=pilot),
        ],
        tasks=[
            build_task_payload(
                task="Pending task",
                business_unit=pilot,
                assigned_membership=staff,
            ),
            build_task_payload(
                task="Done task",
                business_unit=pilot,
                position=2,
                assigned_membership=staff,
            ),
        ],
    )
    done_task = ActionPlanExecutionTask.objects.get(
        action_plan_execution=execution,
        task="Done task",
    )
    done_task.status = ActionPlanExecutionTask.Status.DONE
    done_task.save(update_fields=["status", "updated_at"])
    execution.refresh_from_db()

    update_action_plan_execution(
        execution_id=execution.id,
        actor=owner,
        expected_updated_at=execution.updated_at,
        assignees=[
            {
                "membership_id": owner.id,
                "business_unit_id": pilot.id,
            }
        ],
    )
    pending = ActionPlanExecutionTask.objects.get(
        action_plan_execution=execution,
        task="Pending task",
    )
    done_task.refresh_from_db()
    assert pending.assigned_membership_id is None
    assert pending.assigned_display_name == ""
    assert done_task.assigned_membership_id == staff.id
    assert not ActionPlanAssignee.objects.filter(
        action_plan_execution=execution,
        membership=staff,
    ).exists()


def test_pending_assignee_must_be_in_final_assignees():
    establishment = create_establishment()
    pilot = create_business_unit(establishment=establishment, key="pilot")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    staff = _scoped_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        business_unit=pilot,
    )
    execution = _create_in_progress_execution(
        owner=owner,
        pilot_bu=pilot,
        assignees=[build_assignee_payload(membership=owner, business_unit=pilot)],
    )
    pending = ActionPlanExecutionTask.objects.get(action_plan_execution=execution)
    with pytest.raises(ActionPlanValidationError, match="assignees"):
        update_action_plan_execution(
            execution_id=execution.id,
            actor=owner,
            expected_updated_at=execution.updated_at,
            pending_tasks=[
                {
                    "id": pending.id,
                    "task": pending.task,
                    "description": "",
                    "business_unit_id": pilot.id,
                    "position": pending.position,
                    "assigned_membership_id": staff.id,
                }
            ],
        )


def test_manager_cannot_remove_out_of_scope_assignee():
    establishment = create_establishment()
    pilot = create_business_unit(establishment=establishment, key="pilot")
    other = create_business_unit(establishment=establishment, key="other")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    manager = _scoped_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        business_unit=pilot,
    )
    contributor = _scoped_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        business_unit=other,
    )
    execution = _create_in_progress_execution(
        owner=owner,
        pilot_bu=pilot,
        assignees=[
            build_assignee_payload(membership=owner, business_unit=pilot),
            build_assignee_payload(membership=contributor, business_unit=other),
        ],
        tasks=[
            build_task_payload(task="Pilot", business_unit=pilot),
            build_task_payload(task="Other", business_unit=other, position=2),
        ],
    )
    with pytest.raises(ActionPlanPermissionError, match="remove"):
        update_action_plan_execution(
            execution_id=execution.id,
            actor=manager,
            expected_updated_at=execution.updated_at,
            assignees=[
                {
                    "membership_id": owner.id,
                    "business_unit_id": pilot.id,
                }
            ],
        )


def test_manager_can_keep_cross_pole_pending_unchanged():
    establishment = create_establishment()
    pilot = create_business_unit(establishment=establishment, key="pilot")
    other = create_business_unit(establishment=establishment, key="other")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    manager = _scoped_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        business_unit=pilot,
    )
    execution = _create_in_progress_execution(
        owner=owner,
        pilot_bu=pilot,
        assignees=[build_assignee_payload(membership=owner, business_unit=pilot)],
        tasks=[
            build_task_payload(task="Pilot", business_unit=pilot),
            build_task_payload(task="Other", business_unit=other, position=2),
        ],
    )
    updated = update_action_plan_execution(
        execution_id=execution.id,
        actor=manager,
        expected_updated_at=execution.updated_at,
        title="Manager edit",
    )
    assert updated.title == "Manager edit"
    assert ActionPlanExecutionTask.objects.filter(
        action_plan_execution=execution,
        task="Other",
    ).exists()


def test_add_pending_preserves_action_plan_task_id_on_existing():
    establishment = create_establishment()
    pilot = create_business_unit(establishment=establishment, key="pilot")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    execution = _create_in_progress_execution(owner=owner, pilot_bu=pilot)
    existing = ActionPlanExecutionTask.objects.get(action_plan_execution=execution)
    original_plan_task_id = existing.action_plan_task_id
    update_action_plan_execution(
        execution_id=execution.id,
        actor=owner,
        expected_updated_at=execution.updated_at,
        pending_tasks=[
            {
                "id": existing.id,
                "task": "Renamed",
                "description": "",
                "business_unit_id": pilot.id,
                "position": 1,
            },
            {
                "task": "Brand new",
                "description": "",
                "business_unit_id": pilot.id,
                "position": 2,
            },
        ],
    )
    renamed = ActionPlanExecutionTask.objects.get(id=existing.id)
    created = ActionPlanExecutionTask.objects.get(task="Brand new")
    assert renamed.action_plan_task_id == original_plan_task_id
    assert created.action_plan_task_id is None
