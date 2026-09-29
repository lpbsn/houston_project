from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.utils import timezone

from houston.analytics.classifier import (
    classifier_version_for_provider,
    get_pattern_classifier_provider,
)
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.scheduling import (
    republish_due_signal_pattern_classifications,
    schedule_signal_pattern_classification_on_commit,
)
from houston.analytics.services import (
    PatternClassificationRetryableError,
    mark_assignment_processing,
)
from houston.analytics.signature import build_signal_pattern_signature
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


def test_celery_redelivery_does_not_resume_a_consent_terminal_after_consent_returns(settings):
    settings.HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER = "fake"
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    provider = get_pattern_classifier_provider()
    SignalPatternAssignment.objects.create(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED,
        last_error_code="ai_consent_required",
        pending_signature=build_signal_pattern_signature(signal),
        pending_classifier_version=classifier_version_for_provider(provider),
        attempt_count=2,
    )

    with (
        patch(
            "houston.analytics.services._openai_signal_pattern_share_allowed",
            return_value=True,
        ),
        patch("houston.analytics.tasks.classify_signal_pattern") as classify,
    ):
        classify_signal_pattern_task.run(str(signal.id))

    classify.assert_not_called()
    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.attempt_count == 2
    assert assignment.classification_status == (
        SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED
    )
    assert assignment.last_error_code == "ai_consent_required"


def test_celery_redelivery_after_signature_change_is_not_a_consent_terminal():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    SignalPatternAssignment.objects.create(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED,
        last_error_code="ai_consent_required",
        pending_signature="previous-signature",
        pending_classifier_version="previous-classifier",
        attempt_count=2,
    )

    with patch("houston.analytics.tasks.classify_signal_pattern") as classify:
        classify_signal_pattern_task.run(str(signal.id))

    classify.assert_called_once_with(signal.id)


def test_task_has_no_celery_retry():
    assert classify_signal_pattern_task.max_retries == 0


def test_task_reloads_by_id_and_calls_service():
    membership = build_membership()
    signal = create_signal_for_membership(membership)

    with patch("houston.analytics.tasks.classify_signal_pattern") as classify:
        classify_signal_pattern_task.run(str(signal.id))

    classify.assert_called_once()
    assert classify.call_args.args[0] == signal.id


def test_task_noops_for_unknown_signal():
    classify_signal_pattern_task.run(str(uuid.uuid4()))


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
        patch(
            "houston.analytics.tasks.publish_signal_pattern_classification",
            return_value=True,
        ) as publish,
    ):
        classify_signal_pattern_task.run(str(signal.id))

    publish.assert_called_once_with(signal.id, countdown=30)
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
    processing.attempt_count = 4
    processing.save(update_fields=["attempt_count", "updated_at"])
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
        patch(
            "houston.analytics.tasks.publish_signal_pattern_classification",
            return_value=True,
        ) as publish,
    ):
        classify_signal_pattern_task.run(str(signal.id))

    publish.assert_not_called()

    signal.refresh_from_db()
    assignment = signal.pattern_assignment
    assert assignment.classification_status == "permanently_failed"
    assert assignment.last_error_code == "retry_exhausted"


@pytest.mark.django_db(transaction=True)
def test_schedule_persists_not_started_when_publish_fails_and_sweep_recovers():
    membership = build_membership()
    signal = create_signal_for_membership(membership)

    with patch("houston.core.celery_publish.publish_celery_task", return_value=False):
        schedule_signal_pattern_classification_on_commit(signal.id)

    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert (
        assignment.classification_status
        == SignalPatternAssignment.ClassificationStatus.NOT_STARTED
    )

    with patch("houston.core.celery_publish.publish_celery_task", return_value=True) as publish:
        assert republish_due_signal_pattern_classifications() == 1
    publish.assert_called_once()
    assert publish.call_args.kwargs["args"] == (str(signal.id),)


def test_sweep_does_not_republish_fresh_processing():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    assignment = SignalPatternAssignment.objects.create(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
        last_attempted_at=timezone.now(),
    )

    with patch("houston.core.celery_publish.publish_celery_task", return_value=True) as publish:
        assert republish_due_signal_pattern_classifications() == 0
    publish.assert_not_called()
    assignment.refresh_from_db()
    assert (
        assignment.classification_status
        == SignalPatternAssignment.ClassificationStatus.PROCESSING
    )


def test_sweep_keeps_processing_inside_the_provider_time_window():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    SignalPatternAssignment.objects.create(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
        last_attempted_at=timezone.now()
        - timedelta(seconds=settings.HOUSTON_AI_ANALYTICS_PATTERN_TIMEOUT_SECONDS * 2),
    )

    with patch("houston.core.celery_publish.publish_celery_task", return_value=True) as publish:
        assert republish_due_signal_pattern_classifications() == 0
    publish.assert_not_called()


def test_sweep_skips_assignment_blocked_for_missing_ai_consent():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    SignalPatternAssignment.objects.create(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED,
        last_error_code="ai_consent_required",
    )

    with patch("houston.core.celery_publish.publish_celery_task", return_value=True) as publish:
        assert republish_due_signal_pattern_classifications() == 0
    publish.assert_not_called()


def test_sweep_does_not_republish_a_confirmed_message_until_it_is_stale():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    SignalPatternAssignment.objects.create(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.NOT_STARTED,
        published_at=timezone.now(),
    )

    with patch("houston.core.celery_publish.publish_celery_task", return_value=True) as publish:
        assert republish_due_signal_pattern_classifications() == 0
    publish.assert_not_called()


def test_sweep_republishes_when_the_confirm_is_older_than_the_stale_window():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    SignalPatternAssignment.objects.create(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED,
        next_retry_at=timezone.now() - timedelta(seconds=1),
        published_at=timezone.now()
        - timedelta(seconds=settings.HOUSTON_ANALYTICS_PATTERN_PROCESSING_STALE_SECONDS + 5),
    )

    with patch("houston.core.celery_publish.publish_celery_task", return_value=True) as publish:
        assert republish_due_signal_pattern_classifications() == 1
    publish.assert_called_once()
    assignment = SignalPatternAssignment.objects.get(signal=signal)
    assert assignment.published_at is not None
    assert assignment.published_at > timezone.now() - timedelta(seconds=30)


def test_sweep_does_not_restack_a_confirmed_stale_processing():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    SignalPatternAssignment.objects.create(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
        last_attempted_at=timezone.now() - timedelta(days=1),
        published_at=timezone.now(),
    )

    with patch("houston.core.celery_publish.publish_celery_task", return_value=True) as publish:
        assert republish_due_signal_pattern_classifications() == 0
    publish.assert_not_called()


def test_sweep_republishes_stale_processing():
    membership = build_membership()
    signal = create_signal_for_membership(membership)
    SignalPatternAssignment.objects.create(
        signal=signal,
        classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
        last_attempted_at=timezone.now() - timedelta(days=1),
    )

    with patch("houston.core.celery_publish.publish_celery_task", return_value=True) as publish:
        assert republish_due_signal_pattern_classifications() == 1
    assert publish.call_args.kwargs["args"] == (str(signal.id),)
