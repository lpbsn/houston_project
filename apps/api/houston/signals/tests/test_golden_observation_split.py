from __future__ import annotations

import pytest

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.tests.test_permissions import build_membership
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import CandidateSignal, Signal, SignalSourceObservation
from houston.signals.services import apply_pipeline_output
from houston.signals.tests.conftest import (
    GOLDEN_OBSERVATION_TEXT,
    RESTAURANT_BAR_STOCK_SUBJECT_KEY,
    RESTAURANT_MODULE_KEY,
    RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY,
    create_observation,
    create_restaurant_lighting_bar_stock_taxonomy,
    golden_two_candidate_pipeline_output,
)

pytestmark = pytest.mark.django_db


def test_observation_with_lighting_issue_and_bar_stock_shortage_splits_into_two_signals():
    membership = build_membership()
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    observation = create_observation(
        membership=membership,
        text=GOLDEN_OBSERVATION_TEXT,
    )

    outcome = apply_pipeline_output(
        observation=observation,
        output=golden_two_candidate_pipeline_output(taxonomy=taxonomy),
    )

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
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(
        membership.establishment,
        include_bar_stock=False,
    )
    assert taxonomy.bar_stock_subject is None
    assert taxonomy.salle_maintenance_subject is not None
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)

    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière clignote à l'entrée du restaurant",
                structured_summary="Entrée restaurant, éclairage instable.",
                operational_module_key=RESTAURANT_MODULE_KEY,
                operational_domain_key=taxonomy.salle_domain.key,
                operational_subject_key=taxonomy.salle_maintenance_subject.key,
                operational_unit_key=None,
                aggregate_into_signal_id=None,
            ),
            PipelineCandidateOutput(
                title="Rupture de sirop mojito au bar",
                structured_summary="Bar, sirop mojito manquant.",
                operational_module_key=RESTAURANT_MODULE_KEY,
                operational_domain_key=taxonomy.bar_domain.key,
                operational_subject_key=RESTAURANT_BAR_STOCK_SUBJECT_KEY,
                operational_unit_key=None,
                aggregate_into_signal_id=None,
            ),
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output)

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    signal = Signal.objects.get()
    assert signal.operational_subject.key == RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY
    assert CandidateSignal.objects.filter(
        observation=observation,
        outcome=CandidateSignal.Outcome.REJECTED,
    ).exists()
    assert not Signal.objects.filter(
        operational_subject__key=RESTAURANT_BAR_STOCK_SUBJECT_KEY,
    ).exists()


def test_golden_incomplete_taxonomy_rejects_lighting_candidate():
    membership = build_membership()
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(
        membership.establishment,
        include_salle_maintenance=False,
    )
    assert taxonomy.salle_maintenance_subject is None
    assert taxonomy.bar_stock_subject is not None
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)

    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière clignote à l'entrée du restaurant",
                structured_summary="Entrée restaurant, éclairage instable.",
                operational_module_key=RESTAURANT_MODULE_KEY,
                operational_domain_key=taxonomy.salle_domain.key,
                operational_subject_key=RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY,
                operational_unit_key=None,
                aggregate_into_signal_id=None,
            ),
            PipelineCandidateOutput(
                title="Rupture de sirop mojito au bar",
                structured_summary="Bar, sirop mojito manquant.",
                operational_module_key=RESTAURANT_MODULE_KEY,
                operational_domain_key=taxonomy.bar_domain.key,
                operational_subject_key=taxonomy.bar_stock_subject.key,
                operational_unit_key=None,
                aggregate_into_signal_id=None,
            ),
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output)

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    signal = Signal.objects.get()
    assert signal.operational_subject.key == RESTAURANT_BAR_STOCK_SUBJECT_KEY
    assert CandidateSignal.objects.filter(
        observation=observation,
        outcome=CandidateSignal.Outcome.REJECTED,
    ).exists()
    assert not Signal.objects.filter(
        operational_subject__key=RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY,
    ).exists()


def test_golden_invented_taxonomy_key_does_not_create_signal():
    membership = build_membership()
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)

    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière entrée",
                structured_summary="Entrée restaurant.",
                operational_module_key=RESTAURANT_MODULE_KEY,
                operational_domain_key=taxonomy.salle_domain.key,
                operational_subject_key=taxonomy.salle_maintenance_subject.key,
                operational_unit_key=None,
                aggregate_into_signal_id=None,
            ),
            PipelineCandidateOutput(
                title="Stock inventé",
                structured_summary="Bar.",
                operational_module_key="invented_module",
                operational_domain_key="invented__domain",
                operational_subject_key="invented__domain__subject",
                operational_unit_key=None,
                aggregate_into_signal_id=None,
            ),
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output)

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.count() == 1
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.REJECTED).count() == 1
