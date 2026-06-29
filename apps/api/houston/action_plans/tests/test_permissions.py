from __future__ import annotations

import pytest

from houston.accounts.models import User
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.permissions import (
    action_plan_visible_to_membership,
    can_assign_to_execution_business_unit,
    can_cancel_action_plan_execution,
    can_create_action_plan,
    can_create_linked_action_plan,
    can_create_staff_feed_execution_plan,
    can_define_cross_pole_task,
    can_execute_action_plan_task,
    can_mark_action_plan_execution_done,
    can_reopen_action_plan_execution,
    can_use_action_plan,
    can_validate_action_plan_execution,
    is_pilot_pole_assignee,
    manages_pilot_pole,
)
from houston.action_plans.services import (
    create_action_plan_with_execution,
    mark_action_plan_execution_done,
    validate_action_plan_execution,
)
from houston.action_plans.tests.conftest import build_assignee_payload, build_task_payload
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization
from houston.signals.models import Signal
from houston.testing.factories import build_membership, create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit, create_minimal_v3_signal

pytestmark = pytest.mark.django_db


def _execution_for_permissions(
    *,
    owner,
    pilot_business_unit,
    maintenance_business_unit=None,
    pilot_assignee=None,
    contributor_assignee=None,
    status=ActionPlanExecution.Status.IN_PROGRESS,
    requires_validation=True,
):
    tasks = [
        build_task_payload(task="Pilot task", business_unit=pilot_business_unit),
    ]
    assignees = []
    if pilot_assignee is not None:
        assignees.append(
            build_assignee_payload(membership=pilot_assignee, business_unit=pilot_business_unit)
        )
    if contributor_assignee is not None and maintenance_business_unit is not None:
        tasks.append(
            build_task_payload(
                task="Contributor task",
                business_unit=maintenance_business_unit,
                position=2,
            )
        )
        assignees.append(
            build_assignee_payload(
                membership=contributor_assignee,
                business_unit=maintenance_business_unit,
            )
        )
    if not assignees:
        assignees.append(
            build_assignee_payload(
                membership=pilot_assignee or owner,
                business_unit=pilot_business_unit,
            )
        )

    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=pilot_business_unit.id,
        title="Permission test plan",
        requires_validation=requires_validation,
        tasks=tasks,
        assignees=assignees,
    )

    if status == ActionPlanExecution.Status.PENDING_VALIDATION:
        execution = mark_action_plan_execution_done(
            execution_id=execution.id,
            actor_membership=owner,
        )
    elif status == ActionPlanExecution.Status.DONE:
        execution = mark_action_plan_execution_done(
            execution_id=execution.id,
            actor_membership=owner,
        )
        if requires_validation:
            execution = validate_action_plan_execution(
                execution_id=execution.id,
                actor_membership=owner,
            )
    elif status != ActionPlanExecution.Status.IN_PROGRESS:
        execution.status = status
        execution.save(update_fields=["status", "updated_at"])
    return execution


def _task_execution_for_permissions(
    *,
    owner,
    pilot_business_unit,
    maintenance_business_unit=None,
    pilot_assignee=None,
    contributor_assignee=None,
):
    execution = _execution_for_permissions(
        owner=owner,
        pilot_business_unit=pilot_business_unit,
        maintenance_business_unit=maintenance_business_unit,
        pilot_assignee=pilot_assignee,
        contributor_assignee=contributor_assignee,
        requires_validation=False,
    )
    if maintenance_business_unit is not None:
        return execution.task_executions.filter(
            execution_team__business_unit=maintenance_business_unit,
        ).select_related("action_plan_execution", "execution_team__business_unit").first()
    return execution.task_executions.select_related(
        "action_plan_execution",
        "execution_team__business_unit",
    ).first()


def test_owner_can_execute_action_plan_task(
    owner_membership,
    business_unit,
    staff_membership,
):
    task_execution = _task_execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        pilot_assignee=staff_membership,
    )
    assert can_execute_action_plan_task(owner_membership, task_execution) is True


def test_pilot_manager_can_execute_action_plan_task_without_assignee(
    owner_membership,
    manager_membership,
    business_unit,
    staff_membership,
):
    task_execution = _task_execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        pilot_assignee=staff_membership,
    )
    assert can_execute_action_plan_task(manager_membership, task_execution) is True


def test_contributor_manager_can_execute_task_in_managed_pole(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    contributor_manager_membership,
    out_of_scope_staff,
):
    task_execution = _task_execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        maintenance_business_unit=maintenance_business_unit,
        pilot_assignee=owner_membership,
        contributor_assignee=out_of_scope_staff,
    )
    assert can_execute_action_plan_task(contributor_manager_membership, task_execution) is True


def test_staff_assignee_in_scope_can_execute_task(
    owner_membership,
    business_unit,
    staff_membership,
):
    task_execution = _task_execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        pilot_assignee=staff_membership,
    )
    assert can_execute_action_plan_task(staff_membership, task_execution) is True


def test_staff_out_of_scope_cannot_execute_task(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    out_of_scope_staff,
):
    execution = _execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        maintenance_business_unit=maintenance_business_unit,
        pilot_assignee=owner_membership,
        contributor_assignee=out_of_scope_staff,
        requires_validation=False,
    )
    pilot_task = execution.task_executions.filter(
        execution_team__business_unit=business_unit,
    ).select_related("action_plan_execution", "execution_team__business_unit").first()
    assert can_execute_action_plan_task(out_of_scope_staff, pilot_task) is False


def test_staff_non_assignee_cannot_execute_task(
    owner_membership,
    business_unit,
    out_of_scope_staff,
    staff_membership,
):
    task_execution = _task_execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        pilot_assignee=staff_membership,
    )
    assert can_execute_action_plan_task(out_of_scope_staff, task_execution) is False


def test_pilot_assignee_can_mark_done(
    owner_membership,
    business_unit,
    staff_membership,
):
    execution = _execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        pilot_assignee=staff_membership,
    )

    assert is_pilot_pole_assignee(staff_membership, execution) is True
    assert can_mark_action_plan_execution_done(staff_membership, execution) is True


def test_contributor_assignee_cannot_mark_done(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    out_of_scope_staff,
):
    execution = _execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        maintenance_business_unit=maintenance_business_unit,
        pilot_assignee=owner_membership,
        contributor_assignee=out_of_scope_staff,
    )

    assert is_pilot_pole_assignee(out_of_scope_staff, execution) is False
    assert can_mark_action_plan_execution_done(out_of_scope_staff, execution) is False


def test_pilot_manager_can_mark_done_validate_reopen_cancel(
    owner_membership,
    business_unit,
    manager_membership,
    staff_membership,
):
    execution = _execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        pilot_assignee=staff_membership,
    )

    assert manages_pilot_pole(manager_membership, execution) is True
    assert can_mark_action_plan_execution_done(manager_membership, execution) is True

    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=manager_membership,
    )
    assert can_validate_action_plan_execution(manager_membership, pending) is True
    assert can_reopen_action_plan_execution(manager_membership, pending) is True
    assert can_cancel_action_plan_execution(manager_membership, pending) is True


def test_contributor_manager_cannot_mark_done_or_validate(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    contributor_manager_membership,
    out_of_scope_staff,
):
    execution = _execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        maintenance_business_unit=maintenance_business_unit,
        pilot_assignee=owner_membership,
        contributor_assignee=out_of_scope_staff,
        status=ActionPlanExecution.Status.PENDING_VALIDATION,
    )

    assert manages_pilot_pole(contributor_manager_membership, execution) is False
    assert can_mark_action_plan_execution_done(contributor_manager_membership, execution) is False
    assert can_validate_action_plan_execution(contributor_manager_membership, execution) is False
    assert can_reopen_action_plan_execution(contributor_manager_membership, execution) is False
    assert can_cancel_action_plan_execution(contributor_manager_membership, execution) is False


def test_out_of_scope_pilot_manager_denied(
    owner_membership,
    business_unit,
    out_of_scope_manager,
    staff_membership,
):
    execution = _execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        pilot_assignee=staff_membership,
        status=ActionPlanExecution.Status.PENDING_VALIDATION,
    )

    assert manages_pilot_pole(out_of_scope_manager, execution) is False
    assert can_validate_action_plan_execution(out_of_scope_manager, execution) is False


def test_staff_non_assignee_cannot_mark_done(
    owner_membership,
    business_unit,
    staff_membership,
    out_of_scope_staff,
):
    execution = _execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        pilot_assignee=staff_membership,
    )

    assert can_mark_action_plan_execution_done(out_of_scope_staff, execution) is False


def test_cross_establishment_membership_denied(owner_membership, business_unit, staff_membership):
    foreign = create_membership(
        establishment=create_establishment(name="Foreign hotel"),
        role=EstablishmentMembership.Role.OWNER,
    )
    execution = _execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        pilot_assignee=staff_membership,
        status=ActionPlanExecution.Status.PENDING_VALIDATION,
    )

    assert can_mark_action_plan_execution_done(foreign, execution) is False
    assert can_validate_action_plan_execution(foreign, execution) is False


def test_inactive_membership_denied_lifecycle(
    owner_membership,
    business_unit,
    staff_membership,
):
    execution = _execution_for_permissions(
        owner=owner_membership,
        pilot_business_unit=business_unit,
        pilot_assignee=staff_membership,
    )
    staff_membership.status = EstablishmentMembership.Status.DEACTIVATED
    staff_membership.save(update_fields=["status", "updated_at"])

    assert can_mark_action_plan_execution_done(staff_membership, execution) is False


def test_manager_can_create_in_scope_feed_plan(manager_membership, business_unit):
    assert can_create_action_plan(
        manager_membership,
        establishment_id=manager_membership.establishment_id,
        pilot_business_unit=business_unit,
    ) is True


def test_manager_out_of_scope_cannot_create(out_of_scope_manager, business_unit):
    assert can_create_action_plan(
        out_of_scope_manager,
        establishment_id=out_of_scope_manager.establishment_id,
        pilot_business_unit=business_unit,
    ) is False


def test_staff_cannot_create_catalog_plan(staff_membership, business_unit):
    assert can_create_action_plan(
        staff_membership,
        establishment_id=staff_membership.establishment_id,
        pilot_business_unit=business_unit,
    ) is False


def test_staff_feed_create_allowed(staff_membership, business_unit):
    assert can_create_staff_feed_execution_plan(
        staff_membership,
        pilot_business_unit=business_unit,
        assignees=[
            type(
                "Assignee",
                (),
                {
                    "membership": staff_membership,
                    "business_unit": business_unit,
                },
            )()
        ],
        tasks=[{"business_unit": business_unit}],
        requires_validation=False,
    ) is True


def test_staff_feed_create_rejects_requires_validation(staff_membership, business_unit):
    assert can_create_staff_feed_execution_plan(
        staff_membership,
        pilot_business_unit=business_unit,
        assignees=[
            type(
                "Assignee",
                (),
                {
                    "membership": staff_membership,
                    "business_unit": business_unit,
                },
            )()
        ],
        tasks=[],
        requires_validation=True,
    ) is False


def test_staff_cannot_create_linked_action_plan(staff_membership, signal):
    assert can_create_linked_action_plan(staff_membership, signal=signal) is False


def test_manager_can_use_catalog_when_pilot_in_scope(
    manager_membership,
    cross_pole_catalog_action_plan,
):
    assert action_plan_visible_to_membership(manager_membership, cross_pole_catalog_action_plan)
    assert can_use_action_plan(manager_membership, cross_pole_catalog_action_plan) is True


def test_manager_cannot_use_catalog_when_pilot_out_of_scope(
    out_of_scope_manager,
    cross_pole_catalog_action_plan,
):
    assert can_use_action_plan(out_of_scope_manager, cross_pole_catalog_action_plan) is False


def test_staff_cannot_use_catalog(staff_membership, catalog_action_plan):
    assert can_use_action_plan(staff_membership, catalog_action_plan) is False


def test_owner_can_define_cross_pole_task(owner_membership):
    assert can_define_cross_pole_task(owner_membership) is True


def test_manager_cannot_define_cross_pole_task(manager_membership):
    assert can_define_cross_pole_task(manager_membership) is False


def test_owner_can_assign_cross_pole(owner_membership, business_unit, maintenance_business_unit):
    assert can_assign_to_execution_business_unit(
        owner_membership,
        business_unit=maintenance_business_unit,
        pilot_business_unit=business_unit,
    ) is True


def test_pilot_manager_cannot_assign_out_of_scope(
    manager_membership,
    business_unit,
    maintenance_business_unit,
):
    assert can_assign_to_execution_business_unit(
        manager_membership,
        business_unit=maintenance_business_unit,
        pilot_business_unit=business_unit,
    ) is False


def test_manager_actionable_signal_can_create_linked(
    contributor_manager_membership,
    maintenance_business_unit,
):
    signal = create_minimal_v3_signal(
        contributor_manager_membership,
        title="Maintenance signal",
        status=Signal.Status.OPEN,
    )
    assert can_create_linked_action_plan(contributor_manager_membership, signal=signal) is True


def test_manager_visible_non_actionable_signal_denied(
    manager_membership,
    signal,
):
    assert can_create_linked_action_plan(manager_membership, signal=signal) is False


@pytest.mark.parametrize(
    "establishment_status",
    [Establishment.Status.DRAFT, Establishment.Status.DEACTIVATED],
)
def test_non_active_establishment_denies_create(establishment_status):
    membership = build_membership(
        role=EstablishmentMembership.Role.MANAGER,
        establishment_status=establishment_status,
    )
    pilot_business_unit = create_business_unit(establishment=membership.establishment, key="bar")
    assert can_create_action_plan(
        membership,
        establishment_id=membership.establishment_id,
        pilot_business_unit=pilot_business_unit,
    ) is False


@pytest.mark.parametrize(
    "organization_status",
    [Organization.Status.SUSPENDED, Organization.Status.ARCHIVED],
)
def test_non_active_organization_denies_create(organization_status):
    membership = build_membership(
        role=EstablishmentMembership.Role.MANAGER,
        organization_status=organization_status,
    )
    pilot_business_unit = create_business_unit(establishment=membership.establishment, key="bar")
    assert can_create_action_plan(
        membership,
        establishment_id=membership.establishment_id,
        pilot_business_unit=pilot_business_unit,
    ) is False


@pytest.mark.parametrize(
    "user_status",
    [User.Status.PENDING, User.Status.SUSPENDED],
)
def test_non_active_user_denies_create(user_status):
    membership = build_membership(
        role=EstablishmentMembership.Role.MANAGER,
        user_status=user_status,
    )
    pilot_business_unit = create_business_unit(establishment=membership.establishment, key="bar")
    assert can_create_action_plan(
        membership,
        establishment_id=membership.establishment_id,
        pilot_business_unit=pilot_business_unit,
    ) is False
