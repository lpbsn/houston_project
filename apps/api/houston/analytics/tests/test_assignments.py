from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.analytics.services import (
    create_operational_pattern,
    get_or_create_assignment_for_signal,
    mark_assignment_permanently_failed,
    mark_assignment_processing,
    mark_assignment_succeeded,
    mark_assignment_temporary_failed,
)
from houston.signals.models import Signal
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def create_signal_for_membership(membership):
    return Signal.objects.create(
        establishment=membership.establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title="Issue",
        structured_summary="Structured issue summary",
        last_activity_at=timezone.now(),
    )


def create_pattern_for_membership(membership, *, label="Guest Bathroom"):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
    )


def process_then_succeed(
    *,
    signal,
    pattern,
    signature,
    classifier_version,
    assigned_at=None,
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
        assigned_at=assigned_at,
    )


def test_get_or_create_assignment_for_signal_is_idempotent():
    membership = build_membership()
    signal = create_signal_for_membership(membership)

    first = get_or_create_assignment_for_signal(signal)
    second = get_or_create_assignment_for_signal(signal)

    assert first.id == second.id
    assert first.classification_status == SignalPatternAssignment.ClassificationStatus.NOT_STARTED
    assert first.pattern is None
    assert first.assigned_signature == ""
    assert first.assigned_classifier_version == ""
    assert first.assigned_at is None
    assert SignalPatternAssignment.objects.filter(signal=signal).count() == 1


def test_assignment_one_to_one_rejects_second_row_for_signal():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    SignalPatternAssignment.objects.create(signal=signal)

    with pytest.raises(IntegrityError), transaction.atomic():
        SignalPatternAssignment.objects.create(signal=signal)


def test_get_or_create_assignment_locks_signal_before_create():
    membership = build_membership()
    signal = create_signal_for_membership(membership)

    with patch.object(
        Signal.objects,
        "select_for_update",
        wraps=Signal.objects.select_for_update,
    ) as select_for_update:
        get_or_create_assignment_for_signal(signal)

    assert select_for_update.called


def test_not_started_with_pattern_is_invalid():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_membership(membership)
    assignment = SignalPatternAssignment(
        signal=signal,
        pattern=pattern,
        classification_status=SignalPatternAssignment.ClassificationStatus.NOT_STARTED,
        assigned_signature="sig-v1",
        assigned_classifier_version="classifier-v1",
        assigned_at=timezone.now(),
    )

    with pytest.raises(ValidationError) as exc_info:
        assignment.full_clean()
    assert "pattern" in exc_info.value.message_dict


def test_pattern_null_with_assigned_metadata_is_invalid():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    assignment = SignalPatternAssignment(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
        assigned_signature="sig-v1",
    )

    with pytest.raises(ValidationError) as exc_info:
        assignment.full_clean()
    assert "assigned_signature" in exc_info.value.message_dict


@pytest.mark.parametrize(
    "field_name,overrides",
    [
        ("assigned_signature", {"assigned_signature": ""}),
        ("assigned_classifier_version", {"assigned_classifier_version": ""}),
        ("assigned_at", {"assigned_at": None}),
    ],
)
def test_pattern_with_missing_success_metadata_is_invalid(field_name, overrides):
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_membership(membership)
    data = {
        "signal": signal,
        "pattern": pattern,
        "classification_status": SignalPatternAssignment.ClassificationStatus.PROCESSING,
        "assigned_signature": "sig-v1",
        "assigned_classifier_version": "classifier-v1",
        "assigned_at": timezone.now(),
    }
    data.update(overrides)
    assignment = SignalPatternAssignment(**data)

    with pytest.raises(ValidationError) as exc_info:
        assignment.full_clean()
    assert field_name in exc_info.value.message_dict


def test_processing_increments_attempt_and_preserves_last_success():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_membership(membership)
    assigned_at = timezone.now() - timedelta(hours=1)
    process_then_succeed(
        signal=signal,
        pattern=pattern,
        signature="sig-v1",
        classifier_version="classifier-v1",
        assigned_at=assigned_at,
    )

    assignment = mark_assignment_processing(
        signal=signal,
        pending_signature="sig-v2",
        pending_classifier_version="classifier-v2",
    )

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.PROCESSING
    )
    assert assignment.attempt_count == 2
    assert assignment.pending_signature == "sig-v2"
    assert assignment.pending_classifier_version == "classifier-v2"
    assert assignment.pattern_id == pattern.id
    assert assignment.assigned_signature == "sig-v1"
    assert assignment.assigned_classifier_version == "classifier-v1"
    assert assignment.assigned_at == assigned_at
    assert assignment.last_error_code == ""
    assert assignment.next_retry_at is None


def test_succeeded_replaces_pattern_and_clears_pending_and_error_fields():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    first_pattern = create_pattern_for_membership(membership, label="First")
    second_pattern = create_pattern_for_membership(membership, label="Second")
    first_assigned_at = timezone.now() - timedelta(hours=2)
    process_then_succeed(
        signal=signal,
        pattern=first_pattern,
        signature="sig-v1",
        classifier_version="classifier-v1",
        assigned_at=first_assigned_at,
    )
    assignment = mark_assignment_processing(
        signal=signal,
        pending_signature="sig-v2",
        pending_classifier_version="classifier-v2",
    )
    assignment.last_error_code = "previous_timeout"
    assignment.next_retry_at = timezone.now() + timedelta(minutes=5)
    assignment.save(update_fields=["last_error_code", "next_retry_at", "updated_at"])
    second_assigned_at = timezone.now()

    assignment = mark_assignment_succeeded(
        signal=signal,
        pattern=second_pattern,
        assigned_signature="sig-v2",
        assigned_classifier_version="classifier-v2",
        expected_attempt_count=assignment.attempt_count,
        assigned_at=second_assigned_at,
    )

    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    )
    assert assignment.pattern_id == second_pattern.id
    assert assignment.assigned_signature == "sig-v2"
    assert assignment.assigned_classifier_version == "classifier-v2"
    assert assignment.assigned_at == second_assigned_at
    assert assignment.pending_signature == ""
    assert assignment.pending_classifier_version == ""
    assert assignment.last_error_code == ""
    assert assignment.next_retry_at is None


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
def test_failures_finish_processing_and_preserve_last_success(
    failure_service,
    expected_status,
):
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_membership(membership)
    assigned_at = timezone.now() - timedelta(hours=1)
    process_then_succeed(
        signal=signal,
        pattern=pattern,
        signature="sig-v1",
        classifier_version="classifier-v1",
        assigned_at=assigned_at,
    )
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="sig-v2",
        pending_classifier_version="classifier-v2",
    )

    assignment = failure_service(
        signal=signal,
        error_code="provider_timeout",
        expected_attempt_count=processing.attempt_count,
    )

    assert assignment.classification_status == expected_status
    assert assignment.pattern_id == pattern.id
    assert assignment.assigned_signature == "sig-v1"
    assert assignment.assigned_classifier_version == "classifier-v1"
    assert assignment.assigned_at == assigned_at
    assert assignment.last_error_code == "provider_timeout"


def test_temporary_failure_stores_retry_without_modifying_assigned_at():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_membership(membership)
    assigned_at = timezone.now() - timedelta(hours=1)
    retry_at = timezone.now() + timedelta(minutes=10)
    process_then_succeed(
        signal=signal,
        pattern=pattern,
        signature="sig-v1",
        classifier_version="classifier-v1",
        assigned_at=assigned_at,
    )
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="sig-v2",
        pending_classifier_version="classifier-v2",
    )

    assignment = mark_assignment_temporary_failed(
        signal=signal,
        error_code="provider_timeout",
        expected_attempt_count=processing.attempt_count,
        next_retry_at=retry_at,
    )

    assert assignment.assigned_at == assigned_at
    assert assignment.next_retry_at == retry_at


def test_failure_without_processing_attempt_is_refused():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    get_or_create_assignment_for_signal(signal)

    with pytest.raises(AnalyticsValidationError):
        mark_assignment_temporary_failed(
            signal=signal,
            error_code="provider_timeout",
            expected_attempt_count=1,
        )


def test_succeeded_without_pattern_is_rejected_by_database():
    membership = build_membership()
    signal = create_signal_for_membership(membership)

    with pytest.raises(IntegrityError), transaction.atomic():
        SignalPatternAssignment.objects.create(
            signal=signal,
            classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        )


def test_cross_organization_pattern_is_refused():
    membership = build_membership()
    other_membership = build_membership()
    signal = create_signal_for_membership(membership)
    pattern = create_pattern_for_membership(other_membership)
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="sig-v1",
        pending_classifier_version="classifier-v1",
    )

    with pytest.raises(AnalyticsValidationError):
        mark_assignment_succeeded(
            signal=signal,
            pattern=pattern,
            assigned_signature="sig-v1",
            assigned_classifier_version="classifier-v1",
            expected_attempt_count=processing.attempt_count,
        )


@pytest.mark.parametrize(
    "status",
    [
        OperationalPattern.Status.MERGED,
        OperationalPattern.Status.RETIRED,
    ],
)
def test_inactive_pattern_is_refused(status):
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    target = create_pattern_for_membership(membership, label="Canonical")
    pattern = OperationalPattern.objects.create(
        organization=membership.establishment.organization,
        label=f"Inactive {status}",
        status=status,
        merged_into=target if status == OperationalPattern.Status.MERGED else None,
    )
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="sig-v1",
        pending_classifier_version="classifier-v1",
    )

    with pytest.raises(AnalyticsValidationError):
        mark_assignment_succeeded(
            signal=signal,
            pattern=pattern,
            assigned_signature="sig-v1",
            assigned_classifier_version="classifier-v1",
            expected_attempt_count=processing.attempt_count,
        )
