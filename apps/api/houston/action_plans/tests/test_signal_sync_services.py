from __future__ import annotations

import pytest
from django.utils import timezone

from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import (
    cancel_action_plan_execution,
    create_action_plan_with_execution,
    mark_action_plan_execution_done,
    reopen_action_plan_execution,
    sync_signal_after_execution_change,
    validate_action_plan_execution,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.signals.models import Signal
from houston.signals.services import resolve_signal
from houston.testing.taxonomy import create_minimal_v3_signal

pytestmark = pytest.mark.django_db


def _create_linked_execution(
    *,
    owner_membership,
    business_unit,
    staff_membership,
    signal,
    title: str,
    requires_validation: bool = False,
) -> ActionPlanExecution:
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title=title,
        source_signal_id=signal.id,
        requires_validation=requires_validation,
        tasks=[build_task_payload(task=f"Task for {title}", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    return execution


def test_sync_auto_resolves_when_one_done_one_canceled(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Sync resolve",
        status=Signal.Status.IN_PROGRESS,
    )
    done_execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Done execution",
        requires_validation=False,
    )
    canceled_execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Canceled execution",
    )

    mark_action_plan_execution_done(
        execution_id=done_execution.id,
        actor_membership=owner_membership,
    )
    cancel_action_plan_execution(
        execution_id=canceled_execution.id,
        actor=owner_membership,
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_sync_reopens_to_open_when_all_canceled_without_done(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Reopen to open",
        status=Signal.Status.IN_PROGRESS,
    )
    signal.is_pinned = True
    signal.pinned_at = timezone.now()
    signal.pinned_by_membership = owner_membership
    signal.save()

    execution_a = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Execution A",
    )
    execution_b = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Execution B",
    )

    cancel_action_plan_execution(execution_id=execution_a.id, actor=owner_membership)
    cancel_action_plan_execution(execution_id=execution_b.id, actor=owner_membership)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.OPEN
    assert signal.is_pinned is False
    assert signal.pinned_at is None
    assert signal.pinned_by_membership is None


def test_sync_does_not_reopen_resolved_signal_when_all_canceled(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Stay resolved",
        status=Signal.Status.IN_PROGRESS,
    )
    _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Canceled execution",
    )

    resolve_signal(signal=signal, actor_membership=owner_membership)
    sync_signal_after_execution_change(signal=signal)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_mark_done_without_validation_auto_resolves_linked_signal(
    owner_membership,
    business_unit,
    staff_membership,
    signal,
):
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Auto resolve",
        requires_validation=False,
    )

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_validate_execution_auto_resolves_linked_signal(
    owner_membership,
    business_unit,
    staff_membership,
    signal,
):
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Validate resolve",
        requires_validation=True,
    )
    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )
    validate_action_plan_execution(
        execution_id=pending.id,
        actor_membership=owner_membership,
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_lifecycle_resolves_signal_after_validation_cycle(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Lifecycle succeeds",
        status=Signal.Status.IN_PROGRESS,
    )
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Validation cycle",
        requires_validation=True,
    )

    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )
    validated = validate_action_plan_execution(
        execution_id=pending.id,
        actor_membership=owner_membership,
    )
    reopened = reopen_action_plan_execution(
        execution_id=validated.id,
        actor=owner_membership,
    )
    canceled = cancel_action_plan_execution(
        execution_id=reopened.id,
        actor=owner_membership,
    )

    assert canceled.status == ActionPlanExecution.Status.CANCELED
    signal.refresh_from_db()
    assert signal.status == Signal.Status.OPEN


def test_reopen_linked_execution_sets_signal_in_progress(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Reopen signal",
        status=Signal.Status.IN_PROGRESS,
    )
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Resolved execution",
        requires_validation=False,
    )
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED

    reopen_action_plan_execution(execution_id=execution.id, actor=owner_membership)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS


def test_resolve_signal_cancels_active_executions_and_resolves(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Manual resolve",
        status=Signal.Status.IN_PROGRESS,
    )
    execution_a = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Active A",
    )
    execution_b = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Active B",
    )

    resolve_signal(signal=signal, actor_membership=owner_membership)

    signal.refresh_from_db()
    execution_a.refresh_from_db()
    execution_b.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
    assert execution_a.status == ActionPlanExecution.Status.CANCELED
    assert execution_b.status == ActionPlanExecution.Status.CANCELED

    sync_signal_after_execution_change(signal=signal)
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_sync_idempotent_when_signal_already_resolved_with_done_execution(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Idempotent resolve",
        status=Signal.Status.IN_PROGRESS,
    )
    done_execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Done execution",
        requires_validation=False,
    )
    _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Active execution",
    )
    mark_action_plan_execution_done(
        execution_id=done_execution.id,
        actor_membership=owner_membership,
    )

    resolve_signal(signal=signal, actor_membership=owner_membership)
    sync_signal_after_execution_change(signal=signal)

    signal.refresh_from_db()
    done_execution.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
    assert done_execution.status == ActionPlanExecution.Status.DONE


def test_cancel_after_manual_resolve_does_not_rollback(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Cancel after manual resolve",
        status=Signal.Status.IN_PROGRESS,
    )
    done_execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Done execution",
        requires_validation=False,
    )
    active_execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Active execution",
    )
    mark_action_plan_execution_done(
        execution_id=done_execution.id,
        actor_membership=owner_membership,
    )

    signal.status = Signal.Status.RESOLVED
    signal.save(update_fields=["status", "updated_at"])

    canceled = cancel_action_plan_execution(
        execution_id=active_execution.id,
        actor=owner_membership,
    )

    signal.refresh_from_db()
    done_execution.refresh_from_db()
    assert canceled.status == ActionPlanExecution.Status.CANCELED
    assert done_execution.status == ActionPlanExecution.Status.DONE
    assert signal.status == Signal.Status.RESOLVED
