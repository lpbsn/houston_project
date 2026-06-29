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
from houston.action_plans.tests.conftest import build_assignee_payload, build_task_payload
from houston.actions.services import accept_action, create_action
from houston.signals.exceptions import SignalBusinessConflictError
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


def _create_active_legacy_action(*, owner_membership, staff_membership, signal):
    action = create_action(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        title="Legacy linked action",
        instruction="Work",
        assignee_ids=[staff_membership.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )
    return accept_action(action_id=action.id, accepted_by=staff_membership)


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


def test_sync_skips_auto_resolve_when_legacy_action_active(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Legacy blocks resolve",
        status=Signal.Status.IN_PROGRESS,
    )
    _create_active_legacy_action(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        signal=signal,
    )
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Done execution",
        requires_validation=False,
    )

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS


def test_sync_skips_open_when_legacy_action_active(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Legacy blocks open",
        status=Signal.Status.IN_PROGRESS,
    )
    _create_active_legacy_action(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        signal=signal,
    )
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Canceled execution",
    )

    cancel_action_plan_execution(execution_id=execution.id, actor=owner_membership)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS


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


def test_resolve_signal_still_blocked_by_active_legacy_action(
    owner_membership,
    staff_membership,
    signal,
):
    _create_active_legacy_action(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        signal=signal,
    )

    with pytest.raises(SignalBusinessConflictError):
        resolve_signal(signal=signal, actor_membership=owner_membership)


def test_lifecycle_succeeds_when_legacy_blocks_sync(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Lifecycle succeeds",
        status=Signal.Status.IN_PROGRESS,
    )
    _create_active_legacy_action(
        owner_membership=owner_membership,
        staff_membership=staff_membership,
        signal=signal,
    )
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        business_unit=business_unit,
        staff_membership=staff_membership,
        signal=signal,
        title="Blocked sync",
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
    assert signal.status == Signal.Status.IN_PROGRESS
