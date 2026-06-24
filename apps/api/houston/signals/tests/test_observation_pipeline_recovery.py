from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import patch

import pytest
from celery.exceptions import Retry
from django.test import override_settings
from django.utils import timezone

from houston.ai.observation_pipeline import (
    FakeObservationPipelineProvider,
    ObservationPipelineUnavailableError,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import (
    recover_orphaned_observation_processing_batch,
    recover_stuck_observation_processing_batch,
    run_observation_pipeline,
)
from houston.signals.tasks import (
    process_observation_task,
    recover_stuck_observation_processing_task,
)
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def _setup_hotel_taxonomy(establishment):
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )


class _FlakyObservationPipelineProvider(FakeObservationPipelineProvider):
    def __init__(self) -> None:
        super().__init__()
        self.call_count = 0

    def propose(self, *, input_payload):
        self.call_count += 1
        if self.call_count == 1:
            raise ObservationPipelineUnavailableError("Transient provider failure")
        return super().propose(input_payload=input_payload)


def test_provider_unavailable_then_retry_completes_without_duplicate_signals():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    flaky = _FlakyObservationPipelineProvider()

    with pytest.raises(ObservationPipelineUnavailableError):
        run_observation_pipeline(observation.id, provider=flaky)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.RETRYING
    assert Signal.objects.filter(establishment=membership.establishment).count() == 0

    run_observation_pipeline(observation.id, provider=flaky)

    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED
    assert processing.outcome
    assert processing.attempt_count >= 2
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1


def test_process_observation_task_retries_after_provider_unavailable():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    flaky = _FlakyObservationPipelineProvider()

    with patch(
        "houston.ai.observation_pipeline.get_observation_pipeline_provider",
        return_value=flaky,
    ):
        with pytest.raises(Retry):
            process_observation_task.run(str(observation.id))

        process_observation_task.run(str(observation.id))

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED
    assert processing.outcome
    assert processing.attempt_count >= 2
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_stuck_processing_recovers_and_completes_pipeline(caplog):
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    processing = observation.processing
    processing.status = ObservationProcessing.Status.PROCESSING
    processing.processing_started_at = timezone.now() - timedelta(seconds=90)
    processing.attempt_count = 1
    processing.save(
        update_fields=[
            "status",
            "processing_started_at",
            "attempt_count",
            "updated_at",
        ]
    )

    with caplog.at_level(logging.WARNING, logger="houston.signals.services"):
        run_observation_pipeline(observation.id, provider=FakeObservationPipelineProvider())

    stuck_records = [
        record
        for record in caplog.records
        if record.getMessage() == "observation_pipeline_stuck_processing"
    ]
    assert len(stuck_records) == 1

    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED
    assert Signal.objects.filter(establishment=membership.establishment).exists()


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_stuck_processing_with_exhausted_attempts_fails():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    processing = observation.processing
    processing.status = ObservationProcessing.Status.PROCESSING
    processing.processing_started_at = timezone.now() - timedelta(seconds=90)
    processing.attempt_count = 3
    processing.save(
        update_fields=[
            "status",
            "processing_started_at",
            "attempt_count",
            "updated_at",
        ]
    )

    run_observation_pipeline(observation.id, provider=FakeObservationPipelineProvider())

    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
    assert processing.last_error_code == "stuck_processing_recovered"
    assert not Signal.objects.filter(establishment=membership.establishment).exists()


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_in_flight_processing_is_skipped_without_recovery():
    membership = build_membership()
    observation = create_observation(membership=membership)
    processing = observation.processing
    processing.status = ObservationProcessing.Status.PROCESSING
    processing.processing_started_at = timezone.now() - timedelta(seconds=5)
    processing.attempt_count = 1
    processing.save(
        update_fields=[
            "status",
            "processing_started_at",
            "attempt_count",
            "updated_at",
        ]
    )

    run_observation_pipeline(observation.id, provider=FakeObservationPipelineProvider())

    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSING
    assert not Signal.objects.filter(establishment=membership.establishment).exists()


def test_double_pipeline_on_processed_is_noop():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider()

    run_observation_pipeline(observation.id, provider=provider)
    signal_count = Signal.objects.filter(establishment=membership.establishment).count()
    candidate_count = CandidateSignal.objects.filter(observation=observation).count()

    run_observation_pipeline(observation.id, provider=provider)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED
    assert Signal.objects.filter(establishment=membership.establishment).count() == signal_count
    assert CandidateSignal.objects.filter(observation=observation).count() == candidate_count


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_recovery_sweep_task_recovers_stuck_rows():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    processing = observation.processing
    processing.status = ObservationProcessing.Status.PROCESSING
    processing.processing_started_at = timezone.now() - timedelta(seconds=90)
    processing.attempt_count = 1
    processing.save(
        update_fields=[
            "status",
            "processing_started_at",
            "attempt_count",
            "updated_at",
        ]
    )

    acted_on = recover_stuck_observation_processing_batch()
    assert acted_on == 1

    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.RETRYING
    assert processing.last_error_code == "stuck_processing_recovered"

    run_observation_pipeline(observation.id, provider=FakeObservationPipelineProvider())
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_recovery_sweep_re_enqueues_pipeline_task():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    processing = observation.processing
    processing.status = ObservationProcessing.Status.PROCESSING
    processing.processing_started_at = timezone.now() - timedelta(seconds=90)
    processing.attempt_count = 1
    processing.save(
        update_fields=[
            "status",
            "processing_started_at",
            "attempt_count",
            "updated_at",
        ]
    )

    with patch("houston.signals.tasks.process_observation_task.delay") as delay:
        acted_on = recover_stuck_observation_processing_batch()
        assert acted_on == 1
        delay.assert_called_once_with(str(observation.id))


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_orphan_queued_recovery_re_enqueues_task():
    membership = build_membership()
    observation = create_observation(membership=membership)
    processing = observation.processing
    processing.queued_at = timezone.now() - timedelta(seconds=90)
    processing.save(update_fields=["queued_at", "updated_at"])

    with patch("houston.signals.tasks.process_observation_task.delay") as delay:
        enqueued = recover_orphaned_observation_processing_batch()
        assert enqueued == 1
        delay.assert_called_once_with(str(observation.id))


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_orphan_retrying_recovery_re_enqueues_task():
    membership = build_membership()
    observation = create_observation(membership=membership)
    processing = observation.processing
    ObservationProcessing.objects.filter(pk=processing.pk).update(
        status=ObservationProcessing.Status.RETRYING,
        processing_started_at=None,
        updated_at=timezone.now() - timedelta(seconds=90),
    )

    with patch("houston.signals.tasks.process_observation_task.delay") as delay:
        enqueued = recover_orphaned_observation_processing_batch()
        assert enqueued == 1
        delay.assert_called_once_with(str(observation.id))


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_recovery_batch_does_not_duplicate_enqueue_on_overlap():
    membership = build_membership()
    observation = create_observation(membership=membership)
    processing = observation.processing
    processing.queued_at = timezone.now() - timedelta(seconds=90)
    processing.save(update_fields=["queued_at", "updated_at"])

    already_enqueued: set = set()
    with patch("houston.signals.tasks.process_observation_task.delay") as delay:
        recover_orphaned_observation_processing_batch(already_enqueued=already_enqueued)
        recover_orphaned_observation_processing_batch(already_enqueued=already_enqueued)
        delay.assert_called_once_with(str(observation.id))


def test_recovery_sweep_task_wrapper():
    membership = build_membership()
    observation = create_observation(membership=membership)
    processing = observation.processing
    processing.status = ObservationProcessing.Status.PROCESSING
    processing.processing_started_at = timezone.now() - timedelta(seconds=90)
    processing.attempt_count = 3
    processing.save(
        update_fields=[
            "status",
            "processing_started_at",
            "attempt_count",
            "updated_at",
        ]
    )

    with override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30):
        acted_on = recover_stuck_observation_processing_task.run()

    assert acted_on == 1
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
