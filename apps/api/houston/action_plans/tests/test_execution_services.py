from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections

from houston.action_plans.constants import CATALOG_STATUS_ACTIVE
from houston.action_plans.exceptions import (
    ActionPlanPermissionError,
    ActionPlanStateError,
    ActionPlanValidationError,
)
from houston.action_plans.models import (
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanTask,
)
from houston.action_plans.services import (
    cancel_action_plan_execution,
    create_action_plan,
    create_action_plan_with_execution,
    create_execution_from_action_plan,
    mark_action_plan_execution_done,
    reopen_action_plan_execution,
    validate_action_plan_execution,
)
from houston.action_plans.tests.conftest import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.factories import create_establishment
from houston.testing.taxonomy import create_minimal_v3_signal

pytestmark = pytest.mark.django_db


def test_create_ponctuel_with_tasks_and_assignees(
    owner_membership,
    business_unit,
    staff_membership,
):
    plan, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Opening checklist",
        description="Open the restaurant",
        tasks=[build_task_payload(task="Unlock doors", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    assert plan.is_reusable is False
    assert plan.catalog_status is None
    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS
    assert execution.source_signal_id is None
    assert ActionPlanTask.objects.filter(action_plan=plan).count() == 1
    assert ActionPlanExecutionTeam.objects.filter(action_plan_execution=execution).count() == 1
    assert ActionPlanAssignee.objects.filter(action_plan_execution=execution).count() == 1
    assert ActionPlanExecutionTask.objects.filter(action_plan_execution=execution).count() == 1


def test_create_ponctuel_with_tasks_only(owner_membership, business_unit):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Task-only plan",
        tasks=[build_task_payload(task="Sanitize tables", business_unit=business_unit)],
        assignees=[],
    )

    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS
    assert ActionPlanAssignee.objects.filter(action_plan_execution=execution).count() == 0
    assert ActionPlanExecutionTask.objects.filter(action_plan_execution=execution).count() == 1


def test_create_ponctuel_with_assignees_only(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Assignee-only plan",
        tasks=[],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    assert ActionPlanAssignee.objects.filter(action_plan_execution=execution).count() == 1
    assert ActionPlanExecutionTask.objects.filter(action_plan_execution=execution).count() == 0


def test_create_ponctuel_rejects_empty_execution(owner_membership, business_unit):
    with pytest.raises(ActionPlanValidationError, match="At least one task or assignee"):
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="Empty plan",
            tasks=[],
            assignees=[],
        )


def test_create_from_signal_sets_execution_signal_only(
    owner_membership,
    business_unit,
    staff_membership,
    signal,
):
    plan, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Signal plan",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Inspect leak", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    assert execution.source_signal_id == signal.id
    assert not hasattr(plan, "source_signal_id")


def test_manager_linked_signal_rejects_out_of_scope_pilot(
    contributor_manager_membership,
    maintenance_business_unit,
    business_unit,
    out_of_scope_staff,
):
    signal = create_minimal_v3_signal(
        contributor_manager_membership,
        title="Maintenance signal",
        status=Signal.Status.OPEN,
    )
    with pytest.raises(ActionPlanPermissionError, match="Not allowed to create"):
        create_action_plan_with_execution(
            establishment_id=contributor_manager_membership.establishment_id,
            created_by=contributor_manager_membership,
            pilot_business_unit_id=business_unit.id,
            title="Bypass attempt",
            source_signal_id=signal.id,
            tasks=[
                build_task_payload(task="Maintenance task", business_unit=maintenance_business_unit)
            ],
            assignees=[
                build_assignee_payload(
                    membership=out_of_scope_staff,
                    business_unit=maintenance_business_unit,
                )
            ],
        )


def test_manager_linked_signal_allows_in_scope_pilot(
    contributor_manager_membership,
    maintenance_business_unit,
    out_of_scope_staff,
):
    signal = create_minimal_v3_signal(
        contributor_manager_membership,
        title="Maintenance signal",
        status=Signal.Status.OPEN,
    )
    _, execution = create_action_plan_with_execution(
        establishment_id=contributor_manager_membership.establishment_id,
        created_by=contributor_manager_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Linked maintenance plan",
        source_signal_id=signal.id,
        tasks=[
            build_task_payload(task="Maintenance task", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=out_of_scope_staff,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    assert execution.source_signal_id == signal.id


def test_create_catalog_plan_without_execution(owner_membership, business_unit):
    plan = create_action_plan(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Catalog entry",
        is_reusable=True,
        catalog_status=CATALOG_STATUS_ACTIVE,
        tasks=[],
    )

    assert plan.is_reusable is True
    assert plan.catalog_status == CATALOG_STATUS_ACTIVE
    assert ActionPlanExecution.objects.filter(action_plan=plan).count() == 0


def test_create_execution_from_catalog_plan(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = create_execution_from_action_plan(
        action_plan_id=catalog_action_plan.id,
        actor=owner_membership,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    assert execution.action_plan_id == catalog_action_plan.id
    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS
    assert ActionPlanExecutionTask.objects.filter(action_plan_execution=execution).count() == 1


def test_create_execution_from_catalog_with_plan_tasks_only(
    owner_membership,
    catalog_action_plan,
):
    execution = create_execution_from_action_plan(
        action_plan_id=catalog_action_plan.id,
        actor=owner_membership,
        assignees=[],
    )

    assert ActionPlanExecutionTask.objects.filter(action_plan_execution=execution).count() == 1


def test_create_rejects_empty_title(owner_membership, business_unit, staff_membership):
    with pytest.raises(ActionPlanValidationError, match="Title is required"):
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="   ",
            assignees=[
                build_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        )


def test_create_rejects_assignee_out_of_establishment(
    owner_membership,
    business_unit,
    establishment,
):
    outsider = EstablishmentMembership.objects.create(
        user=owner_membership.user,
        establishment=create_establishment(name="Other hotel"),
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    with pytest.raises(ActionPlanValidationError, match="Invalid establishment membership"):
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="Bad assignee",
            assignees=[build_assignee_payload(membership=outsider, business_unit=business_unit)],
        )


def test_create_rejects_assignee_out_of_scope(
    owner_membership,
    business_unit,
    out_of_scope_staff,
):
    with pytest.raises(ActionPlanValidationError, match="out of scope"):
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="Scope mismatch",
            assignees=[
                build_assignee_payload(
                    membership=out_of_scope_staff,
                    business_unit=business_unit,
                )
            ],
        )


def test_create_rejects_invalid_signal(owner_membership, business_unit, staff_membership):
    with pytest.raises(ActionPlanValidationError, match="Invalid signal"):
        create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="Bad signal",
            source_signal_id=owner_membership.establishment_id,
            assignees=[
                build_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        )


def test_create_execution_from_inactive_catalog_rejected(
    owner_membership,
    inactive_catalog_action_plan,
):
    with pytest.raises(ActionPlanPermissionError, match="Not allowed to use"):
        create_execution_from_action_plan(
            action_plan_id=inactive_catalog_action_plan.id,
            actor=owner_membership,
            assignees=[],
        )


def test_mark_done_with_validation_goes_pending(
    owner_membership,
    execution_with_assignee,
):
    execution = mark_action_plan_execution_done(
        execution_id=execution_with_assignee.id,
        actor_membership=owner_membership,
    )

    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.PENDING_VALIDATION
    assert execution.marked_done_at is not None
    assert execution.validated_at is None


def test_mark_done_without_validation_goes_done(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="No validation",
        requires_validation=False,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    execution = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )

    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.DONE
    assert execution.marked_done_at is not None
    assert execution.validated_at is None


def test_validate_sets_validated_at(owner_membership, execution_with_assignee):
    pending = mark_action_plan_execution_done(
        execution_id=execution_with_assignee.id,
        actor_membership=owner_membership,
    )

    execution = validate_action_plan_execution(
        execution_id=pending.id,
        actor_membership=owner_membership,
    )

    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.DONE
    assert execution.validated_at is not None


def test_reopen_from_pending_validation_clears_timestamps(
    owner_membership,
    execution_with_assignee,
):
    pending = mark_action_plan_execution_done(
        execution_id=execution_with_assignee.id,
        actor_membership=owner_membership,
    )

    execution = reopen_action_plan_execution(
        execution_id=pending.id,
        actor=owner_membership,
    )

    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS
    assert execution.marked_done_at is None
    assert execution.validated_at is None
    assert execution.canceled_at is None


def test_reopen_from_done_clears_timestamps(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Done plan",
        requires_validation=False,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    done = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )

    reopened = reopen_action_plan_execution(
        execution_id=done.id,
        actor=owner_membership,
    )

    reopened.refresh_from_db()
    assert reopened.status == ActionPlanExecution.Status.IN_PROGRESS
    assert reopened.marked_done_at is None
    assert reopened.validated_at is None
    assert reopened.canceled_at is None


def test_cancel_from_in_progress_sets_canceled_at(
    owner_membership,
    execution_with_assignee,
):
    execution = cancel_action_plan_execution(
        execution_id=execution_with_assignee.id,
        actor=owner_membership,
    )

    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.CANCELED
    assert execution.canceled_at is not None


def test_cancel_from_pending_validation(
    owner_membership,
    execution_with_assignee,
):
    pending = mark_action_plan_execution_done(
        execution_id=execution_with_assignee.id,
        actor_membership=owner_membership,
    )

    execution = cancel_action_plan_execution(
        execution_id=pending.id,
        actor=owner_membership,
    )

    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.CANCELED
    assert execution.canceled_at is not None


def test_mark_done_rejects_non_in_progress(owner_membership, execution_with_assignee):
    done = mark_action_plan_execution_done(
        execution_id=execution_with_assignee.id,
        actor_membership=owner_membership,
    )

    with pytest.raises(ActionPlanStateError, match="cannot be marked done"):
        mark_action_plan_execution_done(
            execution_id=done.id,
            actor_membership=owner_membership,
        )


def test_validate_rejects_non_pending(owner_membership, execution_with_assignee):
    with pytest.raises(ActionPlanStateError, match="cannot be validated"):
        validate_action_plan_execution(
            execution_id=execution_with_assignee.id,
            actor_membership=owner_membership,
        )


def test_reopen_rejects_in_progress(owner_membership, execution_with_assignee):
    with pytest.raises(ActionPlanStateError, match="cannot be reopened"):
        reopen_action_plan_execution(
            execution_id=execution_with_assignee.id,
            actor=owner_membership,
        )


def test_reopen_rejects_canceled(owner_membership, execution_with_assignee):
    canceled = cancel_action_plan_execution(
        execution_id=execution_with_assignee.id,
        actor=owner_membership,
    )

    with pytest.raises(ActionPlanStateError, match="cannot be reopened"):
        reopen_action_plan_execution(
            execution_id=canceled.id,
            actor=owner_membership,
        )


def test_cancel_rejects_done(owner_membership, business_unit, staff_membership):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Done plan",
        requires_validation=False,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    done = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )

    with pytest.raises(ActionPlanStateError, match="cannot be canceled"):
        cancel_action_plan_execution(
            execution_id=done.id,
            actor=owner_membership,
        )


def test_pilot_manager_mark_done_succeeds(
    manager_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=manager_membership.establishment_id,
        created_by=manager_membership,
        pilot_business_unit_id=business_unit.id,
        title="Manager plan",
        requires_validation=False,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    execution = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=manager_membership,
    )

    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.DONE


def test_contributor_assignee_mark_done_denied(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    out_of_scope_staff,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Multi-pole plan",
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
            build_assignee_payload(
                membership=out_of_scope_staff,
                business_unit=maintenance_business_unit,
            ),
        ],
        tasks=[
            build_task_payload(task="Pilot", business_unit=business_unit),
            build_task_payload(
                task="Maintenance",
                business_unit=maintenance_business_unit,
                position=2,
            ),
        ],
    )

    with pytest.raises(ActionPlanPermissionError, match="Not allowed to mark"):
        mark_action_plan_execution_done(
            execution_id=execution.id,
            actor_membership=out_of_scope_staff,
        )


def test_contributor_manager_validate_denied(
    owner_membership,
    business_unit,
    maintenance_business_unit,
    contributor_manager_membership,
    out_of_scope_staff,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Validate RBAC plan",
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=business_unit),
            build_assignee_payload(
                membership=out_of_scope_staff,
                business_unit=maintenance_business_unit,
            ),
        ],
        tasks=[
            build_task_payload(task="Pilot", business_unit=business_unit),
            build_task_payload(
                task="Maintenance",
                business_unit=maintenance_business_unit,
                position=2,
            ),
        ],
    )
    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )

    with pytest.raises(ActionPlanPermissionError, match="Not allowed to validate"):
        validate_action_plan_execution(
            execution_id=pending.id,
            actor_membership=contributor_manager_membership,
        )


def test_staff_feed_create_succeeds(staff_membership, business_unit):
    _, execution = create_action_plan_with_execution(
        establishment_id=staff_membership.establishment_id,
        created_by=staff_membership,
        pilot_business_unit_id=business_unit.id,
        title="Staff personal plan",
        requires_validation=False,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
        tasks=[build_task_payload(task="My task", business_unit=business_unit)],
    )

    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS
    assert execution.requires_validation is False


def test_staff_feed_create_rejects_requires_validation(staff_membership, business_unit):
    with pytest.raises(ActionPlanPermissionError, match="Not allowed to create"):
        create_action_plan_with_execution(
            establishment_id=staff_membership.establishment_id,
            created_by=staff_membership,
            pilot_business_unit_id=business_unit.id,
            title="Staff invalid plan",
            requires_validation=True,
            assignees=[
                build_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        )


def test_staff_cannot_create_from_signal(staff_membership, business_unit, signal):
    with pytest.raises(ActionPlanPermissionError, match="Not allowed to create"):
        create_action_plan_with_execution(
            establishment_id=staff_membership.establishment_id,
            created_by=staff_membership,
            pilot_business_unit_id=business_unit.id,
            title="Staff signal plan",
            requires_validation=False,
            source_signal_id=signal.id,
            assignees=[
                build_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        )


def test_manager_direct_cross_pole_task_denied(
    manager_membership,
    business_unit,
    maintenance_business_unit,
    staff_membership,
):
    with pytest.raises(ActionPlanPermissionError, match="non-pilot business unit"):
        create_action_plan_with_execution(
            establishment_id=manager_membership.establishment_id,
            created_by=manager_membership,
            pilot_business_unit_id=business_unit.id,
            title="Cross-pole direct",
            assignees=[
                build_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
            tasks=[
                build_task_payload(
                    task="Maintenance task",
                    business_unit=maintenance_business_unit,
                )
            ],
        )


def test_manager_launches_cross_pole_catalog_in_scope_pilot(
    manager_membership,
    cross_pole_catalog_action_plan,
    staff_membership,
    business_unit,
):
    execution = create_execution_from_action_plan(
        action_plan_id=cross_pole_catalog_action_plan.id,
        actor=manager_membership,
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS
    assert ActionPlanExecutionTask.objects.filter(action_plan_execution=execution).count() == 2


def test_manager_cannot_assign_out_of_scope_on_catalog_launch(
    manager_membership,
    cross_pole_catalog_action_plan,
    out_of_scope_staff,
    maintenance_business_unit,
):
    with pytest.raises(ActionPlanPermissionError, match="Not allowed to assign"):
        create_execution_from_action_plan(
            action_plan_id=cross_pole_catalog_action_plan.id,
            actor=manager_membership,
            assignees=[
                build_assignee_payload(
                    membership=out_of_scope_staff,
                    business_unit=maintenance_business_unit,
                )
            ],
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_mark_done_only_one_succeeds(owner_membership, execution_with_assignee):
    def try_mark_done() -> str:
        close_old_connections()
        try:
            mark_action_plan_execution_done(
                execution_id=execution_with_assignee.id,
                actor_membership=owner_membership,
            )
            return "ok"
        except ActionPlanStateError:
            return "error"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: try_mark_done(), range(2)))

    assert results.count("ok") == 1
    assert results.count("error") == 1
    execution_with_assignee.refresh_from_db()
    assert execution_with_assignee.status == ActionPlanExecution.Status.PENDING_VALIDATION
