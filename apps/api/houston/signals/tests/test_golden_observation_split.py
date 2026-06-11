from __future__ import annotations

import pytest

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import CandidateSignal, Signal, SignalSourceObservation
from houston.signals.services import apply_pipeline_output
from houston.signals.tests.conftest import (
    GOLDEN_OBSERVATION_TEXT,
    RESTAURANT_MODULE_KEY,
    create_observation,
    create_restaurant_v3_taxonomy,
    golden_two_candidate_pipeline_output,
)
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def test_observation_with_lighting_issue_and_bar_stock_shortage_splits_into_two_signals():
    membership = build_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    observation = create_observation(
        membership=membership,
        text=GOLDEN_OBSERVATION_TEXT,
    )

    outcome = apply_pipeline_output(
        observation=observation,
        output=golden_two_candidate_pipeline_output(taxonomy=taxonomy),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 2
    assert (
        CandidateSignal.objects.filter(
            observation=observation,
            outcome__in=(
                CandidateSignal.Outcome.CREATED_SIGNAL,
                CandidateSignal.Outcome.AGGREGATED_SIGNAL,
            ),
        ).count()
        == 2
    )
    links = SignalSourceObservation.objects.filter(observation=observation)
    assert links.count() == 2
    assert links.filter(link_type=SignalSourceObservation.LinkType.CREATED_FROM).count() == 2

    titles = set(Signal.objects.values_list("title", flat=True))
    assert any("entrée" in title.lower() or "lumière" in title.lower() for title in titles)
    assert any("bar" in title.lower() or "mojito" in title.lower() for title in titles)

    location_texts = set(Signal.objects.values_list("location_text", flat=True))
    assert "Entrée restaurant" in location_texts
    assert "Bar" in location_texts
    assert GOLDEN_OBSERVATION_TEXT not in location_texts


def test_golden_incomplete_taxonomy_rejects_bar_stock_candidate():
    membership = build_membership()
    taxonomy = create_restaurant_v3_taxonomy(
        membership.establishment,
        include_bar_stock=False,
    )
    assert taxonomy.stock_subject is None
    assert taxonomy.lighting_subject is not None
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)

    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière clignote à l'entrée du restaurant",
                structured_summary="Entrée restaurant, éclairage instable.",
                affected_business_unit_key=RESTAURANT_MODULE_KEY,
                responsible_business_unit_key="maintenance",
                activity_subject_key=taxonomy.lighting_subject.normalized_name,
                operational_unit_key=None,
                location_text="Entrée restaurant",
                aggregate_into_signal_id=None,
            ),
            PipelineCandidateOutput(
                title="Rupture de sirop mojito au bar",
                structured_summary="Bar, sirop mojito manquant.",
                affected_business_unit_key="bar",
                responsible_business_unit_key="bar",
                activity_subject_key="stock",
                operational_unit_key=None,
                location_text="Bar",
                aggregate_into_signal_id=None,
            ),
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    signal = Signal.objects.get()
    assert signal.responsible_business_unit.key == "maintenance"
    assert CandidateSignal.objects.filter(
        observation=observation,
        outcome=CandidateSignal.Outcome.REJECTED,
    ).exists()
    assert not Signal.objects.filter(affected_business_unit__key="bar").exists()


def test_golden_incomplete_taxonomy_rejects_lighting_candidate():
    membership = build_membership()
    taxonomy = create_restaurant_v3_taxonomy(
        membership.establishment,
        include_lighting_subject=False,
    )
    assert taxonomy.lighting_subject is None
    assert taxonomy.stock_subject is not None
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)

    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière clignote à l'entrée du restaurant",
                structured_summary="Entrée restaurant, éclairage instable.",
                affected_business_unit_key=RESTAURANT_MODULE_KEY,
                responsible_business_unit_key="maintenance",
                activity_subject_key="electricite",
                operational_unit_key=None,
                location_text="Entrée restaurant",
                aggregate_into_signal_id=None,
            ),
            PipelineCandidateOutput(
                title="Rupture de sirop mojito au bar",
                structured_summary="Bar, sirop mojito manquant.",
                affected_business_unit_key="bar",
                responsible_business_unit_key="bar",
                activity_subject_key=taxonomy.stock_subject.normalized_name,
                operational_unit_key=None,
                location_text="Bar",
                aggregate_into_signal_id=None,
            ),
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    signal = Signal.objects.get()
    assert signal.affected_business_unit.key == "bar"
    assert CandidateSignal.objects.filter(
        observation=observation,
        outcome=CandidateSignal.Outcome.REJECTED,
    ).exists()
    assert not Signal.objects.filter(affected_business_unit__key=RESTAURANT_MODULE_KEY).exists()


def test_golden_invented_taxonomy_key_does_not_create_signal():
    membership = build_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)

    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière entrée",
                structured_summary="Entrée restaurant.",
                affected_business_unit_key=RESTAURANT_MODULE_KEY,
                responsible_business_unit_key="maintenance",
                activity_subject_key=taxonomy.lighting_subject.normalized_name,
                operational_unit_key=None,
                location_text=None,
                aggregate_into_signal_id=None,
            ),
            PipelineCandidateOutput(
                title="Stock inventé",
                structured_summary="Bar.",
                affected_business_unit_key="invented",
                responsible_business_unit_key="invented",
                activity_subject_key="invented_subject",
                operational_unit_key=None,
                location_text=None,
                aggregate_into_signal_id=None,
            ),
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.count() == 1
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.REJECTED).count() == 1
