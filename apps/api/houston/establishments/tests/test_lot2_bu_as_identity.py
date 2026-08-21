from __future__ import annotations

import uuid

import pytest
from django.db import IntegrityError, connection

from houston.establishments.business_unit_identity import (
    build_business_unit_routing_key,
    build_free_activity_subject_routing_key,
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
from houston.testing.taxonomy import create_business_unit


def _create_establishment() -> Establishment:
    org = Organization.objects.create(name="Org")
    return Establishment.objects.create(organization=org, name="Est")


def _raw_business_unit(
    *,
    establishment: Establishment,
    catalog_key: str,
    specific_name: str,
    routing_key: str | None = None,
) -> BusinessUnit:
    catalog = CatalogBusinessUnit.objects.get(key=catalog_key)
    business_unit_id = uuid.uuid4()
    normalized = normalize_business_unit_specific_name(specific_name)
    return BusinessUnit.objects.create(
        id=business_unit_id,
        establishment=establishment,
        catalog_business_unit=catalog,
        specific_name=specific_name,
        normalized_specific_name=normalized,
        routing_key=routing_key
        or build_business_unit_routing_key(
            business_unit_id=business_unit_id,
            catalog_key=catalog.key,
            specific_name=specific_name,
        ),
        instance_description="",
        source=BusinessUnit.Source.MANUAL,
        active=True,
    )


def _raw_free_activity_subject(
    *,
    establishment: Establishment,
    business_unit: BusinessUnit,
    label: str,
    normalized_name: str | None = None,
    routing_key: str | None = None,
) -> ActivitySubject:
    activity_subject_id = uuid.uuid4()
    return ActivitySubject.objects.create(
        id=activity_subject_id,
        establishment=establishment,
        business_unit=business_unit,
        normalized_name=normalized_name or slugify_label(label),
        label=label,
        routing_key=routing_key
        or build_free_activity_subject_routing_key(
            activity_subject_id=activity_subject_id,
            label=label,
        ),
        source=ActivitySubject.Source.MANUAL,
        active=True,
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
def test_business_unit_unique_normalized_specific_name(imported_catalog):
    establishment = _create_establishment()
    _raw_business_unit(
        establishment=establishment,
        catalog_key="hotel",
        specific_name="Food Court",
    )
    with pytest.raises(IntegrityError):
        _raw_business_unit(
            establishment=establishment,
            catalog_key="hotel",
            specific_name="Food Court",
        )


@pytest.mark.django_db
def test_business_unit_rejects_empty_normalized_specific_name(imported_catalog):
    establishment = _create_establishment()
    catalog = CatalogBusinessUnit.objects.get(key="hotel")
    business_unit_id = uuid.uuid4()
    with pytest.raises(IntegrityError):
        BusinessUnit.objects.create(
            id=business_unit_id,
            establishment=establishment,
            catalog_business_unit=catalog,
            specific_name="Food Court",
            normalized_specific_name="",
            routing_key=build_business_unit_routing_key(
                business_unit_id=business_unit_id,
                catalog_key=catalog.key,
                specific_name="Food Court",
            ),
            instance_description="",
            source=BusinessUnit.Source.MANUAL,
            active=True,
        )


@pytest.mark.django_db
def test_business_unit_unique_routing_key(imported_catalog):
    establishment = _create_establishment()
    catalog = CatalogBusinessUnit.objects.get(key="hotel")
    bu_id = uuid.uuid4()
    routing_key = build_business_unit_routing_key(
        business_unit_id=bu_id,
        catalog_key=catalog.key,
        specific_name="Food Court",
    )
    _raw_business_unit(
        establishment=establishment,
        catalog_key="hotel",
        specific_name="Food Court",
        routing_key=routing_key,
    )
    with pytest.raises(IntegrityError):
        _raw_business_unit(
            establishment=establishment,
            catalog_key="hotel",
            specific_name="Rooftop",
            routing_key=routing_key,
        )


@pytest.mark.django_db
def test_activity_subject_routing_key_unique_per_business_unit(imported_catalog):
    establishment = _create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    routing_key = build_free_activity_subject_routing_key(
        activity_subject_id=uuid.uuid4(),
        label="Stock",
    )
    _raw_free_activity_subject(
        establishment=establishment,
        business_unit=business_unit,
        label="Stock",
        normalized_name="stock",
        routing_key=routing_key,
    )
    with pytest.raises(IntegrityError):
        _raw_free_activity_subject(
            establishment=establishment,
            business_unit=business_unit,
            label="Stock duplicate",
            normalized_name="stock_duplicate",
            routing_key=routing_key,
        )


@pytest.mark.django_db
def test_activity_subject_rejects_empty_routing_key(imported_catalog):
    establishment = _create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    with pytest.raises(IntegrityError):
        ActivitySubject.objects.create(
            establishment=establishment,
            business_unit=business_unit,
            normalized_name="stock",
            label="Stock",
            routing_key="",
            source=ActivitySubject.Source.MANUAL,
            active=True,
        )


@pytest.mark.django_db
def test_activity_subject_normalized_name_accepts_255_chars(imported_catalog):
    establishment = _create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    normalized_name = "a" * 255
    subject = _raw_free_activity_subject(
        establishment=establishment,
        business_unit=business_unit,
        label="Long normalized name",
        normalized_name=normalized_name,
    )
    subject.refresh_from_db()
    assert subject.normalized_name == normalized_name
    assert len(subject.normalized_name) == 255


@pytest.mark.django_db
def test_derive_activity_subject_establishment_sets_establishment_id(imported_catalog):
    establishment = _create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    other_establishment = _create_establishment()
    subject = ActivitySubject(
        establishment=other_establishment,
        business_unit=business_unit,
        normalized_name="stock",
        label="Stock",
        routing_key="custom--stock--0123456789abcdef",
    )
    derive_activity_subject_establishment(subject)
    assert subject.establishment_id == business_unit.establishment_id


@pytest.mark.django_db
def test_bulk_create_activity_subject_with_explicit_establishment_derivation(imported_catalog):
    establishment = _create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    other_establishment = _create_establishment()
    rows = [
        ActivitySubject(
            establishment=other_establishment,
            business_unit=business_unit,
            normalized_name="stock",
            label="Stock",
            routing_key="custom--stock--0123456789abcdef",
        ),
        ActivitySubject(
            establishment=other_establishment,
            business_unit=business_unit,
            normalized_name="maintenance",
            label="Maintenance",
            routing_key="custom--maintenance--0123456789abcde0",
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


@pytest.mark.django_db
def test_lot2_legacy_columns_dropped_after_0026():
    table_name = BusinessUnit._meta.db_table
    with connection.cursor() as cursor:
        column_names = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table_name)
        }
    assert "key" not in column_names
    assert "label" not in column_names
    assert "description" not in column_names
    assert "unit_type" not in column_names
