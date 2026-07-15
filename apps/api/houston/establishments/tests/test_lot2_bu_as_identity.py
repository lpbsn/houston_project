from __future__ import annotations

import uuid

import pytest
from django.db import IntegrityError, connection
from django.db.migrations.executor import MigrationExecutor

from houston.establishments.business_unit_identity import (
    build_business_unit_routing_key,
    derive_activity_subject_establishment,
    normalize_business_unit_specific_name,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogBusinessUnit,
    Establishment,
)
from houston.establishments.taxonomy_normalization import slugify_label
from houston.organizations.models import Organization


def _create_establishment() -> Establishment:
    org = Organization.objects.create(name="Org")
    return Establishment.objects.create(organization=org, name="Est")


def _create_legacy_business_unit(
    *,
    establishment: Establishment,
    key: str = "hotel",
    label: str = "Hotel",
) -> BusinessUnit:
    return BusinessUnit.objects.create(
        establishment=establishment,
        key=key,
        label=label,
        description="Legacy BU description",
        unit_type=BusinessUnit.UnitType.DEDICATED,
    )


def test_normalize_business_unit_specific_name():
    assert normalize_business_unit_specific_name("Food Court") == slugify_label("Food Court")


def test_build_business_unit_routing_key_format():
    catalog_key = "restaurant"
    food_court_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    rooftop_id = uuid.UUID("71c981d6-4e82-4f13-a001-446655440001")

    food_court_key = build_business_unit_routing_key(
        business_unit_id=food_court_id,
        catalog_key=catalog_key,
        specific_name="Food Court",
    )
    rooftop_key = build_business_unit_routing_key(
        business_unit_id=rooftop_id,
        catalog_key=catalog_key,
        specific_name="Rooftop",
    )

    assert food_court_key == "restaurant--food-court--550e8400e29b41d4"
    assert rooftop_key == "restaurant--rooftop--71c981d64e824f13"
    assert food_court_key != rooftop_key


@pytest.mark.django_db
def test_business_unit_partial_unique_normalized_specific_name():
    establishment = _create_establishment()
    _create_legacy_business_unit(establishment=establishment, key="hotel_a")
    BusinessUnit.objects.create(
        establishment=establishment,
        key="hotel_b",
        label="Hotel B",
        unit_type=BusinessUnit.UnitType.DEDICATED,
        normalized_specific_name="food_court",
    )
    with pytest.raises(IntegrityError):
        BusinessUnit.objects.create(
            establishment=establishment,
            key="hotel_c",
            label="Hotel C",
            unit_type=BusinessUnit.UnitType.DEDICATED,
            normalized_specific_name="food_court",
        )


@pytest.mark.django_db
def test_business_unit_partial_unique_allows_multiple_null_normalized_specific_name():
    establishment = _create_establishment()
    _create_legacy_business_unit(establishment=establishment, key="hotel_a")
    BusinessUnit.objects.create(
        establishment=establishment,
        key="hotel_b",
        label="Hotel B",
        unit_type=BusinessUnit.UnitType.DEDICATED,
    )
    assert BusinessUnit.objects.filter(establishment=establishment).count() == 2


@pytest.mark.django_db
def test_business_unit_partial_unique_routing_key(imported_catalog):
    establishment = _create_establishment()
    catalog = CatalogBusinessUnit.objects.get(key="hotel")
    bu_id = uuid.uuid4()
    routing_key = build_business_unit_routing_key(
        business_unit_id=bu_id,
        catalog_key=catalog.key,
        specific_name="Food Court",
    )
    BusinessUnit.objects.create(
        id=bu_id,
        establishment=establishment,
        key="hotel_a",
        label="Hotel A",
        unit_type=BusinessUnit.UnitType.DEDICATED,
        catalog_business_unit=catalog,
        routing_key=routing_key,
    )
    with pytest.raises(IntegrityError):
        BusinessUnit.objects.create(
            establishment=establishment,
            key="hotel_b",
            label="Hotel B",
            unit_type=BusinessUnit.UnitType.DEDICATED,
            catalog_business_unit=catalog,
            routing_key=routing_key,
        )


@pytest.mark.django_db
def test_activity_subject_routing_key_partial_unique():
    establishment = _create_establishment()
    business_unit = _create_legacy_business_unit(establishment=establishment)
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name="stock",
        label="Stock",
        routing_key="hotel__gestion_des_stocks",
    )
    with pytest.raises(IntegrityError):
        ActivitySubject.objects.create(
            establishment=establishment,
            business_unit=business_unit,
            normalized_name="stock_duplicate",
            label="Stock duplicate",
            routing_key="hotel__gestion_des_stocks",
        )


@pytest.mark.django_db
def test_activity_subject_routing_key_partial_unique_allows_multiple_null():
    establishment = _create_establishment()
    business_unit = _create_legacy_business_unit(establishment=establishment)
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name="stock",
        label="Stock",
    )
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name="maintenance",
        label="Maintenance",
    )


@pytest.mark.django_db
def test_activity_subject_normalized_name_accepts_255_chars():
    establishment = _create_establishment()
    business_unit = _create_legacy_business_unit(establishment=establishment)
    normalized_name = "a" * 255
    subject = ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name=normalized_name,
        label="Long normalized name",
    )
    subject.refresh_from_db()
    assert subject.normalized_name == normalized_name
    assert len(subject.normalized_name) == 255


@pytest.mark.django_db
def test_derive_activity_subject_establishment_sets_establishment_id():
    establishment = _create_establishment()
    business_unit = _create_legacy_business_unit(establishment=establishment)
    other_establishment = _create_establishment()
    subject = ActivitySubject(
        establishment=other_establishment,
        business_unit=business_unit,
        normalized_name="stock",
        label="Stock",
    )
    derive_activity_subject_establishment(subject)
    assert subject.establishment_id == business_unit.establishment_id


@pytest.mark.django_db
def test_bulk_create_activity_subject_with_explicit_establishment_derivation():
    establishment = _create_establishment()
    business_unit = _create_legacy_business_unit(establishment=establishment)
    other_establishment = _create_establishment()
    rows = [
        ActivitySubject(
            establishment=other_establishment,
            business_unit=business_unit,
            normalized_name="stock",
            label="Stock",
        ),
        ActivitySubject(
            establishment=other_establishment,
            business_unit=business_unit,
            normalized_name="maintenance",
            label="Maintenance",
        ),
    ]
    for row in rows:
        derive_activity_subject_establishment(row)
    ActivitySubject.objects.bulk_create(rows)

    persisted = (
        ActivitySubject.objects.filter(business_unit=business_unit).order_by("normalized_name")
    )
    assert persisted.count() == 2
    assert all(subject.establishment_id == business_unit.establishment_id for subject in persisted)


@pytest.mark.django_db(transaction=True)
def test_lot2_migration_preserves_legacy_rows():
    executor = MigrationExecutor(connection)
    executor.migrate([("establishments", "0022_catalog_lot1")])
    apps = executor.loader.project_state([("establishments", "0022_catalog_lot1")]).apps

    Organization = apps.get_model("organizations", "Organization")
    Establishment = apps.get_model("establishments", "Establishment")
    BusinessUnit = apps.get_model("establishments", "BusinessUnit")
    ActivitySubject = apps.get_model("establishments", "ActivitySubject")

    org = Organization.objects.create(name="Migration Org")
    establishment = Establishment.objects.create(organization=org, name="Migration Est")
    business_unit = BusinessUnit.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
        description="Legacy BU description",
        unit_type="dedicated",
    )
    activity_subject = ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name="climatisation",
        label="Climatisation",
        description="Legacy subject description",
        source="manual",
    )

    legacy_business_unit = {
        "key": business_unit.key,
        "label": business_unit.label,
        "description": business_unit.description,
        "unit_type": business_unit.unit_type,
    }
    legacy_activity_subject = {
        "normalized_name": activity_subject.normalized_name,
        "label": activity_subject.label,
        "description": activity_subject.description,
        "source": activity_subject.source,
    }
    business_unit_id = business_unit.id
    activity_subject_id = activity_subject.id

    executor = MigrationExecutor(connection)
    executor.migrate([("establishments", "0023_bu_as_lot2_identity")])

    from houston.establishments.models import ActivitySubject as RealActivitySubject
    from houston.establishments.models import BusinessUnit as RealBusinessUnit

    business_unit = RealBusinessUnit.objects.get(pk=business_unit_id)
    activity_subject = RealActivitySubject.objects.get(pk=activity_subject_id)

    assert business_unit.key == legacy_business_unit["key"]
    assert business_unit.label == legacy_business_unit["label"]
    assert business_unit.description == legacy_business_unit["description"]
    assert business_unit.unit_type == legacy_business_unit["unit_type"]
    assert business_unit.specific_name is None
    assert business_unit.normalized_specific_name is None
    assert business_unit.routing_key is None
    assert business_unit.instance_description is None

    assert activity_subject.normalized_name == legacy_activity_subject["normalized_name"]
    assert activity_subject.label == legacy_activity_subject["label"]
    assert activity_subject.description == legacy_activity_subject["description"]
    assert activity_subject.source == legacy_activity_subject["source"]
    assert activity_subject.routing_key is None

    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())
