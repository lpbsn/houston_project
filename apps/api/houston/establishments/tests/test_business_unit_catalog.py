from __future__ import annotations

import pytest

from houston.establishments.business_unit_catalog import (
    suggest_activity_subjects,
    suggest_business_units,
)
from houston.establishments.models import BusinessUnit, CatalogBusinessUnit

pytestmark = pytest.mark.django_db


def test_suggest_business_units_returns_empty_without_import(requires_empty_catalog):
    results = suggest_business_units(query="hotel")
    assert results == []


def test_suggest_activity_subjects_returns_empty_without_import(requires_empty_catalog):
    results = suggest_activity_subjects(
        business_unit_key="hotel",
        query="proprete",
    )
    assert results == []


def test_suggest_business_units_returns_coworking_for_cow_query(imported_catalog):
    results = suggest_business_units(query="Cow")
    assert results
    assert any(item["key"] == "coworking" and item["label"] == "Coworking" for item in results)


def test_suggest_business_units_returns_transversal_for_maintenance(imported_catalog):
    results = suggest_business_units(query="Maintenance")
    assert results
    maintenance = next(item for item in results if item["key"] == "maintenance")
    assert maintenance["default_unit_type"] == "transversal"


def test_suggest_activity_subjects_filters_by_business_unit(imported_catalog):
    results = suggest_activity_subjects(
        business_unit_key="coworking",
        query="prop",
    )
    assert results
    assert all(item["business_unit_key"] == "coworking" for item in results)
    assert any("Propreté" in item["label"] for item in results)


def test_default_unit_type_is_not_imposed_on_establishment_business_unit(imported_catalog):
    from houston.establishments.tests.taxonomy_helpers import create_establishment

    establishment = create_establishment(name="Catalog Override Hotel")
    business_unit = BusinessUnit.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.DEDICATED,
    )
    catalog_row = CatalogBusinessUnit.objects.get(key="maintenance")
    assert catalog_row.default_unit_type == CatalogBusinessUnit.DefaultUnitType.TRANSVERSAL
    assert business_unit.unit_type == BusinessUnit.UnitType.DEDICATED
