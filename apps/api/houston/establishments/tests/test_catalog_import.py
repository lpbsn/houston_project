from __future__ import annotations

import pytest

from houston.establishments.catalog_import import (
    preflight_catalog_import_from_rows,
    sync_catalog_from_normalized_rows,
)
from houston.establishments.catalog_seed_counts import (
    EXPECTED_CATALOG_ACTIVITY_SUBJECT_COUNT,
    EXPECTED_CATALOG_BUSINESS_UNIT_COUNT,
)
from houston.establishments.catalog_source_normalization import (
    default_unit_type_for_business_unit_key,
    load_normalized_activity_subject_rows,
    load_normalized_business_unit_rows,
    normalize_catalog_from_source,
)
from houston.establishments.models import CatalogActivitySubject, CatalogBusinessUnit

pytestmark = pytest.mark.django_db


# suggestion_source.csv is the historical Excel trace. Regenerating it does not
# rebuild the normalized seed: descriptions stay empty and later catalogue rows
# are absent. These counts belong to that trace, not to the versioned CSVs.
HISTORICAL_SOURCE_BUSINESS_UNIT_COUNT = 14
HISTORICAL_SOURCE_ACTIVITY_SUBJECT_COUNT = 134


def test_normalized_seed_counts():
    historical = normalize_catalog_from_source()
    assert historical.report.deduplicated_pairs
    assert historical.report.business_unit_count == HISTORICAL_SOURCE_BUSINESS_UNIT_COUNT
    assert len(historical.business_units) == HISTORICAL_SOURCE_BUSINESS_UNIT_COUNT
    assert historical.report.activity_subject_count == HISTORICAL_SOURCE_ACTIVITY_SUBJECT_COUNT
    assert len(historical.activity_subjects) == HISTORICAL_SOURCE_ACTIVITY_SUBJECT_COUNT
    assert all(not row.description for row in historical.business_units)
    assert all(not row.description for row in historical.activity_subjects)
    historical_unit_keys = {row.key for row in historical.business_units}
    assert all(
        row.catalog_business_unit_key in historical_unit_keys
        for row in historical.activity_subjects
    )
    assert all(
        row.unit_type == default_unit_type_for_business_unit_key(row.key)
        for row in historical.business_units
    )

    business_unit_rows = load_normalized_business_unit_rows()
    activity_subject_rows = load_normalized_activity_subject_rows()
    assert len(business_unit_rows) == EXPECTED_CATALOG_BUSINESS_UNIT_COUNT
    assert len(activity_subject_rows) == EXPECTED_CATALOG_ACTIVITY_SUBJECT_COUNT
    assert len(business_unit_rows) != len(historical.business_units)
    assert len(activity_subject_rows) != len(historical.activity_subjects)
    preflight_catalog_import_from_rows(
        business_unit_rows=business_unit_rows,
        activity_subject_rows=activity_subject_rows,
    )


def test_import_creates_catalog_business_units(imported_catalog):
    assert imported_catalog.business_units_created == EXPECTED_CATALOG_BUSINESS_UNIT_COUNT
    assert CatalogBusinessUnit.objects.count() == EXPECTED_CATALOG_BUSINESS_UNIT_COUNT
    hotel = CatalogBusinessUnit.objects.get(key="hotel")
    assert hotel.label == "Hôtel"
    assert hotel.unit_type == CatalogBusinessUnit.DefaultUnitType.DEDICATED


def test_import_creates_catalog_activity_subjects_linked_to_business_unit(imported_catalog):
    assert imported_catalog.activity_subjects_created == EXPECTED_CATALOG_ACTIVITY_SUBJECT_COUNT
    coworking = CatalogBusinessUnit.objects.get(key="coworking")
    subjects = CatalogActivitySubject.objects.filter(catalog_business_unit=coworking)
    assert subjects.count() == 12
    assert subjects.filter(key="coworking__proprete", label="Propreté").exists()


def test_import_is_idempotent(imported_catalog):
    first_bu_count = CatalogBusinessUnit.objects.count()
    first_as_count = CatalogActivitySubject.objects.count()

    second = sync_catalog_from_normalized_rows()

    assert second.total_created == 0
    assert second.total_updated == imported_catalog.total_created
    assert CatalogBusinessUnit.objects.count() == first_bu_count
    assert CatalogActivitySubject.objects.count() == first_as_count


def test_import_reads_versioned_seed_csvs():
    bu_rows = load_normalized_business_unit_rows()
    as_rows = load_normalized_activity_subject_rows()
    assert len(bu_rows) == EXPECTED_CATALOG_BUSINESS_UNIT_COUNT
    assert len(as_rows) == EXPECTED_CATALOG_ACTIVITY_SUBJECT_COUNT
    assert any(
        row.key == "maintenance" and row.unit_type == "transversal" for row in bu_rows
    )
