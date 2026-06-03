from __future__ import annotations

import pytest
from django.utils import timezone

from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.tests.test_permissions import build_membership
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import CandidateSignal, Signal, SignalSourceObservation
from houston.signals.services import apply_pipeline_output, run_observation_pipeline
from houston.signals.tests.conftest import create_observation, create_taxonomy

pytestmark = pytest.mark.django_db


def _output_with_candidate(*, module_key: str, domain_key: str, subject_key: str):
    return ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Clim en panne",
                structured_summary="La climatisation ne fonctionne plus.",
                operational_module_key=module_key,
                operational_domain_key=domain_key,
                operational_subject_key=subject_key,
                operational_unit_key=None,
                aggregate_into_signal_id=None,
            )
        ],
    )


def test_apply_pipeline_creates_open_signal():
    membership = build_membership()
    module, domain, subject = create_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(
            module_key=module.key,
            domain_key=domain.key,
            subject_key=subject.key,
        ),
    )

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    signal = Signal.objects.get()
    assert signal.status == Signal.Status.OPEN
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.CREATED_SIGNAL).exists()


def test_invalid_taxonomy_key_rejects_candidate():
    membership = build_membership()
    create_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(
            module_key="unknown",
            domain_key="hotel__hebergement",
            subject_key="hotel__hebergement__maintenance",
        ),
    )

    assert outcome == ObservationProcessing.Outcome.NO_SIGNAL_CREATED
    assert Signal.objects.count() == 0
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.REJECTED).count() == 1


def test_observation_pipeline_links_created_signal_to_source_observation():
    membership = build_membership()
    module, domain, subject = create_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(
            module_key=module.key,
            domain_key=domain.key,
            subject_key=subject.key,
        ),
    )

    signal = Signal.objects.get()
    link = SignalSourceObservation.objects.get(signal=signal, observation=observation)
    assert link.link_type == SignalSourceObservation.LinkType.CREATED_FROM


def test_apply_pipeline_persists_aggregate_hint_signal_id():
    membership = build_membership()
    module, domain, subject = create_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    existing = Signal.objects.create(
        establishment=membership.establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
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
                    operational_module_key=module.key,
                    operational_domain_key=domain.key,
                    operational_subject_key=subject.key,
                    operational_unit_key=None,
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
    create_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider()

    run_observation_pipeline(observation.id, provider=provider)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED
    assert Signal.objects.filter(establishment=membership.establishment).exists()
