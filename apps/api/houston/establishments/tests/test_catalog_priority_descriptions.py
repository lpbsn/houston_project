from __future__ import annotations

import pytest

from houston.ai.observation_pipeline import build_pipeline_input
from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.catalog_priority import (
    MIN_PRIORITY_DESCRIPTION_LENGTH,
    PRIORITY_ACTIVITY_SUBJECT_KEYS,
    PRIORITY_BUSINESS_UNIT_KEYS,
)
from houston.establishments.catalog_source_normalization import (
    load_normalized_activity_subject_rows,
    load_normalized_business_unit_rows,
)
from houston.establishments.models import CatalogActivitySubject, CatalogBusinessUnit
from houston.establishments.taxonomy_snapshot import build_establishment_taxonomy_snapshot
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
    create_establishment,
)
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def _rows_by_key(rows, *, key_attr: str = "key") -> dict[str, object]:
    return {getattr(row, key_attr): row for row in rows}


def test_priority_catalog_csv_rows_have_scope_descriptions():
    bu_rows = _rows_by_key(load_normalized_business_unit_rows())
    as_rows = _rows_by_key(load_normalized_activity_subject_rows())

    missing_bu = sorted(PRIORITY_BUSINESS_UNIT_KEYS - bu_rows.keys())
    missing_as = sorted(PRIORITY_ACTIVITY_SUBJECT_KEYS - as_rows.keys())
    assert not missing_bu, f"Missing priority business units in CSV: {missing_bu}"
    assert not missing_as, f"Missing priority activity subjects in CSV: {missing_as}"

    for key in PRIORITY_BUSINESS_UNIT_KEYS:
        description = bu_rows[key].description.strip()
        assert len(description) >= MIN_PRIORITY_DESCRIPTION_LENGTH, key
        if key == "maintenance":
            assert (
                "Exclut" in description
                or "exclut" in description
                or "pas un simple" in description
            ), key

    ambiguous_routing_keys = {
        "hotel__menage",
        "maintenance__plomberie_eau",
        "maintenance__equipements_dexploitation",
    }
    stock_routing_keys = {
        "restaurant__stock",
        "petit_dejeuner__stock",
        "commerce__stock",
        "livraison_uber_eats_deliveroo__stocks_dedies_livraison",
    }
    for key in PRIORITY_ACTIVITY_SUBJECT_KEYS:
        description = as_rows[key].description.strip()
        assert len(description) >= MIN_PRIORITY_DESCRIPTION_LENGTH, key
        if key in ambiguous_routing_keys:
            assert "Exclut" in description or "exclut" in description, key
        if key in stock_routing_keys:
            lowered = description.lower()
            assert "focus" in lowered or "produit" in lowered, key


def test_import_persists_priority_descriptions(imported_catalog):
    for key in PRIORITY_BUSINESS_UNIT_KEYS:
        row = CatalogBusinessUnit.objects.get(key=key)
        assert len(row.description.strip()) >= MIN_PRIORITY_DESCRIPTION_LENGTH

    for key in PRIORITY_ACTIVITY_SUBJECT_KEYS:
        row = CatalogActivitySubject.objects.get(key=key)
        assert len(row.description.strip()) >= MIN_PRIORITY_DESCRIPTION_LENGTH


@pytest.mark.django_db
def test_taxonomy_snapshot_includes_imported_catalog_descriptions():
    sync_catalog_from_normalized_rows()
    establishment = create_establishment()
    catalog_hotel = CatalogBusinessUnit.objects.get(key="hotel")
    catalog_menage = CatalogActivitySubject.objects.get(key="hotel__menage")

    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label=catalog_hotel.label,
        description=catalog_hotel.description,
        unit_type="dedicated",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label=catalog_menage.label,
        description=catalog_menage.description,
    )

    snapshot = build_establishment_taxonomy_snapshot(establishment_id=establishment.id)

    assert snapshot["business_units"][0]["description"] == catalog_hotel.description
    assert snapshot["business_units"][0]["activity_subjects"][0]["description"] == (
        catalog_menage.description
    )


@pytest.mark.django_db
def test_pipeline_input_includes_runtime_descriptions_from_catalog():
    sync_catalog_from_normalized_rows()
    membership = build_membership()
    catalog_plomberie = CatalogActivitySubject.objects.get(key="maintenance__plomberie_eau")
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
        description=CatalogBusinessUnit.objects.get(key="maintenance").description,
        unit_type="transversal",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label=catalog_plomberie.label,
        description=catalog_plomberie.description,
    )
    observation = create_observation(membership=membership, text="Fuite d'eau dans le couloir.")

    payload = build_pipeline_input(observation=observation)
    subjects = payload["establishment_taxonomy"]["business_units"][0]["activity_subjects"]

    assert subjects[0]["description"] == catalog_plomberie.description
    assert "Exclut" in subjects[0]["description"]
