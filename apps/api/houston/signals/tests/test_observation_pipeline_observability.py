from __future__ import annotations

import logging
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone

from houston.ai.observation_pipeline import (
    FakeObservationPipelineProvider,
    ObservationPipelineInvalidOutputError,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.signals.services import run_observation_pipeline
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


def test_pipeline_failure_logs_safe_ux_projection(caplog):
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(
        membership=membership,
        text="Sensitive operational detail that must never appear in logs.",
    )
    provider = FakeObservationPipelineProvider()

    with patch.object(
        provider,
        "propose",
        side_effect=ObservationPipelineInvalidOutputError(
            "invalid output",
            payload={"candidates": []},
        ),
    ):
        with caplog.at_level(logging.WARNING, logger="houston.signals.services"):
            run_observation_pipeline(observation.id, provider=provider)

    failure_records = [
        record
        for record in caplog.records
        if record.getMessage() == "observation_pipeline_failed"
    ]
    assert len(failure_records) == 1
    record = failure_records[0]
    assert record.observation_id == str(observation.id)
    assert record.ux_status == "analysis_failed"
    assert record.last_error_code == "invalid_structured_output"
    assert "Sensitive operational detail" not in caplog.text
    assert observation.raw_text not in caplog.text

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED


@override_settings(HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS=30)
def test_stuck_processing_logs_duration_and_status(caplog):
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
    record = stuck_records[0]
    assert record.observation_id == str(observation.id)
    assert record.processing_status == ObservationProcessing.Status.PROCESSING
    assert record.processing_duration_seconds >= 90
    assert observation.raw_text not in caplog.text

    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED
