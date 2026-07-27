from __future__ import annotations

import pytest

from houston.ai.observation_pipeline import (
    _resolve_action_plan_business_unit_context,
    build_pipeline_input,
)
from houston.establishments.business_unit_identity import normalize_generic_activity_subject_name
from houston.establishments.models import ActivitySubject, BusinessUnit, CatalogActivitySubject
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
    create_membership_with_business_unit_scope,
)
from houston.signals.catalog_capabilities import CATALOG_CAPABILITIES_VERSION
from houston.signals.tests.conftest import create_observation
from houston.testing.action_plan_pipeline import create_action_plan_task_observation
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def test_dual_context_active_non_routable_spa_and_routable_hotel():
    membership = build_membership()
    create_business_unit(
        establishment=membership.establishment, key="spa", label="Spa"
    )
    hotel = create_business_unit(
        establishment=membership.establishment, key="hotel", label="Hôtel"
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Ménage",
    )
    observation = create_observation(membership=membership, text="Problème au spa")
    payload = build_pipeline_input(observation=observation)

    active_keys = {
        unit["catalog_key"]
        for unit in payload["establishment_context"]["active_business_units"]
    }
    routing_keys = {
        unit["catalog_key"] for unit in payload["routing_taxonomy"]["business_units"]
    }
    assert active_keys == {"spa", "hotel"}
    assert "spa" not in routing_keys
    assert "hotel" in routing_keys
    assert payload["routing_taxonomy"]["capabilities_version"] == CATALOG_CAPABILITIES_VERSION


def test_author_scope_omitted_from_llm_pipeline_input():
    membership = build_membership()
    rooftop = create_business_unit(
        establishment=membership.establishment, key="rooftop", label="Rooftop"
    )
    food = create_business_unit(
        establishment=membership.establishment, key="food_court", label="Food Court"
    )
    create_activity_subject(
        establishment=membership.establishment, business_unit=rooftop, label="Service"
    )
    create_activity_subject(
        establishment=membership.establishment, business_unit=food, label="Service"
    )
    create_membership_with_business_unit_scope(membership=membership, business_unit=rooftop)
    create_membership_with_business_unit_scope(membership=membership, business_unit=food)
    observation = create_observation(membership=membership, text="Multi rattachements.")
    payload = build_pipeline_input(observation=observation)
    assert "submission_context" not in payload
    assert "author_scope_business_unit_routing_keys" not in payload


def test_action_plan_task_preferred_when_both_routable():
    membership = build_membership()
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.TRANSVERSAL,
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label="Équipements",
    )
    observation = create_action_plan_task_observation(
        membership=membership,
        task_business_unit=maintenance,
        pilot_business_unit=maintenance,
    )
    ctx = build_pipeline_input(observation=observation)["action_plan_context"]
    assert ctx["context_business_unit_source"] == "task"
    assert ctx["business_unit_routing_key"] == maintenance.routing_key


def test_action_plan_falls_back_to_pilot_entirely():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment, key="hotel", label="Hôtel"
    )
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.TRANSVERSAL,
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label="Équipements",
    )
    observation = create_action_plan_task_observation(
        membership=membership,
        task_business_unit=hotel,
        pilot_business_unit=maintenance,
    )
    ctx = build_pipeline_input(observation=observation)["action_plan_context"]
    assert ctx["context_business_unit_source"] == "pilot"
    assert ctx["business_unit_routing_key"] == maintenance.routing_key
    assert ctx["business_unit_specific_name"] == maintenance.specific_name


def test_action_plan_non_routable_keeps_name_and_source():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment, key="hotel", label="Hôtel"
    )
    spa = create_business_unit(
        establishment=membership.establishment, key="spa", label="Spa"
    )
    observation = create_action_plan_task_observation(
        membership=membership,
        task_business_unit=hotel,
        pilot_business_unit=spa,
    )
    ctx = build_pipeline_input(observation=observation)["action_plan_context"]
    assert ctx["business_unit_routing_key"] is None
    assert ctx["business_unit_specific_name"] == hotel.specific_name
    assert ctx["context_business_unit_source"] == "task"


def test_action_plan_no_business_units_all_null():
    key, name, source = _resolve_action_plan_business_unit_context(
        task_business_unit=None,
        pilot_business_unit=None,
        routable_keys=set(),
    )
    assert key is None
    assert name is None
    assert source is None


def test_custom_subject_has_empty_capabilities_catalog_known_has_seed():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment, key="hotel", label="Hôtel"
    )
    catalog = CatalogActivitySubject.objects.create(
        catalog_business_unit=hotel.catalog_business_unit,
        key="hotel__menage",
        label="Ménage",
        description="Propreté",
        active=True,
        sort_order=1,
    )
    ActivitySubject.objects.create(
        establishment=membership.establishment,
        business_unit=hotel,
        catalog_activity_subject=catalog,
        normalized_name=normalize_generic_activity_subject_name(catalog.label),
        label="",
        description="",
        routing_key=catalog.key,
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Machine à café",
    )
    observation = create_observation(membership=membership, text="Machine à café en panne")
    subjects = {
        item["routing_key"]: item
        for item in build_pipeline_input(observation=observation)["routing_taxonomy"][
            "business_units"
        ][0]["activity_subjects"]
    }
    assert subjects[catalog.key]["capabilities"]
    free = next(item for item in subjects.values() if item["source"] == "free")
    assert free["capabilities"] == []
    assert free["catalog_key"] is None
