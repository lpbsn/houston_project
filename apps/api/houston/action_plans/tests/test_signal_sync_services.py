from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections
from django.utils import timezone

from houston.action_plans.constants import SIGNAL_BLOCKING_EXECUTION_STATUSES
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
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.services import resolve_signal, resolve_signal_from_execution_sync
from houston.testing.pipeline import create_observation
from houston.testing.taxonomy import create_minimal_v3_signal

pytestmark = pytest.mark.django_db


def _create_linked_execution(
    *,
    owner_membership,
    signal,
    title: str,
    requires_validation: bool = False,
) -> ActionPlanExecution:
    responsible_business_unit = signal.responsible_business_unit
    assert responsible_business_unit is not None
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=responsible_business_unit.id,
        title=title,
        source_signal_id=signal.id,
        requires_validation=requires_validation,
        tasks=[
            build_task_payload(task=f"Task for {title}", business_unit=responsible_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=responsible_business_unit,
            )
        ],
        use_shared_chronology=True,
    )
    return execution


def test_cancel_single_linked_execution_reopens_signal_to_open(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Single cancel reopen",
        status=Signal.Status.OPEN,
    )
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Only execution",
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS

    cancel_action_plan_execution(execution_id=execution.id, actor=owner_membership)

    signal.refresh_from_db()
    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.CANCELED
    assert signal.status == Signal.Status.OPEN


def test_sync_resolves_when_one_done_one_canceled(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Done plus canceled",
        status=Signal.Status.IN_PROGRESS,
    )
    done_execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Done execution",
        requires_validation=False,
    )
    canceled_execution = _create_linked_execution(
        owner_membership=owner_membership,
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
        signal=signal,
        title="Execution A",
    )
    execution_b = _create_linked_execution(
        owner_membership=owner_membership,
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
        signal=signal,
        title="Canceled execution",
    )

    resolve_signal_from_execution_sync(signal=signal)
    sync_signal_after_execution_change(signal=signal)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_mark_done_without_validation_resolves_linked_signal(
    owner_membership,
    business_unit,
    staff_membership,
    signal,
):
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Mark done only",
        requires_validation=False,
    )

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_validate_execution_resolves_linked_signal(
    owner_membership,
    business_unit,
    staff_membership,
    signal,
):
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Validate only",
        requires_validation=True,
    )
    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )
    validate_action_plan_execution(
        execution_id=pending.id,
        actor_membership=owner_membership,
        stars=4,
    )

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_pending_validation_does_not_resolve_linked_signal(
    owner_membership,
    business_unit,
    staff_membership,
    signal,
):
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Pending validation",
        requires_validation=True,
    )

    pending = mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )

    assert pending.status == ActionPlanExecution.Status.PENDING_VALIDATION
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS


def test_lifecycle_reopens_signal_to_open_after_cancel_following_validation_cycle(
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
        stars=4,
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


def test_reopen_linked_execution_after_auto_resolve_sets_signal_in_progress(
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
        signal=signal,
        title="Done execution",
        requires_validation=False,
    )
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )
    # sync may already auto-resolve the Signal via the done execution.
    signal.refresh_from_db()
    if signal.status != Signal.Status.RESOLVED:
        resolve_signal_from_execution_sync(signal=signal)
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED

    reopen_action_plan_execution(execution_id=execution.id, actor=owner_membership)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS


def test_manual_resolve_refuses_in_progress_with_active_executions(
    owner_membership,
    business_unit,
    staff_membership,
):
    from houston.signals.constants import SIGNAL_IN_PROGRESS_MANUAL_RESOLVE_DETAIL
    from houston.signals.exceptions import SignalStateError

    signal = create_minimal_v3_signal(
        owner_membership,
        title="Manual resolve refused",
        status=Signal.Status.IN_PROGRESS,
    )
    execution_a = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Active A",
    )
    execution_b = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Active B",
    )

    with pytest.raises(SignalStateError, match=SIGNAL_IN_PROGRESS_MANUAL_RESOLVE_DETAIL):
        resolve_signal(signal=signal, actor_membership=owner_membership)

    signal.refresh_from_db()
    execution_a.refresh_from_db()
    execution_b.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS
    assert execution_a.status == ActionPlanExecution.Status.IN_PROGRESS
    assert execution_b.status == ActionPlanExecution.Status.IN_PROGRESS


def test_auto_resolve_cancels_active_executions_and_resolves(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Auto resolve",
        status=Signal.Status.IN_PROGRESS,
    )
    execution_a = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Active A",
    )
    execution_b = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Active B",
    )

    resolve_signal_from_execution_sync(signal=signal)

    signal.refresh_from_db()
    execution_a.refresh_from_db()
    execution_b.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
    assert execution_a.status == ActionPlanExecution.Status.CANCELED
    assert execution_b.status == ActionPlanExecution.Status.CANCELED

    sync_signal_after_execution_change(signal=signal)
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED


def test_sync_does_not_resolve_when_signal_auto_resolved_with_done_execution(
    owner_membership,
    business_unit,
    staff_membership,
):
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Auto resolve stays",
        status=Signal.Status.IN_PROGRESS,
    )
    done_execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Done execution",
        requires_validation=False,
    )
    _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Active execution",
    )
    mark_action_plan_execution_done(
        execution_id=done_execution.id,
        actor_membership=owner_membership,
    )

    resolve_signal_from_execution_sync(signal=signal)
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
        signal=signal,
        title="Done execution",
        requires_validation=False,
    )
    active_execution = _create_linked_execution(
        owner_membership=owner_membership,
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


def test_sync_noop_when_interesting_with_done_execution(
    owner_membership,
    business_unit,
    staff_membership,
):
    """Inconsistent state: interesting must not auto-resolve via sync."""
    _ = business_unit, staff_membership
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Interesting with done",
        status=Signal.Status.INTERESTING,
    )
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Forced done",
        requires_validation=False,
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS

    execution.status = ActionPlanExecution.Status.DONE
    execution.save(update_fields=["status", "updated_at"])
    signal.status = Signal.Status.INTERESTING
    signal.save(update_fields=["status", "updated_at"])

    sync_signal_after_execution_change(signal=signal)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.INTERESTING


def test_sync_noop_when_interesting_with_all_canceled_executions(
    owner_membership,
    business_unit,
    staff_membership,
):
    """Inconsistent state: interesting must not reopen to open via sync."""
    _ = business_unit, staff_membership
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Interesting with canceled",
        status=Signal.Status.INTERESTING,
    )
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Forced canceled",
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS

    now = timezone.now()
    execution.status = ActionPlanExecution.Status.CANCELED
    execution.canceled_at = now
    execution.last_activity_at = now
    execution.save(
        update_fields=["status", "canceled_at", "last_activity_at", "updated_at"]
    )
    signal.status = Signal.Status.INTERESTING
    signal.save(update_fields=["status", "updated_at"])

    sync_signal_after_execution_change(signal=signal)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.INTERESTING


@pytest.mark.django_db(transaction=True)
def test_concurrent_resolve_vs_reopen_on_created_from_siblings_does_not_break_invariants(
    owner_membership,
    business_unit,
    staff_membership,
):
    """Déclenche la course resolve(sibling_a) ↔ reopen(execution linked à sibling_b)."""
    _ = business_unit, staff_membership

    sibling_a = create_minimal_v3_signal(
        owner_membership,
        title="Sibling A",
        status=Signal.Status.IN_PROGRESS,
    )
    sibling_b = create_minimal_v3_signal(
        owner_membership,
        title="Sibling B",
        status=Signal.Status.IN_PROGRESS,
    )

    shared_observation = create_observation(membership=owner_membership, text="shared created_from")
    SignalSourceObservation.objects.create(
        signal=sibling_a,
        observation=shared_observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    SignalSourceObservation.objects.create(
        signal=sibling_b,
        observation=shared_observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    # blocking execution for sibling_a: resolve must cancel it
    blocking_execution_a = _create_linked_execution(
        owner_membership=owner_membership,
        signal=sibling_a,
        title="blocking execution for A",
        requires_validation=False,
    )

    # done execution for sibling_b: reopen should turn it back in_progress
    execution_b = _create_linked_execution(
        owner_membership=owner_membership,
        signal=sibling_b,
        title="done execution for B",
        requires_validation=False,
    )
    mark_action_plan_execution_done(
        execution_id=execution_b.id,
        actor_membership=owner_membership,
    )
    execution_b.refresh_from_db()
    assert execution_b.status == ActionPlanExecution.Status.DONE

    # Ensure sibling_b is RESOLVED so reopen transitions it to IN_PROGRESS.
    # Depending on sync timing, this may already have happened automatically.
    sibling_b.refresh_from_db()
    if sibling_b.status != Signal.Status.RESOLVED:
        resolve_signal_from_execution_sync(signal=sibling_b)
    sibling_b.refresh_from_db()
    assert sibling_b.status == Signal.Status.RESOLVED

    def run_resolve_a() -> None:
        close_old_connections()
        resolve_signal_from_execution_sync(signal=sibling_a)

    def run_reopen_b() -> None:
        close_old_connections()
        reopen_action_plan_execution(execution_id=execution_b.id, actor=owner_membership)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_resolve_a), executor.submit(run_reopen_b)]
        for future in futures:
            future.result(timeout=30)

    sibling_a.refresh_from_db()
    sibling_b.refresh_from_db()
    blocking_execution_a.refresh_from_db()
    execution_b.refresh_from_db()

    # Invariant: any resolved signal must not have blocking executions linked to it.
    if sibling_a.status == Signal.Status.RESOLVED:
        assert not ActionPlanExecution.objects.filter(
            source_signal_id=sibling_a.id,
            status__in=SIGNAL_BLOCKING_EXECUTION_STATUSES,
        ).exists()

    if sibling_b.status == Signal.Status.RESOLVED:
        assert not ActionPlanExecution.objects.filter(
            source_signal_id=sibling_b.id,
            status__in=SIGNAL_BLOCKING_EXECUTION_STATUSES,
        ).exists()

    # Sanity checks for this scenario.
    assert execution_b.status == ActionPlanExecution.Status.IN_PROGRESS
    assert sibling_b.status == Signal.Status.IN_PROGRESS
