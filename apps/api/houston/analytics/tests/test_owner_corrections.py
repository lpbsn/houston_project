from __future__ import annotations

import threading
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connections, transaction
from django.utils import timezone

from houston.accounts.models import User
from houston.analytics import services as analytics_services
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
    mark_assignment_permanently_failed,
    mark_assignment_processing,
    mark_assignment_succeeded,
    mark_assignment_temporary_failed,
    merge_operational_patterns,
    move_signals_between_patterns,
    rename_operational_pattern,
)
from houston.analytics.signature import build_signal_pattern_signature
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.factories import build_membership, create_membership

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


def test_rename_requires_owner_membership_bound_to_pattern_organization():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern_for_membership(owner, label="Leak")
    other_owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    create_membership(
        establishment=owner.establishment,
        user=other_owner.user,
        role=EstablishmentMembership.Role.OWNER,
    )

    with pytest.raises(AnalyticsValidationError) as exc_info:
        rename_operational_pattern(
            actor_membership=other_owner,
            pattern=pattern,
            label="Water leak",
        )

    assert exc_info.value.code == "analytics_owner_permission_required"
    pattern.refresh_from_db()
    assert pattern.label == "Leak"


@pytest.mark.parametrize(
    "role,status,user_status",
    [
        (
            EstablishmentMembership.Role.DIRECTOR,
            EstablishmentMembership.Status.ACTIVE,
            User.Status.ACTIVE,
        ),
        (
            EstablishmentMembership.Role.MANAGER,
            EstablishmentMembership.Status.ACTIVE,
            User.Status.ACTIVE,
        ),
        (
            EstablishmentMembership.Role.OWNER,
            EstablishmentMembership.Status.DEACTIVATED,
            User.Status.ACTIVE,
        ),
        (
            EstablishmentMembership.Role.OWNER,
            EstablishmentMembership.Status.ACTIVE,
            User.Status.SUSPENDED,
        ),
    ],
)
def test_rename_rejects_non_active_owner(role, status, user_status):
    membership = build_membership(
        role=role,
        membership_status=status,
        user_status=user_status,
    )
    pattern = create_pattern_for_membership(membership, label="Leak")

    with pytest.raises(AnalyticsValidationError):
        rename_operational_pattern(
            actor_membership=membership,
            pattern=pattern,
            label="Water leak",
        )


def test_rename_normalizes_detects_active_collision_and_journals():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern_for_membership(owner, label="Leak")
    create_pattern_for_membership(owner, label="Water leak")

    with pytest.raises(AnalyticsValidationError) as exc_info:
        rename_operational_pattern(
            actor_membership=owner,
            pattern=pattern,
            label="  water   leak ",
        )

    assert exc_info.value.code == "analytics_pattern_label_conflict"

    rename_operational_pattern(
        actor_membership=owner,
        pattern=pattern,
        label="Bathroom leak",
    )
    pattern.refresh_from_db()
    assert pattern.label == "Bathroom leak"
    assert pattern.normalized_label == "bathroom leak"
    event = PatternLifecycleEvent.objects.get(
        pattern=pattern,
        event_type=PatternLifecycleEvent.EventType.RENAMED,
    )
    assert event.metadata_safe["old_label"] == "Leak"
    assert event.metadata_safe["new_normalized_label"] == "bathroom leak"


def test_rename_noop_does_not_create_event():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern_for_membership(owner, label="Leak")

    returned = rename_operational_pattern(
        actor_membership=owner,
        pattern=pattern,
        label="Leak",
    )

    assert returned.id == pattern.id
    assert not PatternLifecycleEvent.objects.filter(
        pattern=pattern,
        event_type=PatternLifecycleEvent.EventType.RENAMED,
    ).exists()


def test_move_rejects_signal_outside_actor_scope():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    other_membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    other_signal = create_signal_for_membership(other_membership)
    SignalPatternAssignment.objects.create(
        signal=other_signal,
        pattern=source,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature="sig-v1",
        assigned_classifier_version="classifier-v1",
        assigned_at=timezone.now(),
    )

    with pytest.raises(AnalyticsValidationError) as exc_info:
        move_signals_between_patterns(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=target,
            signal_ids=[other_signal.id],
        )

    assert exc_info.value.code == "analytics_signal_wrong_organization"


def test_move_deduplicates_ids_moves_delta_and_sets_owner_provenance():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    signal = create_signal_for_membership(owner)
    already_target = create_signal_for_membership(owner, title="Already target")
    assign_signal_to_pattern(signal=signal, pattern=source)
    assign_signal_to_pattern(signal=already_target, pattern=target)
    signature = build_signal_pattern_signature(signal)

    moved = move_signals_between_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[signal.id, already_target.id, signal.id],
    )

    assert [assignment.signal_id for assignment in moved] == [signal.id]
    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.pattern_id == target.id
    assert assignment.assignment_source == (
        SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
    )
    assert assignment.owner_correction_signature == signature
    assert assignment.assigned_signature == signature
    assert assignment.assigned_classifier_version == OWNER_CORRECTION_CLASSIFIER_VERSION

    moved_events = PatternLifecycleEvent.objects.filter(
        event_type=PatternLifecycleEvent.EventType.SIGNALS_MOVED,
    )
    assert moved_events.count() == 2
    assert all(event.metadata_safe["signal_ids"] == [str(signal.id)] for event in moved_events)

    move_signals_between_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[signal.id, already_target.id],
    )
    assert PatternLifecycleEvent.objects.filter(
        event_type=PatternLifecycleEvent.EventType.SIGNALS_MOVED,
    ).count() == 2


def test_move_empty_selection_is_noop_without_event():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")

    assert (
        move_signals_between_patterns(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=target,
            signal_ids=[],
        )
        == ()
    )
    assert PatternLifecycleEvent.objects.count() == 2


def test_move_refuses_signal_without_assignment_or_wrong_pattern():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    other = create_pattern_for_membership(owner, label="Other")
    no_assignment = create_signal_for_membership(owner)
    wrong_pattern = create_signal_for_membership(owner, title="Wrong")
    assign_signal_to_pattern(signal=wrong_pattern, pattern=other)

    with pytest.raises(AnalyticsValidationError) as missing:
        move_signals_between_patterns(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=target,
            signal_ids=[no_assignment.id],
        )
    assert missing.value.code == "analytics_assignment_missing"

    with pytest.raises(AnalyticsValidationError) as wrong:
        move_signals_between_patterns(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=target,
            signal_ids=[wrong_pattern.id],
        )
    assert wrong.value.code == "analytics_assignment_wrong_pattern"


def test_merge_moves_assignments_marks_source_and_journals():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    first = create_signal_for_membership(owner, title="First")
    second = create_signal_for_membership(owner, title="Second")
    assign_signal_to_pattern(signal=first, pattern=source)
    assign_signal_to_pattern(signal=second, pattern=source)

    merge_operational_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
    )

    source.refresh_from_db()
    assert source.status == OperationalPattern.Status.MERGED
    assert source.merged_into_id == target.id
    assert set(
        SignalPatternAssignment.objects.filter(pattern=target).values_list(
            "signal_id",
            flat=True,
        )
    ) == {first.id, second.id}
    assert PatternLifecycleEvent.objects.filter(
        pattern=source,
        event_type=PatternLifecycleEvent.EventType.MERGED,
    ).exists()
    move_events = PatternLifecycleEvent.objects.filter(
        event_type=PatternLifecycleEvent.EventType.SIGNALS_MOVED,
    )
    assert move_events.count() == 2
    expected_signal_ids = tuple(sorted([str(first.id), str(second.id)]))
    assert {
        tuple(event.metadata_safe["signal_ids"])
        for event in move_events
    } == {expected_signal_ids}


def test_merge_terminal_source_noop_or_refusal_before_active_requirement():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    other = create_pattern_for_membership(owner, label="Other")
    merge_operational_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
    )
    event_count = PatternLifecycleEvent.objects.count()

    returned = merge_operational_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
    )

    assert returned.id == source.id
    assert PatternLifecycleEvent.objects.count() == event_count
    with pytest.raises(AnalyticsValidationError) as exc_info:
        merge_operational_patterns(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=other,
        )
    assert exc_info.value.code == "analytics_pattern_already_merged"


@pytest.mark.parametrize(
    "status",
    [OperationalPattern.Status.MERGED, OperationalPattern.Status.RETIRED],
)
def test_merge_refuses_non_active_source_or_target(status):
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    if status == OperationalPattern.Status.MERGED:
        source.status = status
        source.merged_into = target
    else:
        source.status = status
    source.save(update_fields=["status", "merged_into", "updated_at"])

    with pytest.raises(AnalyticsValidationError):
        merge_operational_patterns(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=create_pattern_for_membership(owner, label="Other"),
        )

    active_source = create_pattern_for_membership(owner, label="Active source")
    target.status = OperationalPattern.Status.RETIRED
    target.save(update_fields=["status", "updated_at"])
    with pytest.raises(AnalyticsValidationError) as target_error:
        merge_operational_patterns(
            actor_membership=owner,
            source_pattern=active_source,
            target_pattern=target,
        )
    assert target_error.value.code == "analytics_pattern_target_not_active"


def test_owner_correction_during_processing_invalidates_attempt_and_claim_blocks():
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
    signature = build_signal_pattern_signature(signal)

    move_signals_between_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[signal.id],
    )

    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.attempt_count == processing.attempt_count + 1
    assert assignment.pending_signature == ""
    assert assignment.pattern_id == target.id
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


@pytest.mark.parametrize(
    "failure_service,expected_status",
    [
        (
            mark_assignment_temporary_failed,
            SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED,
        ),
        (
            mark_assignment_permanently_failed,
            SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED,
        ),
    ],
)
def test_classifier_failure_preserves_owner_correction_provenance(
    failure_service,
    expected_status,
):
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    signal = create_signal_for_membership(owner)
    assign_signal_to_pattern(signal=signal, pattern=source)
    move_signals_between_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=target,
        signal_ids=[signal.id],
    )
    owner_signature = build_signal_pattern_signature(signal)
    signal.title = "Changed issue"
    signal.save(update_fields=["title", "updated_at"])
    new_signature = build_signal_pattern_signature(signal)
    claim = claim_signal_pattern_classification(
        signal=signal,
        signature=new_signature,
        classifier_version="classifier-v2",
    )

    assignment = failure_service(
        signal=signal,
        error_code="classifier_failed",
        expected_attempt_count=claim.attempt_count,
        pending_signature=new_signature,
        pending_classifier_version="classifier-v2",
    )

    assert assignment.classification_status == expected_status
    assert assignment.pattern_id == target.id
    assert assignment.assignment_source == (
        SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
    )
    assert assignment.owner_correction_signature == owner_signature


def test_classifier_success_replaces_owner_correction_provenance():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    owner_target = create_pattern_for_membership(owner, label="Owner target")
    classifier_target = create_pattern_for_membership(owner, label="Classifier target")
    signal = create_signal_for_membership(owner)
    assign_signal_to_pattern(signal=signal, pattern=source)
    move_signals_between_patterns(
        actor_membership=owner,
        source_pattern=source,
        target_pattern=owner_target,
        signal_ids=[signal.id],
    )
    signal.title = "Changed issue"
    signal.save(update_fields=["title", "updated_at"])
    signature = build_signal_pattern_signature(signal)
    claim = claim_signal_pattern_classification(
        signal=signal,
        signature=signature,
        classifier_version="classifier-v2",
    )

    assignment = mark_assignment_succeeded(
        signal=signal,
        pattern=classifier_target,
        assigned_signature=signature,
        assigned_classifier_version="classifier-v2",
        expected_attempt_count=claim.attempt_count,
    )

    assert assignment.pattern_id == classifier_target.id
    assert assignment.assignment_source == SignalPatternAssignment.AssignmentSource.CLASSIFIER
    assert assignment.owner_correction_signature == ""


def test_owner_correction_source_requires_pattern():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal_for_membership(owner)
    assignment = SignalPatternAssignment(
        signal=signal,
        assignment_source=SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION,
        owner_correction_signature="sig-v1",
    )

    with pytest.raises(ValidationError) as exc_info:
        assignment.full_clean()
    assert "pattern" in exc_info.value.message_dict

    with pytest.raises(IntegrityError), transaction.atomic():
        SignalPatternAssignment.objects.create(
            signal=signal,
            assignment_source=SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION,
            owner_correction_signature="sig-v1",
        )


def test_merge_refuses_cross_organization_signal_assignment_without_partial_move():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    other_membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    other_signal = create_signal_for_membership(other_membership)
    SignalPatternAssignment.objects.create(
        signal=other_signal,
        pattern=source,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature="sig-v1",
        assigned_classifier_version="classifier-v1",
        assigned_at=timezone.now(),
    )

    with pytest.raises(AnalyticsValidationError) as exc_info:
        merge_operational_patterns(
            actor_membership=owner,
            source_pattern=source,
            target_pattern=target,
        )

    assert exc_info.value.code == "analytics_signal_wrong_organization"
    source.refresh_from_db()
    assert source.status == OperationalPattern.Status.ACTIVE
    assert SignalPatternAssignment.objects.get(signal=other_signal).pattern_id == source.id


@pytest.mark.django_db(transaction=True)
def test_concurrent_merges_same_source_allow_one_success_without_partial_move():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target_one = create_pattern_for_membership(owner, label="Target one")
    target_two = create_pattern_for_membership(owner, label="Target two")
    signal = create_signal_for_membership(owner)
    assign_signal_to_pattern(signal=signal, pattern=source)
    results: list[str] = []

    def _merge(target_id):
        close_old_connections()
        try:
            merge_operational_patterns(
                actor_membership=EstablishmentMembership.objects.get(pk=owner.pk),
                source_pattern=OperationalPattern.objects.get(pk=source.pk),
                target_pattern=OperationalPattern.objects.get(pk=target_id),
            )
            results.append("success")
        except AnalyticsValidationError:
            results.append("failed")
        finally:
            connections.close_all()

    first = threading.Thread(target=_merge, args=(target_one.id,))
    second = threading.Thread(target=_merge, args=(target_two.id,))
    first.start()
    second.start()
    first.join()
    second.join()
    connections.close_all()

    assert sorted(results) == ["failed", "success"]
    source.refresh_from_db()
    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert source.status == OperationalPattern.Status.MERGED
    assert assignment.pattern_id == source.merged_into_id


@pytest.mark.django_db(transaction=True)
def test_concurrent_owner_move_and_ai_success_keep_owner_correction():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    source = create_pattern_for_membership(owner, label="Source")
    target = create_pattern_for_membership(owner, label="Target")
    classifier_target = create_pattern_for_membership(owner, label="Classifier")
    signal = create_signal_for_membership(owner)
    assign_signal_to_pattern(signal=signal, pattern=source)
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="pending",
        pending_classifier_version="classifier-v2",
    )
    results: list[str] = []
    owner_holds_locks = threading.Event()
    original_owner_correct = analytics_services._mark_locked_assignment_owner_corrected

    def _delayed_owner_correct(*args, **kwargs):
        owner_holds_locks.set()
        time.sleep(0.2)
        return original_owner_correct(*args, **kwargs)

    def _owner_move():
        close_old_connections()
        try:
            move_signals_between_patterns(
                actor_membership=EstablishmentMembership.objects.get(pk=owner.pk),
                source_pattern=OperationalPattern.objects.get(pk=source.pk),
                target_pattern=OperationalPattern.objects.get(pk=target.pk),
                signal_ids=[signal.id],
            )
            results.append("owner")
        finally:
            connections.close_all()

    def _ai_success():
        close_old_connections()
        try:
            mark_assignment_succeeded(
                signal=Signal.objects.get(pk=signal.pk),
                pattern=OperationalPattern.objects.get(pk=classifier_target.pk),
                assigned_signature="pending",
                assigned_classifier_version="classifier-v2",
                expected_attempt_count=processing.attempt_count,
                assigned_at=timezone.now() + timedelta(seconds=1),
            )
            results.append("ai")
        except AnalyticsValidationError:
            results.append("obsolete")
        finally:
            connections.close_all()

    first = threading.Thread(target=_owner_move)
    second = threading.Thread(target=_ai_success)
    with patch.object(
        analytics_services,
        "_mark_locked_assignment_owner_corrected",
        side_effect=_delayed_owner_correct,
    ):
        first.start()
        assert owner_holds_locks.wait(timeout=5)
        second.start()
        first.join()
        second.join()
    connections.close_all()

    assert sorted(results) == ["obsolete", "owner"]
    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.pattern_id == target.id
    assert assignment.assignment_source == (
        SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
    )
