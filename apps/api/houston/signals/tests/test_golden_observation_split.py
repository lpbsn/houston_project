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
    assert taxonomy.maintenance is not None
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)

    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière clignote à l'entrée du restaurant",
                structured_summary="Entrée restaurant, éclairage instable.",
                issue_focus="lumière entrée restaurant",
                canonical_object="object",
                signal_kind="actionable",
                expected_action="inspect",
                information_type=None,
                affected_business_unit_routing_key=taxonomy.restaurant.routing_key,
                responsible_business_unit_routing_key=taxonomy.maintenance.routing_key,
                activity_subject_routing_key=taxonomy.lighting_subject.routing_key,
                operational_unit_key=None,
                location_text="Entrée restaurant",
            ),
            PipelineCandidateOutput(
                title="Rupture de sirop mojito au bar",
                structured_summary="Bar, sirop mojito manquant.",
                issue_focus="sirop mojito",
                canonical_object="object",
                signal_kind="actionable",
                expected_action="inspect",
                information_type=None,
                affected_business_unit_routing_key=taxonomy.bar.routing_key,
                responsible_business_unit_routing_key=taxonomy.bar.routing_key,
                activity_subject_routing_key="custom--stock--missing00000000",
                operational_unit_key=None,
                location_text="Bar",
            ),
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 2
    lighting = Signal.objects.get(activity_subject=taxonomy.lighting_subject)
    # Restaurant has no subjects → not in routing_taxonomy → affected null → unassigned.
    assert lighting.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert lighting.responsible_business_unit_id == taxonomy.maintenance.id
    bar_partial = Signal.objects.exclude(id=lighting.id).get()
    assert bar_partial.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert bar_partial.activity_subject is None
    assert CandidateSignal.objects.filter(
        observation=observation,
        outcome=CandidateSignal.Outcome.CREATED_SIGNAL,
    ).count() == 2


def test_golden_incomplete_taxonomy_rejects_lighting_candidate():
    membership = build_membership()
    taxonomy = create_restaurant_v3_taxonomy(
        membership.establishment,
        include_lighting_subject=False,
    )
    assert taxonomy.lighting_subject is None
    assert taxonomy.stock_subject is not None
    assert taxonomy.maintenance is not None
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)

    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière clignote à l'entrée du restaurant",
                structured_summary="Entrée restaurant, éclairage instable.",
                issue_focus="lumière entrée restaurant",
                canonical_object="object",
                signal_kind="actionable",
                expected_action="inspect",
                information_type=None,
                affected_business_unit_routing_key=taxonomy.restaurant.routing_key,
                responsible_business_unit_routing_key=taxonomy.maintenance.routing_key,
                activity_subject_routing_key="custom--electricite--missing000000",
                operational_unit_key=None,
                location_text="Entrée restaurant",
            ),
            PipelineCandidateOutput(
                title="Rupture de sirop mojito au bar",
                structured_summary="Bar, sirop mojito manquant.",
                issue_focus="sirop mojito",
                canonical_object="object",
                signal_kind="actionable",
                expected_action="inspect",
                information_type=None,
                affected_business_unit_routing_key=taxonomy.bar.routing_key,
                responsible_business_unit_routing_key=taxonomy.bar.routing_key,
                activity_subject_routing_key=taxonomy.stock_subject.routing_key,
                operational_unit_key=None,
                location_text="Bar",
            ),
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 2
    bar_signal = Signal.objects.get(
        affected_business_unit__catalog_business_unit__key="bar"
    )
    assert bar_signal.routing_status == Signal.RoutingStatus.RESOLVED
    lighting_partial = Signal.objects.exclude(id=bar_signal.id).get()
    assert lighting_partial.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert lighting_partial.activity_subject is None
    # Maintenance without lighting subject is absent from routing_taxonomy.
    assert lighting_partial.responsible_business_unit is None
    assert CandidateSignal.objects.filter(
        observation=observation,
        outcome=CandidateSignal.Outcome.CREATED_SIGNAL,
    ).count() == 2


def test_golden_invented_taxonomy_key_does_not_create_signal():
    membership = build_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)

    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière entrée",
                structured_summary="Entrée restaurant.",
                issue_focus="lumière entrée restaurant",
                canonical_object="object",
                signal_kind="actionable",
                expected_action="inspect",
                information_type=None,
                affected_business_unit_routing_key=taxonomy.restaurant.routing_key,
                responsible_business_unit_routing_key=taxonomy.maintenance.routing_key,
                activity_subject_routing_key=taxonomy.lighting_subject.routing_key,
                operational_unit_key=None,
                location_text=None,
            ),
            PipelineCandidateOutput(
                title="Stock inventé",
                structured_summary="Bar.",
                issue_focus="stock inventé",
                canonical_object="object",
                signal_kind="actionable",
                expected_action="inspect",
                information_type=None,
                affected_business_unit_routing_key="invented--missing--0000000000000000",
                responsible_business_unit_routing_key="invented--missing--0000000000000000",
                activity_subject_routing_key="invented_subject",
                operational_unit_key=None,
                location_text=None,
            ),
        ],
    )
    outcome = apply_pipeline_output(observation=observation, output=output).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.count() == 2
    invented = Signal.objects.get(issue_focus="stock inventé")
    assert invented.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert invented.affected_business_unit is None
    assert invented.responsible_business_unit is None
    assert invented.activity_subject is None
    assert CandidateSignal.objects.filter(
        outcome=CandidateSignal.Outcome.CREATED_SIGNAL
    ).count() == 2
