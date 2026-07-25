from __future__ import annotations

import pytest

from houston.ai.observation_pipeline_schema import PipelineCandidateOutput
from houston.establishments.business_unit_domain_service import _create_business_unit_core
from houston.establishments.models import CatalogBusinessUnit
from houston.establishments.taxonomy_snapshot import build_routing_taxonomy
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.models import Signal
from houston.signals.routing_resolver import (
    resolve_candidate_routing,
    routing_proposal_from_pipeline_candidate,
)
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def _candidate(**kwargs) -> PipelineCandidateOutput:
    base = {
        "title": "Issue",
        "structured_summary": "Structured summary for test.",
        "issue_focus": "focus",
        "canonical_object": "object",
        "signal_kind": "actionable",
        "expected_action": "inspect",
        "information_type": None,
        "operational_unit_key": None,
        "location_text": None,
    }
    base.update(kwargs)
    return PipelineCandidateOutput(**base)


def _resolve(*, establishment_id, candidate: PipelineCandidateOutput):
    taxonomy = build_routing_taxonomy(establishment_id=establishment_id)
    return resolve_candidate_routing(
        establishment_id=establishment_id,
        proposal=routing_proposal_from_pipeline_candidate(candidate),
        routing_taxonomy=taxonomy,
    )


def _restaurant_catalog() -> CatalogBusinessUnit:
    catalog, _ = CatalogBusinessUnit.objects.get_or_create(
        key="restaurant",
        defaults={
            "label": "Restaurant",
            "description": "",
            "unit_type": "dedicated",
            "active": True,
            "sort_order": 0,
        },
    )
    return catalog


def test_ai_can_distinguish_food_court_and_rooftop_routing_keys():
    membership = build_membership()
    establishment = membership.establishment
    restaurant = _restaurant_catalog()
    food_court = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
    )
    rooftop = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Rooftop",
    )
    food_subject = create_activity_subject(
        establishment=establishment,
        business_unit=food_court,
        label="Stock",
    )
    rooftop_subject = create_activity_subject(
        establishment=establishment,
        business_unit=rooftop,
        label="Stock",
    )

    assert food_court.routing_key != rooftop.routing_key

    resolved_food = _resolve(
        establishment_id=establishment.id,
        candidate=_candidate(
            affected_business_unit_routing_key=food_court.routing_key,
            responsible_business_unit_routing_key=food_court.routing_key,
            activity_subject_routing_key=food_subject.routing_key,
        ),
    )
    resolved_rooftop = _resolve(
        establishment_id=establishment.id,
        candidate=_candidate(
            affected_business_unit_routing_key=rooftop.routing_key,
            responsible_business_unit_routing_key=rooftop.routing_key,
            activity_subject_routing_key=rooftop_subject.routing_key,
        ),
    )

    assert resolved_food.affected_business_unit.id == food_court.id
    assert resolved_rooftop.affected_business_unit.id == rooftop.id
    assert resolved_food.routing_status == Signal.RoutingStatus.RESOLVED
    assert resolved_rooftop.routing_status == Signal.RoutingStatus.RESOLVED


def test_activity_subject_from_sibling_business_unit_derives_responsible():
    membership = build_membership()
    establishment = membership.establishment
    restaurant = _restaurant_catalog()
    food_court = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
    )
    rooftop = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Rooftop",
    )
    food_subject = create_activity_subject(
        establishment=establishment,
        business_unit=food_court,
        label="Stock",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=rooftop,
        label="Service",
    )

    resolution = _resolve(
        establishment_id=establishment.id,
        candidate=_candidate(
            affected_business_unit_routing_key=rooftop.routing_key,
            responsible_business_unit_routing_key=rooftop.routing_key,
            activity_subject_routing_key=food_subject.routing_key,
        ),
    )

    assert resolution.activity_subject is not None
    assert resolution.activity_subject.id == food_subject.id
    assert resolution.responsible_business_unit is not None
    assert resolution.responsible_business_unit.id == food_court.id
    assert resolution.affected_business_unit is not None
    assert resolution.affected_business_unit.id == rooftop.id
    assert resolution.routing_status == Signal.RoutingStatus.RESOLVED
    assert resolution.resolution_audit["responsible"]["source"] == "responsible_corrected"


def test_unknown_activity_subject_routing_key_keeps_partial():
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )

    resolution = _resolve(
        establishment_id=establishment.id,
        candidate=_candidate(
            affected_business_unit_routing_key=hotel.routing_key,
            responsible_business_unit_routing_key=hotel.routing_key,
            activity_subject_routing_key="custom--missing--0123456789abcdef",
        ),
    )

    assert resolution.affected_business_unit is not None
    assert resolution.affected_business_unit.id == hotel.id
    assert resolution.responsible_business_unit is not None
    assert resolution.responsible_business_unit.id == hotel.id
    assert resolution.activity_subject is None
    assert resolution.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert resolution.resolution_audit["subject"]["source"] == "invalid_key"


def test_inactive_responsible_business_unit_nulls_dimension():
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Housekeeping",
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
        label="Climatisation",
    )
    maintenance.active = False
    maintenance.save(update_fields=["active", "updated_at"])

    resolution = _resolve(
        establishment_id=establishment.id,
        candidate=_candidate(
            affected_business_unit_routing_key=hotel.routing_key,
            responsible_business_unit_routing_key=maintenance.routing_key,
            activity_subject_routing_key=subject.routing_key,
        ),
    )

    assert resolution.affected_business_unit is not None
    assert resolution.affected_business_unit.id == hotel.id
    assert resolution.activity_subject is None
    assert resolution.responsible_business_unit is None
    assert resolution.routing_status == Signal.RoutingStatus.UNASSIGNED


def test_inactive_activity_subject_nulls_subject_dimension():
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Other",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    subject.active = False
    subject.save(update_fields=["active", "updated_at"])

    resolution = _resolve(
        establishment_id=establishment.id,
        candidate=_candidate(
            affected_business_unit_routing_key=hotel.routing_key,
            responsible_business_unit_routing_key=hotel.routing_key,
            activity_subject_routing_key=subject.routing_key,
        ),
    )

    assert resolution.affected_business_unit is not None
    assert resolution.affected_business_unit.id == hotel.id
    assert resolution.responsible_business_unit is not None
    assert resolution.responsible_business_unit.id == hotel.id
    assert resolution.activity_subject is None
    assert resolution.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert resolution.resolution_audit["subject"]["source"] == "invalid_key"


def test_activity_subject_resolution_does_not_raise_multiple_objects_returned():
    membership = build_membership()
    establishment = membership.establishment
    restaurant = _restaurant_catalog()
    food_court = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
    )
    rooftop = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Rooftop",
    )
    food_subject = create_activity_subject(
        establishment=establishment,
        business_unit=food_court,
        label="Stock",
    )
    rooftop_subject = create_activity_subject(
        establishment=establishment,
        business_unit=rooftop,
        label="Stock",
    )
    assert food_subject.normalized_name == rooftop_subject.normalized_name

    resolution = _resolve(
        establishment_id=establishment.id,
        candidate=_candidate(
            affected_business_unit_routing_key=food_court.routing_key,
            responsible_business_unit_routing_key=food_court.routing_key,
            activity_subject_routing_key=food_subject.routing_key,
        ),
    )
    assert resolution.activity_subject.id == food_subject.id
