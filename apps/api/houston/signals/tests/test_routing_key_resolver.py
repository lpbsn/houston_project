from __future__ import annotations

import pytest

from houston.ai.observation_pipeline_schema import PipelineCandidateOutput
from houston.establishments.business_unit_domain_service import _create_business_unit_core
from houston.establishments.models import CatalogBusinessUnit
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.exceptions import SignalValidationError
from houston.signals.services import resolve_taxonomy_from_candidate
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

    resolved_food = resolve_taxonomy_from_candidate(
        establishment_id=establishment.id,
        candidate=_candidate(
            affected_business_unit_routing_key=food_court.routing_key,
            responsible_business_unit_routing_key=food_court.routing_key,
            activity_subject_routing_key=food_subject.routing_key,
        ),
    )
    resolved_rooftop = resolve_taxonomy_from_candidate(
        establishment_id=establishment.id,
        candidate=_candidate(
            affected_business_unit_routing_key=rooftop.routing_key,
            responsible_business_unit_routing_key=rooftop.routing_key,
            activity_subject_routing_key=rooftop_subject.routing_key,
        ),
    )

    assert resolved_food.affected_business_unit.id == food_court.id
    assert resolved_rooftop.affected_business_unit.id == rooftop.id


def test_activity_subject_from_sibling_business_unit_is_rejected():
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

    with pytest.raises(SignalValidationError) as exc_info:
        resolve_taxonomy_from_candidate(
            establishment_id=establishment.id,
            candidate=_candidate(
                affected_business_unit_routing_key=rooftop.routing_key,
                responsible_business_unit_routing_key=rooftop.routing_key,
                activity_subject_routing_key=food_subject.routing_key,
            ),
        )

    assert exc_info.value.code == "activity_subject_under_other_business_unit"


def test_unknown_activity_subject_routing_key_is_rejected():
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )

    with pytest.raises(SignalValidationError) as exc_info:
        resolve_taxonomy_from_candidate(
            establishment_id=establishment.id,
            candidate=_candidate(
                affected_business_unit_routing_key=hotel.routing_key,
                responsible_business_unit_routing_key=hotel.routing_key,
                activity_subject_routing_key="custom--missing--0123456789abcdef",
            ),
        )

    assert exc_info.value.code == "unknown_activity_subject_routing_key"


def test_inactive_responsible_business_unit_rejects_candidate():
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
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

    with pytest.raises(SignalValidationError) as exc_info:
        resolve_taxonomy_from_candidate(
            establishment_id=establishment.id,
            candidate=_candidate(
                affected_business_unit_routing_key=hotel.routing_key,
                responsible_business_unit_routing_key=maintenance.routing_key,
                activity_subject_routing_key=subject.routing_key,
            ),
        )

    assert exc_info.value.code == "unknown_responsible_business_unit_routing_key"


def test_inactive_activity_subject_rejects_candidate():
    membership = build_membership()
    establishment = membership.establishment
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    subject.active = False
    subject.save(update_fields=["active", "updated_at"])

    with pytest.raises(SignalValidationError) as exc_info:
        resolve_taxonomy_from_candidate(
            establishment_id=establishment.id,
            candidate=_candidate(
                affected_business_unit_routing_key=hotel.routing_key,
                responsible_business_unit_routing_key=hotel.routing_key,
                activity_subject_routing_key=subject.routing_key,
            ),
        )

    assert exc_info.value.code == "unknown_activity_subject_routing_key"


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

    resolved = resolve_taxonomy_from_candidate(
        establishment_id=establishment.id,
        candidate=_candidate(
            affected_business_unit_routing_key=food_court.routing_key,
            responsible_business_unit_routing_key=food_court.routing_key,
            activity_subject_routing_key=food_subject.routing_key,
        ),
    )
    assert resolved.activity_subject.id == food_subject.id
