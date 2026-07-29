from __future__ import annotations

import pytest
from django.db import transaction

from houston.action_plans.services import (
    create_action_plan_with_execution,
    mark_action_plan_execution_done,
    reopen_action_plan_execution,
    sync_signal_after_execution_change,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.signals.api.serializers import (
    serialize_signal_detail,
    serialize_signal_feed_item,
)
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
    SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING,
    SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN,
    SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST,
)
from houston.signals.exceptions import SignalStateError
from houston.signals.lifecycle_events import sanitize_lifecycle_metadata_safe
from houston.signals.models import Signal, SignalLifecycleEvent
from houston.signals.resolution_request_services import (
    approve_signal_resolution_request,
    cancel_signal_resolution_request_by_requester,
    create_signal_resolution_request,
    reject_signal_resolution_request,
)
from houston.signals.services import (
    archive_signal,
    mark_signal_interesting,
    merge_signal_into_resolved,
    resolve_signal,
)
from houston.signals.tests.conftest import build_api_membership, create_minimal_v3_signal
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)

pytestmark = pytest.mark.django_db


def _lifecycle_events(*, signal: Signal) -> list[SignalLifecycleEvent]:
    return list(
        SignalLifecycleEvent.objects.filter(signal=signal).order_by("occurred_at", "id")
    )


def _create_linked_execution(*, owner_membership, signal, title: str = "Linked plan"):
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
    )
    return execution


def test_manual_resolve_sets_actor_origin_and_lifecycle_event():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Manual resolve audit")

    result = resolve_signal(signal=signal, actor_membership=membership)

    assert result.status == Signal.Status.RESOLVED
    assert result.resolved_by_membership_id == membership.id
    assert result.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_MANUAL
    assert result.resolved_at is not None
    events = _lifecycle_events(signal=result)
    assert len(events) == 1
    assert events[0].event_type == SIGNAL_LIFECYCLE_EVENT_RESOLVED
    assert events[0].actor_membership_id == membership.id
    assert events[0].occurred_at == result.resolved_at
    assert events[0].metadata_safe["resolution_origin"] == SIGNAL_RESOLUTION_ORIGIN_MANUAL


def test_action_plan_resolve_null_actor_and_origin():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="AP resolve audit")
    execution = _create_linked_execution(owner_membership=membership, signal=signal)
    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=membership,
    )
    signal.refresh_from_db()

    assert signal.status == Signal.Status.RESOLVED
    assert signal.resolved_by_membership_id is None
    assert signal.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN
    resolved_events = [
        e
        for e in _lifecycle_events(signal=signal)
        if e.event_type == SIGNAL_LIFECYCLE_EVENT_RESOLVED
    ]
    assert len(resolved_events) == 1
    assert resolved_events[0].actor_membership_id is None
    assert resolved_events[0].occurred_at == signal.resolved_at


def test_approve_resolution_request_sets_origin_without_rr_lifecycle_events():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, title="RR approve audit")
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    assign_business_unit_scope(manager, signal.responsible_business_unit)
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    assign_business_unit_scope(staff, signal.responsible_business_unit)

    request = create_signal_resolution_request(signal=signal, actor_membership=staff)
    before = SignalLifecycleEvent.objects.filter(signal=signal).count()
    approve_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
    )
    signal.refresh_from_db()

    assert signal.status == Signal.Status.RESOLVED
    assert signal.resolved_by_membership_id == manager.id
    assert signal.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST
    events = _lifecycle_events(signal=signal)
    assert SignalLifecycleEvent.objects.filter(signal=signal).count() == before + 1
    assert events[-1].event_type == SIGNAL_LIFECYCLE_EVENT_RESOLVED
    assert all(
        not e.event_type.startswith("signal.resolution_request") for e in events
    )


def test_reject_and_cancel_resolution_request_do_not_emit_lifecycle_events():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, title="RR no lifecycle")
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    assign_business_unit_scope(manager, signal.responsible_business_unit)
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    assign_business_unit_scope(staff, signal.responsible_business_unit)

    request = create_signal_resolution_request(signal=signal, actor_membership=staff)
    assert SignalLifecycleEvent.objects.filter(signal=signal).count() == 0

    reject_signal_resolution_request(
        resolution_request=request,
        actor_membership=manager,
    )
    assert SignalLifecycleEvent.objects.filter(signal=signal).count() == 0

    request2 = create_signal_resolution_request(signal=signal, actor_membership=staff)
    cancel_signal_resolution_request_by_requester(
        resolution_request=request2,
        actor_membership=staff,
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.OPEN
    assert SignalLifecycleEvent.objects.filter(signal=signal).count() == 0


def test_mark_interesting_and_archive_record_actor_fields_and_events():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Interesting archive audit")

    interesting = mark_signal_interesting(signal=signal, actor_membership=membership)
    assert interesting.status == Signal.Status.INTERESTING
    assert interesting.marked_interesting_by_membership_id == membership.id
    assert interesting.marked_interesting_at is not None
    events = _lifecycle_events(signal=interesting)
    assert events[-1].event_type == SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING
    assert events[-1].occurred_at == interesting.marked_interesting_at

    archived = archive_signal(signal=interesting, actor_membership=membership)
    assert archived.status == Signal.Status.ARCHIVED
    assert archived.archived_by_membership_id == membership.id
    assert archived.archived_at is not None
    events = _lifecycle_events(signal=archived)
    assert events[-1].event_type == SIGNAL_LIFECYCLE_EVENT_ARCHIVED
    assert events[-1].actor_membership_id == membership.id
    assert events[-1].occurred_at == archived.archived_at


def test_merge_archive_null_actor():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_minimal_v3_signal(membership, title="Merge source")
    target = create_minimal_v3_signal(membership, title="Merge target")
    from_status = source.status

    merge_signal_into_resolved(
        source=source,
        target=target,
        resolution_audit={},
        candidate_expected_action=None,
    )
    source.refresh_from_db()

    assert source.status == Signal.Status.ARCHIVED
    assert source.archived_by_membership_id is None
    assert source.archived_at is not None
    events = [
        e
        for e in _lifecycle_events(signal=source)
        if e.event_type == SIGNAL_LIFECYCLE_EVENT_ARCHIVED
    ]
    assert len(events) == 1
    assert events[0].actor_membership_id is None
    assert events[0].metadata_safe["origin"] == "qualify_merge"
    assert events[0].metadata_safe["from_status"] == from_status


def test_create_linked_plan_emits_moved_in_progress_with_creator_actor():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Move in progress audit")

    _create_linked_execution(owner_membership=membership, signal=signal)
    signal.refresh_from_db()

    assert signal.status == Signal.Status.IN_PROGRESS
    events = [
        e
        for e in _lifecycle_events(signal=signal)
        if e.event_type == SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS
    ]
    assert len(events) == 1
    assert events[0].actor_membership_id == membership.id


def test_reopen_clears_resolved_fields_and_emits_moved_in_progress():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Reopen clear audit")
    execution = _create_linked_execution(owner_membership=membership, signal=signal)
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=membership,
    )
    signal.refresh_from_db()
    first_resolved_at = signal.resolved_at
    assert first_resolved_at is not None

    reopen_action_plan_execution(execution_id=execution.id, actor=membership)
    signal.refresh_from_db()

    assert signal.status == Signal.Status.IN_PROGRESS
    assert signal.resolved_by_membership_id is None
    assert signal.resolved_at is None
    assert signal.resolution_origin is None
    moved = [
        e
        for e in _lifecycle_events(signal=signal)
        if e.event_type == SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS
    ]
    assert len(moved) >= 2
    assert moved[-1].actor_membership_id == membership.id


def test_detail_exposes_audit_fields_feed_does_not():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Detail audit fields")
    resolve_signal(signal=signal, actor_membership=membership)
    signal.refresh_from_db()

    class _Req:
        pass

    detail = serialize_signal_detail(signal=signal, membership=membership, request=_Req())
    feed = serialize_signal_feed_item(signal=signal, membership=membership)

    assert detail["resolved_by_membership_id"] == membership.id
    assert detail["resolution_origin"] == SIGNAL_RESOLUTION_ORIGIN_MANUAL
    assert detail["resolved_at"] == signal.resolved_at
    assert "resolved_by_membership_id" not in feed
    assert "resolution_origin" not in feed


def test_metadata_safe_strips_disallowed_keys():
    safe = sanitize_lifecycle_metadata_safe(
        {
            "from_status": "open",
            "to_status": "resolved",
            "request_comment": "secret text",
            "nested": {"a": 1},
        }
    )
    assert safe == {"from_status": "open", "to_status": "resolved"}


def test_invalid_transition_does_not_create_lifecycle_event():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(
        membership,
        title="Invalid interesting",
        status=Signal.Status.INTERESTING,
    )
    before = SignalLifecycleEvent.objects.filter(signal=signal).count()

    with pytest.raises(SignalStateError):
        mark_signal_interesting(signal=signal, actor_membership=membership)

    assert SignalLifecycleEvent.objects.filter(signal=signal).count() == before


def test_sync_replay_on_resolved_is_noop_for_lifecycle_events():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Sync idempotent")
    execution = _create_linked_execution(owner_membership=membership, signal=signal)
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=membership,
    )
    signal.refresh_from_db()
    count_after_resolve = SignalLifecycleEvent.objects.filter(signal=signal).count()

    sync_signal_after_execution_change(signal=signal)
    assert SignalLifecycleEvent.objects.filter(signal=signal).count() == count_after_resolve


def test_activate_already_in_progress_does_not_duplicate_moved_event():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Already in progress")
    _create_linked_execution(
        owner_membership=membership,
        signal=signal,
        title="First plan",
    )
    signal.refresh_from_db()
    moved_count = SignalLifecycleEvent.objects.filter(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
    ).count()
    assert moved_count == 1

    _create_linked_execution(
        owner_membership=membership,
        signal=signal,
        title="Second plan",
    )
    assert (
        SignalLifecycleEvent.objects.filter(
            signal=signal,
            event_type=SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
        ).count()
        == moved_count
    )


def test_lifecycle_event_rolls_back_with_failed_transition():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Rollback joint")

    with pytest.raises(RuntimeError, match="forced failure"):
        with transaction.atomic():
            resolve_signal(signal=signal, actor_membership=membership)
            raise RuntimeError("forced failure")

    signal.refresh_from_db()
    assert signal.status == Signal.Status.OPEN
    assert signal.resolved_at is None
    assert SignalLifecycleEvent.objects.filter(signal=signal).count() == 0


def test_shared_timestamp_between_resolved_at_and_occurred_at():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Shared timestamp")
    resolve_signal(signal=signal, actor_membership=membership)
    signal.refresh_from_db()
    event = SignalLifecycleEvent.objects.get(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    )
    assert signal.resolved_at == event.occurred_at


def test_append_only_resolve_reopen_resolve_keeps_prior_event_intact():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Append only cycle")
    execution = _create_linked_execution(owner_membership=membership, signal=signal)
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=membership,
    )
    signal.refresh_from_db()
    first = SignalLifecycleEvent.objects.get(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    )
    first_id = first.id
    first_occurred_at = first.occurred_at
    first_metadata = dict(first.metadata_safe)

    reopen_action_plan_execution(execution_id=execution.id, actor=membership)
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=membership,
    )

    resolved_events = list(
        SignalLifecycleEvent.objects.filter(
            signal=signal,
            event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        ).order_by("occurred_at", "id")
    )
    assert len(resolved_events) == 2
    prior = SignalLifecycleEvent.objects.get(id=first_id)
    assert prior.occurred_at == first_occurred_at
    assert prior.metadata_safe == first_metadata
    assert prior.actor_membership_id is None
