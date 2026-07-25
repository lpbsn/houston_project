from __future__ import annotations

import pytest

from houston.ai.observation_pipeline import build_pipeline_input
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
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import apply_pipeline_output
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def _v3_candidate(**kwargs) -> PipelineCandidateOutput:
    base = {
        "title": "Issue",
        "structured_summary": "Structured summary for test.",
        "issue_focus": "climatisation",
        "operational_unit_key": None,
        "location_text": None,
        "aggregate_into_signal_id": None,
    }
    base.update(kwargs)
    return PipelineCandidateOutput(**base)


def _apply_single(*, observation, candidate: PipelineCandidateOutput):
    return apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[candidate],
        ),
    )


def test_g1_clim_hs_chambre_104_transversal_maintenance():
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
        description="Chambres, couloirs et expérience hébergement.",
    )
    maintenance = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        description="Électricité, plomberie, CVC.",
        unit_type="transversal",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=maintenance,
        label="Climatisation",
    )
    observation = create_observation(
        membership=membership,
        text="Clim HS chambre 104",
    )

    _apply_single(
        observation=observation,
        candidate=_v3_candidate(
            title="Climatisation en panne chambre 104",
            structured_summary="La climatisation ne fonctionne plus en chambre 104.",
            affected_business_unit_routing_key=hotel.routing_key,
            responsible_business_unit_routing_key=maintenance.routing_key,
            activity_subject_routing_key=subject.routing_key,
            location_text="chambre 104",
        ),
    )

    signal = Signal.objects.get()
    assert signal.affected_business_unit_id == hotel.id
    assert signal.responsible_business_unit_id == maintenance.id
    assert signal.activity_subject.normalized_name == "climatisation"
    assert signal.location_text == "chambre 104"


def test_g2_lumiere_hs_restaurant_maintenance_transversal():
    membership = build_membership()
    establishment = membership.establishment
    restaurant = create_business_unit(
        establishment=establishment,
        key="restaurant",
        label="Restaurant",
    )
    maintenance = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        unit_type="transversal",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=maintenance,
        label="Électricité",
    )
    observation = create_observation(
        membership=membership,
        text="Lumière HS au restaurant",
    )

    _apply_single(
        observation=observation,
        candidate=_v3_candidate(
            affected_business_unit_routing_key=restaurant.routing_key,
            responsible_business_unit_routing_key=maintenance.routing_key,
            activity_subject_routing_key=subject.routing_key,
            location_text="restaurant",
        ),
    )

    signal = Signal.objects.get()
    assert signal.affected_business_unit_id == restaurant.id
    assert signal.responsible_business_unit_id == maintenance.id


def test_g3_lumiere_hs_restaurant_local_maintenance_subject():
    membership = build_membership()
    establishment = membership.establishment
    restaurant = create_business_unit(
        establishment=establishment,
        key="restaurant",
        label="Restaurant",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=restaurant,
        label="Maintenance",
    )
    observation = create_observation(
        membership=membership,
        text="Lumière HS au restaurant",
    )

    _apply_single(
        observation=observation,
        candidate=_v3_candidate(
            affected_business_unit_routing_key=restaurant.routing_key,
            responsible_business_unit_routing_key=restaurant.routing_key,
            activity_subject_routing_key=subject.routing_key,
            location_text="restaurant",
        ),
    )

    signal = Signal.objects.get()
    assert signal.affected_business_unit_id == restaurant.id
    assert signal.responsible_business_unit_id == restaurant.id


def test_g4_sale_chambre_104_hotel_proprete():
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Propreté chambre",
    )
    observation = create_observation(
        membership=membership,
        text="C'est sale dans la chambre 104",
    )

    _apply_single(
        observation=observation,
        candidate=_v3_candidate(
            affected_business_unit_routing_key=hotel.routing_key,
            responsible_business_unit_routing_key=hotel.routing_key,
            activity_subject_routing_key=subject.routing_key,
            location_text="chambre 104",
        ),
    )

    signal = Signal.objects.get()
    assert signal.affected_business_unit_id == hotel.id
    assert signal.responsible_business_unit_id == hotel.id
    assert signal.activity_subject.normalized_name == "proprete_chambre"


def test_g5_stock_au_bar():
    membership = build_membership()
    establishment = membership.establishment
    bar = create_business_unit(
        establishment=establishment,
        key="bar",
        label="Bar",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=bar,
        label="Stock",
    )
    observation = create_observation(
        membership=membership,
        text="Problème de stock au bar",
    )

    _apply_single(
        observation=observation,
        candidate=_v3_candidate(
            affected_business_unit_routing_key=bar.routing_key,
            responsible_business_unit_routing_key=bar.routing_key,
            activity_subject_routing_key=subject.routing_key,
            location_text="bar",
        ),
    )

    signal = Signal.objects.get()
    assert signal.affected_business_unit_id == bar.id
    assert signal.responsible_business_unit_id == bar.id
    assert signal.activity_subject.normalized_name == "stock"


def test_g6_subject_hors_responsible_rejected():
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hôtel")
    maintenance = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        unit_type="transversal",
    )
    hotel_subject = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Propreté chambre",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=maintenance,
        label="Climatisation",
    )
    observation = create_observation(membership=membership, text="Propreté chambre 104")

    outcome = _apply_single(
        observation=observation,
        candidate=_v3_candidate(
            affected_business_unit_routing_key=hotel.routing_key,
            responsible_business_unit_routing_key=maintenance.routing_key,
            activity_subject_routing_key=hotel_subject.routing_key,
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.NO_SIGNAL_CREATED
    assert Signal.objects.count() == 0
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.REJECTED).count() == 1


def test_g7_dedicated_different_from_affected_accepted():
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hôtel")
    restaurant = create_business_unit(
        establishment=establishment,
        key="restaurant",
        label="Restaurant",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=restaurant,
        label="Service",
    )
    observation = create_observation(membership=membership, text="Problème restaurant")

    outcome = _apply_single(
        observation=observation,
        candidate=_v3_candidate(
            affected_business_unit_routing_key=hotel.routing_key,
            responsible_business_unit_routing_key=restaurant.routing_key,
            activity_subject_routing_key=subject.routing_key,
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    signal = Signal.objects.get()
    assert signal.affected_business_unit_id == hotel.id
    assert signal.responsible_business_unit_id == restaurant.id
    assert signal.activity_subject_id == subject.id
    assert signal.routing_status == Signal.RoutingStatus.RESOLVED


def test_g8_business_unit_description_in_pipeline_input():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
        description="Regroupe chambres et couloirs.",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Propreté chambre",
    )
    observation = create_observation(membership=membership, text="Chambre sale")

    payload = build_pipeline_input(observation=observation)

    hotel_unit = payload["establishment_taxonomy"]["business_units"][0]
    assert hotel_unit["instance_description"] == "Regroupe chambres et couloirs."
    assert hotel_unit["routing_key"] == hotel.routing_key


def test_no_signal_created_when_candidates_empty():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[],
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.NO_SIGNAL_CREATED
