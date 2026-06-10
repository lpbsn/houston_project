from __future__ import annotations

import pytest
from django.utils import timezone

from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import CandidateSignal, Signal, SignalSourceObservation
from houston.signals.services import apply_pipeline_output, run_observation_pipeline
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
    return hotel


def _output_with_candidate(
    *,
    affected_key: str = "hotel",
    responsible_key: str = "hotel",
    subject_key: str = "maintenance",
):
    return ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Clim en panne",
                structured_summary="La climatisation ne fonctionne plus.",
                affected_business_unit_key=affected_key,
                responsible_business_unit_key=responsible_key,
                activity_subject_key=subject_key,
                operational_unit_key=None,
                location_text=None,
                aggregate_into_signal_id=None,
            )
        ],
    )


def test_apply_pipeline_creates_open_signal():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(),
    )

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    signal = Signal.objects.get()
    assert signal.status == Signal.Status.OPEN
    assert signal.affected_business_unit.key == "hotel"
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.CREATED_SIGNAL).exists()


def test_invalid_taxonomy_key_rejects_candidate():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(affected_key="unknown"),
    )

    assert outcome == ObservationProcessing.Outcome.NO_SIGNAL_CREATED
    assert Signal.objects.count() == 0
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.REJECTED).count() == 1


def test_observation_pipeline_links_created_signal_to_source_observation():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(),
    )

    signal = Signal.objects.get()
    link = SignalSourceObservation.objects.get(signal=signal, observation=observation)
    assert link.link_type == SignalSourceObservation.LinkType.CREATED_FROM


def test_apply_pipeline_persists_aggregate_hint_signal_id():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)
    existing = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Signal actif",
        structured_summary="Situation en cours.",
        last_activity_at=timezone.now(),
    )

    outcome = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                PipelineCandidateOutput(
                    title="Prolongation",
                    structured_summary="Même sujet, aggravation.",
                    affected_business_unit_key="hotel",
                    responsible_business_unit_key="hotel",
                    activity_subject_key="maintenance",
                    operational_unit_key=None,
                    location_text=None,
                    aggregate_into_signal_id=str(existing.id),
                )
            ],
        ),
    )

    assert outcome == ObservationProcessing.Outcome.SIGNAL_AGGREGATED
    row = CandidateSignal.objects.get(observation=observation)
    assert row.ai_aggregate_hint_signal_id == existing.id
    assert row.outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL
    assert row.result_signal_id == existing.id


def test_run_pipeline_with_fake_provider():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider()

    run_observation_pipeline(observation.id, provider=provider)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED
    assert Signal.objects.filter(establishment=membership.establishment).exists()
