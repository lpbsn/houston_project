from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.action_plans.constants import EXECUTION_STATUS_SCHEDULED
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import (
    cancel_action_plan_execution,
    create_action_plan_with_execution,
)
from houston.action_plans.template_deletion_services import (
    hard_delete_scheduled_execution_for_template_deletion,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.analytics.journal import JournalEvent, first_signal_created_at, signal_status_at
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
    SIGNAL_LIFECYCLE_EVENT_CREATED,
)
from houston.signals.models import Signal, SignalLifecycleEvent
from houston.signals.services import merge_signal_into_resolved
from houston.testing.taxonomy import create_minimal_v3_signal

pytestmark = pytest.mark.django_db


def _create_linked_execution(
    *,
    owner_membership,
    signal,
    title: str,
    start_at=None,
) -> ActionPlanExecution:
    responsible = signal.responsible_business_unit
    assert responsible is not None
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=responsible.id,
        title=title,
        source_signal_id=signal.id,
        requires_validation=False,
        tasks=[build_task_payload(task=f"Task for {title}", business_unit=responsible)],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=responsible,
            )
        ],
        use_shared_chronology=True,
        start_at=start_at,
        end_at=None if start_at is None else start_at + timedelta(hours=1),
    )
    return execution


def test_linked_active_execution_stamps_first_association(owner_membership):
    signal = create_minimal_v3_signal(owner_membership, title="Active association")
    assert signal.first_action_plan_associated_at is None

    execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Active plan",
    )
    signal.refresh_from_db()

    assert execution.status != EXECUTION_STATUS_SCHEDULED
    assert signal.first_action_plan_associated_at == execution.created_at


def test_linked_scheduled_execution_stamps_first_association(owner_membership):
    signal = create_minimal_v3_signal(owner_membership, title="Scheduled association")
    start_at = timezone.now() + timedelta(days=2)

    execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Scheduled plan",
        start_at=start_at,
    )
    signal.refresh_from_db()

    assert execution.status == EXECUTION_STATUS_SCHEDULED
    assert signal.first_action_plan_associated_at == execution.created_at


def test_second_linked_execution_does_not_overwrite_association(owner_membership):
    signal = create_minimal_v3_signal(owner_membership, title="Second no-op")
    first = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="First plan",
    )
    signal.refresh_from_db()
    stamped = signal.first_action_plan_associated_at

    second = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Second plan",
    )
    signal.refresh_from_db()

    assert stamped == first.created_at
    assert second.created_at >= first.created_at
    assert signal.first_action_plan_associated_at == stamped


def test_cancel_all_linked_executions_does_not_clear_association(owner_membership):
    signal = create_minimal_v3_signal(owner_membership, title="Cancel-all keeps stamp")
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Only plan",
    )
    signal.refresh_from_db()
    stamped = signal.first_action_plan_associated_at
    assert stamped is not None

    cancel_action_plan_execution(execution_id=execution.id, actor=owner_membership)
    signal.refresh_from_db()

    assert signal.status == Signal.Status.OPEN
    assert signal.first_action_plan_associated_at == stamped


def test_hard_delete_scheduled_linked_execution_does_not_clear_association(
    owner_membership,
):
    signal = create_minimal_v3_signal(owner_membership, title="Hard-delete keeps stamp")
    start_at = timezone.now() + timedelta(days=2)
    execution = _create_linked_execution(
        owner_membership=owner_membership,
        signal=signal,
        title="Scheduled to delete",
        start_at=start_at,
    )
    signal.refresh_from_db()
    stamped = signal.first_action_plan_associated_at
    execution_id = execution.id
    assert stamped is not None
    assert execution.status == EXECUTION_STATUS_SCHEDULED

    hard_delete_scheduled_execution_for_template_deletion(execution_id=execution_id)
    signal.refresh_from_db()

    assert not ActionPlanExecution.objects.filter(id=execution_id).exists()
    assert signal.first_action_plan_associated_at == stamped


def _journal_events(signal: Signal) -> list[JournalEvent]:
    return [
        JournalEvent(
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            metadata_safe=event.metadata_safe or {},
        )
        for event in SignalLifecycleEvent.objects.filter(signal=signal).order_by(
            "occurred_at",
            "id",
        )
    ]


def test_merge_keeps_older_survivor_created_at_and_mins_association(
    owner_membership,
):
    earlier = timezone.now() - timedelta(days=6)
    later = timezone.now() - timedelta(days=2)
    source_created = timezone.now() - timedelta(days=5)
    target_created = timezone.now() - timedelta(days=10)

    source = create_minimal_v3_signal(owner_membership, title="Merge source")
    target = create_minimal_v3_signal(owner_membership, title="Merge survivor")
    Signal.objects.filter(pk=source.pk).update(
        created_at=source_created,
        first_action_plan_associated_at=earlier,
    )
    Signal.objects.filter(pk=target.pk).update(
        created_at=target_created,
        first_action_plan_associated_at=later,
    )
    source.refresh_from_db()
    target.refresh_from_db()

    merge_signal_into_resolved(
        source=source,
        target=target,
        resolution_audit={},
        candidate_expected_action=None,
    )
    source.refresh_from_db()
    target.refresh_from_db()

    assert source.first_action_plan_associated_at == earlier
    assert target.first_action_plan_associated_at == earlier
    assert source.created_at == source_created
    assert target.created_at == target_created
    assert source.merged_into_id == target.id


def test_merge_rewinds_newer_survivor_birth_and_adds_created_origin(
    owner_membership,
):
    source_created = timezone.now() - timedelta(days=6)
    plan_at = timezone.now() - timedelta(days=5)
    target_created = timezone.now() - timedelta(days=1)
    mid = source_created + timedelta(days=2)

    source = create_minimal_v3_signal(owner_membership, title="Older source")
    target = create_minimal_v3_signal(owner_membership, title="Newer survivor")
    Signal.objects.filter(pk=source.pk).update(
        created_at=source_created,
        first_action_plan_associated_at=plan_at,
    )
    Signal.objects.filter(pk=target.pk).update(created_at=target_created)
    source.refresh_from_db()
    target.refresh_from_db()

    merge_signal_into_resolved(
        source=source,
        target=target,
        resolution_audit={},
        candidate_expected_action=None,
    )
    created_count = SignalLifecycleEvent.objects.filter(
        signal=target,
        event_type=SIGNAL_LIFECYCLE_EVENT_CREATED,
    ).count()
    merge_signal_into_resolved(
        source=source,
        target=target,
        resolution_audit={},
        candidate_expected_action=None,
    )
    source.refresh_from_db()
    target.refresh_from_db()

    assert source.created_at == source_created
    assert target.created_at == source_created
    assert target.first_action_plan_associated_at == plan_at
    assert source.merged_into_id == target.id
    created_events = list(
        SignalLifecycleEvent.objects.filter(
            signal=target,
            event_type=SIGNAL_LIFECYCLE_EVENT_CREATED,
            occurred_at=source_created,
        )
    )
    assert len(created_events) == 1
    assert created_events[0].metadata_safe.get("to_status") == Signal.Status.OPEN
    assert created_events[0].metadata_safe.get("origin") == "qualify_merge"
    assert created_events[0].metadata_safe.get("source_signal_id") == str(source.id)
    assert not SignalLifecycleEvent.objects.filter(
        signal=target,
        event_type=SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
    ).exists()
    assert (
        SignalLifecycleEvent.objects.filter(
            signal=target,
            event_type=SIGNAL_LIFECYCLE_EVENT_CREATED,
        ).count()
        == created_count
    )

    events = _journal_events(target)
    assert first_signal_created_at(events, fallback=target.created_at) == source_created
    assert (
        signal_status_at(
            at=mid,
            reliable_from=source_created,
            events=events,
        )
        == Signal.Status.OPEN
    )
