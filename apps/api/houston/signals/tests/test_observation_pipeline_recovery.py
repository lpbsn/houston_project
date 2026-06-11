from __future__ import annotations

import logging
from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import (
    recover_stuck_observation_processing_batch,
    run_observation_pipeline,
)
from houston.signals.tasks import recover_stuck_observation_processing_task
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
