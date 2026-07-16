from __future__ import annotations

import pytest

from houston.establishments.business_unit_identity import normalize_generic_activity_subject_name
from houston.establishments.models import ActivitySubject, CatalogActivitySubject
from houston.establishments.taxonomy_snapshot import (
    build_establishment_taxonomy_snapshot,
    establishment_has_active_business_units,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
    create_establishment,
)
from houston.testing.query_baseline import capture_queries

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
def test_snapshot_includes_generic_and_instance_descriptions():
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

    snapshot = build_establishment_taxonomy_snapshot(establishment_id=establishment.id)

    assert len(snapshot["business_units"]) == 1
    unit = snapshot["business_units"][0]
    assert unit["routing_key"] == hotel.routing_key
    assert unit["specific_name"] == hotel.specific_name
    assert unit["generic_label"] == hotel.catalog_business_unit.label
    assert unit["generic_description"] == "Pôle hébergement catalogue."
    assert unit["instance_description"] == "Zone hébergement locale."
    assert unit["unit_type"] == hotel.catalog_business_unit.unit_type


@pytest.mark.django_db
def test_snapshot_subject_includes_label_description_source():
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
        key="hotel__proprete_test_snapshot",
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

    snapshot = build_establishment_taxonomy_snapshot(establishment_id=establishment.id)
    unit_subjects = snapshot["business_units"][0]["activity_subjects"]
    subjects = {item["routing_key"]: item for item in unit_subjects}

    assert subjects[free_subject.routing_key] == {
        "routing_key": free_subject.routing_key,
        "label": "Terrasse VIP",
        "description": "Zone réservée.",
        "source": "free",
    }
    assert subjects[generic_subject.routing_key] == {
        "routing_key": catalog_subject.key,
        "label": "Propreté catalogue",
        "description": "Description catalogue sujet.",
        "source": "catalog",
    }


@pytest.mark.django_db
def test_snapshot_excludes_inactive_business_units_and_subjects():
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
def test_snapshot_empty_when_no_active_business_units():
    establishment = create_establishment()

    snapshot = build_establishment_taxonomy_snapshot(establishment_id=establishment.id)

    assert snapshot["business_units"] == []
    assert establishment_has_active_business_units(establishment_id=establishment.id) is False


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

    inactive.active = True
    inactive.save(update_fields=["active", "updated_at"])
    assert establishment_has_active_business_units(establishment_id=establishment.id) is True


def test_snapshot_query_count_flat_across_business_units():
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
        build_establishment_taxonomy_snapshot(establishment_id=one_bu_establishment.id)
    with capture_queries() as three_bu_context:
        build_establishment_taxonomy_snapshot(establishment_id=three_bu_establishment.id)

    assert len(one_bu_context.captured_queries) == len(three_bu_context.captured_queries)
