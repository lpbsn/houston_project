from __future__ import annotations

from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.utils import timezone

from houston.analytics.services import (
    PatternClassificationRetryableError,
    mark_assignment_processing,
)
from houston.analytics.tasks import classify_signal_pattern_task
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


def test_task_reloads_by_id_and_calls_service():
    membership = build_membership()
    signal = create_signal_for_membership(membership)

    with patch("houston.analytics.tasks.classify_signal_pattern") as classify:
        classify_signal_pattern_task.run(str(signal.id))

    classify.assert_called_once()
    assert classify.call_args.args[0] == signal.id


def test_task_retryable_with_retry_remaining_records_temporary_failure(settings):
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="sig-v1",
        pending_classifier_version="classifier-v1",
    )
    exc = PatternClassificationRetryableError(
        "timeout",
        signal_id=signal.id,
        attempt_count=processing.attempt_count,
        pending_signature="sig-v1",
        pending_classifier_version="classifier-v1",
        error_code="provider_timeout",
    )

    with (
        patch("houston.analytics.tasks.classify_signal_pattern", side_effect=exc),
        patch.object(classify_signal_pattern_task, "retry", side_effect=Retry()) as retry,
        pytest.raises(Retry),
    ):
        classify_signal_pattern_task.run(str(signal.id))

    retry.assert_called_once()
    signal.refresh_from_db()
    assignment = signal.pattern_assignment
    assert assignment.classification_status == "temporary_failed"
    assert assignment.last_error_code == "provider_timeout"


def test_task_retryable_without_retry_remaining_records_permanent_failure():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    processing = mark_assignment_processing(
        signal=signal,
        pending_signature="sig-v1",
        pending_classifier_version="classifier-v1",
    )
    exc = PatternClassificationRetryableError(
        "timeout",
        signal_id=signal.id,
        attempt_count=processing.attempt_count,
        pending_signature="sig-v1",
        pending_classifier_version="classifier-v1",
        error_code="provider_timeout",
    )

    with patch("houston.analytics.tasks.classify_signal_pattern", side_effect=exc):
        classify_signal_pattern_task.request.retries = classify_signal_pattern_task.max_retries
        classify_signal_pattern_task.run(str(signal.id))

    signal.refresh_from_db()
    assignment = signal.pattern_assignment
    assert assignment.classification_status == "permanently_failed"
    assert assignment.last_error_code == "retry_exhausted"
