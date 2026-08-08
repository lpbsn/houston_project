from __future__ import annotations

import threading

import pytest
from django.db import close_old_connections, connections
from django.utils import timezone

from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import (
    OperationalPattern,
    PatternLifecycleEvent,
    SignalPatternAssignment,
)
from houston.analytics.services import (
    OWNER_CORRECTION_CLASSIFIER_VERSION,
    claim_signal_pattern_classification,
    create_operational_pattern,
    mark_assignment_processing,
    mark_assignment_succeeded,
    split_operational_pattern_to_existing,
    split_operational_pattern_to_new,
)
from houston.analytics.signature import build_signal_pattern_signature
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def create_signal_for_membership(membership, *, title="Issue"):
    return Signal.objects.create(
        establishment=membership.establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title=title,
        structured_summary="Structured issue summary",
        issue_focus="issue",
        last_activity_at=timezone.now(),
    )


def create_pattern_for_membership(membership, *, label="Pattern"):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
    )


def assign_signal_to_pattern(
    *,
    signal,
    pattern,
    signature="sig-v1",
    classifier_version="classifier-v1",
):
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature=signature,
        pending_classifier_version=classifier_version,
    )
    return mark_assignment_succeeded(
        signal=signal,
        pattern=pattern,
        assigned_signature=signature,
        assigned_classifier_version=classifier_version,
        expected_attempt_count=processing.attempt_count,
    )


def test_split_to_existing_moves_selected_signals_and_records_split_intent():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Broad pattern")
    target = create_pattern_for_membership(owner, label="Specific pattern")
    moved = create_signal_for_membership(owner, title="Moved")
    kept = create_signal_for_membership(owner, title="Kept")
    assign_signal_to_pattern(signal=moved, pattern=source)
    assign_signal_to_pattern(signal=kept, pattern=source)
    signature = build_signal_pattern_signature(moved)

    result = split_operational_pattern_to_existing(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[moved.id],
    )

    assert result.target_created is False
    assert [assignment.signal_id for assignment in result.moved_assignments] == [moved.id]
    assert SignalPatternAssignment.objects.get(signal=moved).pattern_id == target.id
    assert SignalPatternAssignment.objects.get(signal=kept).pattern_id == source.id
    assignment = SignalPatternAssignment.objects.get(signal=moved)
    assert assignment.assignment_source == (
        SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
    )
    assert assignment.owner_correction_signature == signature
    assert assignment.assigned_classifier_version == OWNER_CORRECTION_CLASSIFIER_VERSION

    split_event = PatternLifecycleEvent.objects.get(
        pattern=source,
        event_type=PatternLifecycleEvent.EventType.SPLIT,
    )
    assert split_event.metadata_safe["correction_id"] == result.correction_id
    assert split_event.metadata_safe["target_created"] is False
    assert split_event.metadata_safe["selected_signal_count"] == 1
    assert split_event.metadata_safe["moved_signal_count"] == 1
    assert "signal_ids" not in split_event.metadata_safe

    move_events = PatternLifecycleEvent.objects.filter(
        event_type=PatternLifecycleEvent.EventType.SIGNALS_MOVED,
    )
    assert move_events.count() == 2
    assert {
        event.metadata_safe["correction_id"]
        for event in move_events
    } == {result.correction_id}
    assert all(event.metadata_safe["signal_ids"] == [str(moved.id)] for event in move_events)


def test_split_to_existing_empty_selection_is_noop_without_event():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")

    result = split_operational_pattern_to_existing(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[],
    )

    assert result.moved_assignments == ()
    assert result.correction_id == ""
    assert PatternLifecycleEvent.objects.filter(
        event_type__in=[
            PatternLifecycleEvent.EventType.SPLIT,
            PatternLifecycleEvent.EventType.SIGNALS_MOVED,
        ],
    ).count() == 0


def test_split_to_new_creates_pattern_moves_assignments_and_records_created_event():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Broad pattern")
    signal = create_signal_for_membership(owner)
    assign_signal_to_pattern(signal=signal, pattern=source)

    result = split_operational_pattern_to_new(
        actor_membership=owner,
        source_pattern=source,
        label="  New   specific pattern ",
        signal_ids=[signal.id],
    )

    assert result.target_created is True
    assert result.target_pattern is not None
    assert result.target_pattern.normalized_label == "new specific pattern"
    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.pattern_id == result.target_pattern.id
    source.refresh_from_db()
    assert source.status == OperationalPattern.Status.ACTIVE

    created_event = PatternLifecycleEvent.objects.get(
        pattern=result.target_pattern,
        event_type=PatternLifecycleEvent.EventType.CREATED,
    )
    assert created_event.metadata_safe["correction_id"] == result.correction_id
    assert created_event.metadata_safe["created_for_split"] is True
    split_event = PatternLifecycleEvent.objects.get(
        pattern=source,
        event_type=PatternLifecycleEvent.EventType.SPLIT,
    )
    assert split_event.metadata_safe["target_created"] is True
    assert "signal_ids" not in split_event.metadata_safe
    assert PatternLifecycleEvent.objects.filter(
        event_type=PatternLifecycleEvent.EventType.SIGNALS_MOVED,
        metadata_safe__correction_id=result.correction_id,
    ).count() == 2


def test_split_to_new_empty_selection_does_not_create_target_or_events():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    pattern_count = OperationalPattern.objects.count()
    event_count = PatternLifecycleEvent.objects.count()

    result = split_operational_pattern_to_new(
        actor_membership=owner,
        source_pattern=source,
        label="New target",
        signal_ids=[],
    )

    assert result.target_pattern is None
    assert OperationalPattern.objects.count() == pattern_count
    assert PatternLifecycleEvent.objects.count() == event_count


def test_split_to_new_rolls_back_target_creation_when_selection_is_invalid():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    signal = create_signal_for_membership(owner)
    pattern_count = OperationalPattern.objects.count()
    event_count = PatternLifecycleEvent.objects.count()

    with pytest.raises(AnalyticsValidationError) as exc_info:
        split_operational_pattern_to_new(
            actor_membership=owner,
            source_pattern=source,
            label="New target",
            signal_ids=[signal.id],
        )

    assert exc_info.value.code == "analytics_assignment_missing"
    assert OperationalPattern.objects.count() == pattern_count
    assert PatternLifecycleEvent.objects.count() == event_count


def test_split_to_new_rejects_active_collision_and_allows_inactive_collision():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    signal = create_signal_for_membership(owner)
    assign_signal_to_pattern(signal=signal, pattern=source)
    active = create_pattern_for_membership(owner, label="New target")

    with pytest.raises(AnalyticsValidationError) as exc_info:
        split_operational_pattern_to_new(
            actor_membership=owner,
            source_pattern=source,
            label=" new  target ",
            signal_ids=[signal.id],
        )
    assert exc_info.value.code == "analytics_pattern_label_conflict"

    active.status = OperationalPattern.Status.RETIRED
    active.save(update_fields=["status", "updated_at"])
    result = split_operational_pattern_to_new(
        actor_membership=owner,
        source_pattern=source,
        label="New target",
        signal_ids=[signal.id],
    )
    assert result.target_pattern is not None
    assert result.target_pattern.status == OperationalPattern.Status.ACTIVE


def test_split_rejects_wrong_scope_and_wrong_pattern():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    other_pattern = create_pattern_for_membership(owner, label="Other")
    wrong_pattern = create_signal_for_membership(owner)
    assign_signal_to_pattern(signal=wrong_pattern, pattern=other_pattern)
    other_owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    other_signal = create_signal_for_membership(other_owner)
    SignalPatternAssignment.objects.create(
        signal=other_signal,
        pattern=source,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature="sig-v1",
        assigned_classifier_version="classifier-v1",
        assigned_at=timezone.now(),
    )

    with pytest.raises(AnalyticsValidationError) as wrong:
        split_operational_pattern_to_existing(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=target,
            signal_ids=[wrong_pattern.id],
        )
    assert wrong.value.code == "analytics_assignment_wrong_pattern"

    with pytest.raises(AnalyticsValidationError) as scoped:
        split_operational_pattern_to_existing(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=target,
            signal_ids=[other_signal.id],
        )
    assert scoped.value.code == "analytics_signal_wrong_organization"


def test_split_rejects_inactive_source_or_target_and_self_target():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    signal = create_signal_for_membership(owner)
    assign_signal_to_pattern(signal=signal, pattern=source)

    with pytest.raises(AnalyticsValidationError) as same:
        split_operational_pattern_to_existing(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=source,
            signal_ids=[signal.id],
        )
    assert same.value.code == "analytics_pattern_same_source_target"

    target.status = OperationalPattern.Status.RETIRED
    target.save(update_fields=["status", "updated_at"])
    with pytest.raises(AnalyticsValidationError) as inactive_target:
        split_operational_pattern_to_existing(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=target,
            signal_ids=[signal.id],
        )
    assert inactive_target.value.code == "analytics_pattern_target_not_active"

    source.status = OperationalPattern.Status.RETIRED
    source.save(update_fields=["status", "updated_at"])
    with pytest.raises(AnalyticsValidationError) as inactive_source:
        split_operational_pattern_to_new(
            actor_membership=owner,
            source_pattern=source,
            label="New target",
            signal_ids=[signal.id],
        )
    assert inactive_source.value.code == "analytics_pattern_source_not_active"


def test_split_to_existing_partial_repeat_moves_and_journals_delta_only():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    first = create_signal_for_membership(owner, title="First")
    second = create_signal_for_membership(owner, title="Second")
    assign_signal_to_pattern(signal=first, pattern=source)
    assign_signal_to_pattern(signal=second, pattern=target)

    result = split_operational_pattern_to_existing(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[first.id, second.id, first.id],
    )

    assert [assignment.signal_id for assignment in result.moved_assignments] == [first.id]
    assert PatternLifecycleEvent.objects.filter(
        event_type=PatternLifecycleEvent.EventType.SPLIT,
    ).count() == 1
    move_events = PatternLifecycleEvent.objects.filter(
        event_type=PatternLifecycleEvent.EventType.SIGNALS_MOVED,
    )
    assert move_events.count() == 2
    assert all(event.metadata_safe["signal_ids"] == [str(first.id)] for event in move_events)

    split_operational_pattern_to_existing(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[first.id, second.id],
    )
    assert PatternLifecycleEvent.objects.filter(
        event_type=PatternLifecycleEvent.EventType.SPLIT,
    ).count() == 1


def test_split_owner_correction_blocks_classifier_until_signature_changes():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    signal = create_signal_for_membership(owner)
    assign_signal_to_pattern(signal=signal, pattern=source)
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="pending",
        pending_classifier_version="classifier-v2",
    )

    split_operational_pattern_to_existing(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[signal.id],
    )

    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.attempt_count == processing.attempt_count + 1
    signature = build_signal_pattern_signature(signal)
    claim = claim_signal_pattern_classification(
        signal=signal,
        signature=signature,
        classifier_version="classifier-v99",
    )
    assert claim.status == "already_succeeded"

    signal.title = "Changed issue"
    signal.save(update_fields=["title", "updated_at"])
    new_claim = claim_signal_pattern_classification(
        signal=signal,
        signature=build_signal_pattern_signature(signal),
        classifier_version="classifier-v99",
    )
    assert new_claim.status == "claimed"


@pytest.mark.django_db(transaction=True)
def test_concurrent_split_to_new_same_label_allows_one_success_without_partial_move():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    first_signal = create_signal_for_membership(owner, title="First")
    second_signal = create_signal_for_membership(owner, title="Second")
    assign_signal_to_pattern(signal=first_signal, pattern=source)
    assign_signal_to_pattern(signal=second_signal, pattern=source)
    results: list[str] = []

    def _split(signal_id):
        close_old_connections()
        try:
            split_operational_pattern_to_new(
                actor_membership=EstablishmentMembership.objects.get(pk=owner.pk),
                source_pattern=OperationalPattern.objects.get(pk=source.pk),
                label="New target",
                signal_ids=[signal_id],
            )
            results.append("success")
        except AnalyticsValidationError:
            results.append("failed")
        finally:
            connections.close_all()

    first = threading.Thread(target=_split, args=(first_signal.id,))
    second = threading.Thread(target=_split, args=(second_signal.id,))
    first.start()
    second.start()
    first.join()
    second.join()
    connections.close_all()

    assert sorted(results) == ["failed", "success"]
    targets = OperationalPattern.objects.filter(normalized_label="new target")
    assert targets.count() == 1
    moved_count = SignalPatternAssignment.objects.filter(pattern=targets.get()).count()
    assert moved_count == 1
    source_count = SignalPatternAssignment.objects.filter(pattern=source).count()
    assert source_count == 1
