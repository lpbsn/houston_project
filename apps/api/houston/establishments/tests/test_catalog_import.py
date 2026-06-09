from __future__ import annotations

import pytest

from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.catalog_source_normalization import (
    load_normalized_activity_subject_rows,
    load_normalized_business_unit_rows,
    normalize_catalog_from_source,
)
from houston.establishments.models import CatalogActivitySubject, CatalogBusinessUnit

pytestmark = pytest.mark.django_db


@pytest.fixture
def imported_catalog():
    return sync_catalog_from_normalized_rows()


def test_normalized_seed_counts():
    catalog = normalize_catalog_from_source()
    assert len(catalog.business_units) == 14
    assert len(catalog.activity_subjects) == 134
    assert catalog.report.deduplicated_pairs


def test_import_creates_catalog_business_units(imported_catalog):
    assert imported_catalog.business_units_created == 14
    assert CatalogBusinessUnit.objects.count() == 14
    hotel = CatalogBusinessUnit.objects.get(key="hotel")
    assert hotel.label == "Hôtel"
    assert hotel.default_unit_type == CatalogBusinessUnit.DefaultUnitType.DEDICATED


def test_import_creates_catalog_activity_subjects_linked_to_business_unit(imported_catalog):
    assert imported_catalog.activity_subjects_created == 134
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
    assert len(bu_rows) == 14
    assert len(as_rows) == 134
    assert any(
        row.key == "maintenance" and row.default_unit_type == "transversal" for row in bu_rows
    )
