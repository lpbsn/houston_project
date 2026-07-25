from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from houston.establishments.business_unit_identity import normalize_generic_activity_subject_name
from houston.establishments.models import ActivitySubject, CatalogActivitySubject
from houston.establishments.taxonomy_snapshot import (
    build_active_business_units,
    build_establishment_taxonomy_snapshot,
    build_routing_taxonomy,
    establishment_has_active_business_units,
    establishment_has_any_active_business_unit,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
    create_establishment,
)
from houston.signals.catalog_capabilities import CATALOG_CAPABILITIES_VERSION
from houston.testing.query_baseline import capture_queries

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
def test_routing_taxonomy_includes_generic_and_instance_descriptions():
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
        description="Zone hébergement locale.",
        unit_type="dedicated",
    )
    hotel.catalog_business_unit.description = "Pôle hébergement catalogue."
    hotel.catalog_business_unit.save(update_fields=["description", "updated_at"])
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Ménage",
    )

    taxonomy = build_routing_taxonomy(establishment_id=establishment.id)

    assert len(taxonomy["business_units"]) == 1
    unit = taxonomy["business_units"][0]
    assert unit["routing_key"] == hotel.routing_key
    assert unit["specific_name"] == hotel.specific_name
    assert unit["generic_label"] == hotel.catalog_business_unit.label
    assert unit["generic_description"] == "Pôle hébergement catalogue."
    assert unit["instance_description"] == "Zone hébergement locale."
    assert unit["unit_type"] == hotel.catalog_business_unit.unit_type
    assert taxonomy["capabilities_version"] == CATALOG_CAPABILITIES_VERSION


@pytest.mark.django_db
def test_routing_taxonomy_subject_includes_catalog_key_and_capabilities():
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
    )
    free_subject = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Terrasse VIP",
        description="Zone réservée.",
    )
    catalog_subject = CatalogActivitySubject.objects.create(
        catalog_business_unit=hotel.catalog_business_unit,
        key="hotel__menage",
        label="Propreté catalogue",
        description="Description catalogue sujet.",
        active=True,
        sort_order=1,
    )
    generic_subject = ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=hotel,
        catalog_activity_subject=catalog_subject,
        normalized_name=normalize_generic_activity_subject_name(catalog_subject.label),
        label="",
        description="",
        routing_key=catalog_subject.key,
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )
    unknown_catalog = CatalogActivitySubject.objects.create(
        catalog_business_unit=hotel.catalog_business_unit,
        key="hotel__unknown_capability_subject",
        label="Inconnu",
        description="",
        active=True,
        sort_order=2,
    )
    unknown_subject = ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=hotel,
        catalog_activity_subject=unknown_catalog,
        normalized_name=normalize_generic_activity_subject_name(unknown_catalog.label),
        label="",
        description="",
        routing_key=unknown_catalog.key,
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )

    taxonomy = build_routing_taxonomy(establishment_id=establishment.id)
    subjects = {
        item["routing_key"]: item
        for item in taxonomy["business_units"][0]["activity_subjects"]
    }

    assert subjects[free_subject.routing_key]["source"] == "free"
    assert subjects[free_subject.routing_key]["capabilities"] == []
    assert subjects[free_subject.routing_key]["catalog_key"] is None
    assert subjects[generic_subject.routing_key]["source"] == "catalog"
    assert subjects[generic_subject.routing_key]["catalog_key"] == "hotel__menage"
    assert subjects[generic_subject.routing_key]["capabilities"]
    assert subjects[unknown_subject.routing_key]["capabilities"] == []


@pytest.mark.django_db
def test_active_includes_non_routable_absent_from_routing_taxonomy():
    establishment = create_establishment()
    create_business_unit(establishment=establishment, key="spa", label="Spa")
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hôtel")
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Ménage",
    )

    active = build_active_business_units(establishment_id=establishment.id)
    routing = build_routing_taxonomy(establishment_id=establishment.id)

    active_keys = {unit["catalog_key"] for unit in active}
    routing_keys = {unit["catalog_key"] for unit in routing["business_units"]}
    assert active_keys == {"spa", "hotel"}
    assert "spa" not in routing_keys
    assert "hotel" in routing_keys


@pytest.mark.django_db
def test_active_business_units_never_omits_active_pole():
    establishment = create_establishment()
    for key, label in (("a", "A"), ("b", "B"), ("c", "C")):
        create_business_unit(establishment=establishment, key=key, label=label)
    active = build_active_business_units(establishment_id=establishment.id)
    assert len(active) == 3


@pytest.mark.django_db
def test_active_business_units_tolerates_missing_catalog():
    establishment = create_establishment()
    unit = create_business_unit(establishment=establishment, key="hotel", label="Hôtel")
    # Defensive path: serialize as if catalog FK were missing (DB currently requires it).
    mock_unit = MagicMock()
    mock_unit.id = unit.id
    mock_unit.specific_name = unit.specific_name
    mock_unit.instance_description = unit.instance_description
    mock_unit.catalog_business_unit = None
    from houston.establishments import taxonomy_snapshot as module

    fields = module._catalog_fields_for_business_unit(unit=mock_unit)
    assert fields["catalog_key"] is None
    assert fields["generic_label"] is None
    assert fields["unit_type"] is None


@pytest.mark.django_db
def test_snapshot_wrapper_excludes_inactive_business_units_and_subjects():
    establishment = create_establishment()
    active_unit = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    inactive_unit = create_business_unit(
        establishment=establishment,
        key="bar",
        label="Bar",
    )
    inactive_unit.active = False
    inactive_unit.save(update_fields=["active", "updated_at"])

    create_activity_subject(
        establishment=establishment,
        business_unit=active_unit,
        label="Active subject",
    )
    inactive_subject = create_activity_subject(
        establishment=establishment,
        business_unit=active_unit,
        label="Inactive subject",
    )
    inactive_subject.active = False
    inactive_subject.save(update_fields=["active", "updated_at"])

    snapshot = build_establishment_taxonomy_snapshot(establishment_id=establishment.id)

    assert len(snapshot["business_units"]) == 1
    assert snapshot["business_units"][0]["routing_key"] == active_unit.routing_key
    assert len(snapshot["business_units"][0]["activity_subjects"]) == 1
    assert snapshot["business_units"][0]["activity_subjects"][0]["label"] == "Active subject"


@pytest.mark.django_db
def test_routing_taxonomy_empty_when_active_bu_has_no_subjects():
    establishment = create_establishment()
    create_business_unit(establishment=establishment, key="hotel", label="Hotel")

    taxonomy = build_routing_taxonomy(establishment_id=establishment.id)
    active = build_active_business_units(establishment_id=establishment.id)

    assert len(active) == 1
    assert taxonomy["business_units"] == []
    assert establishment_has_active_business_units(establishment_id=establishment.id) is True


@pytest.mark.django_db
def test_establishment_has_active_business_units_requires_snapshot_ready_identity():
    establishment = create_establishment()
    inactive = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    inactive.active = False
    inactive.save(update_fields=["active", "updated_at"])

    assert establishment_has_active_business_units(establishment_id=establishment.id) is False
    assert establishment_has_any_active_business_unit(establishment_id=establishment.id) is False

    inactive.active = True
    inactive.save(update_fields=["active", "updated_at"])
    assert establishment_has_active_business_units(establishment_id=establishment.id) is True
    assert establishment_has_any_active_business_unit(establishment_id=establishment.id) is True


@pytest.mark.django_db
def test_establishment_has_any_active_business_unit_ignores_snapshot_ready_gate():
    establishment = create_establishment()
    assert establishment_has_any_active_business_unit(establishment_id=establishment.id) is False
    unit = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    assert establishment_has_any_active_business_unit(establishment_id=establishment.id) is True
    unit.active = False
    unit.save(update_fields=["active", "updated_at"])
    assert establishment_has_any_active_business_unit(establishment_id=establishment.id) is False


def test_routing_taxonomy_query_count_flat_across_business_units():
    one_bu_establishment = create_establishment(name="One BU")
    single_unit = create_business_unit(
        establishment=one_bu_establishment,
        key="hotel",
        label="Hotel",
    )
    create_activity_subject(
        establishment=one_bu_establishment,
        business_unit=single_unit,
        label="Maintenance",
    )

    three_bu_establishment = create_establishment(name="Three BU")
    for key, label in (("hotel", "Hotel"), ("bar", "Bar"), ("kitchen", "Kitchen")):
        unit = create_business_unit(
            establishment=three_bu_establishment,
            key=key,
            label=label,
        )
        create_activity_subject(
            establishment=three_bu_establishment,
            business_unit=unit,
            label=f"{label} subject",
        )

    with capture_queries() as one_bu_context:
        build_routing_taxonomy(establishment_id=one_bu_establishment.id)
    with capture_queries() as three_bu_context:
        build_routing_taxonomy(establishment_id=three_bu_establishment.id)

    assert len(one_bu_context.captured_queries) == len(three_bu_context.captured_queries)
