import importlib
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.db import IntegrityError, connection, transaction

from houston.establishments.business_unit_domain_service import (
    _create_business_unit_core,
    reactivate_business_unit,
    update_business_unit_specific_name,
)
from houston.establishments.models import BusinessUnit, CatalogBusinessUnit
from houston.establishments.public_serialization import serialize_business_unit_ref
from houston.testing.factories import create_establishment

pytestmark = pytest.mark.django_db


def test_colors_are_distinct_and_stable_across_rename_reactivation_and_new_poles(imported_catalog):
    establishment = create_establishment()
    catalog = CatalogBusinessUnit.objects.get(key="restaurant")

    def create(name):
        return _create_business_unit_core(
            establishment=establishment, catalog_business_unit=catalog, specific_name=name
        )

    first, second = create("Restaurant"), create("Bar")
    assert (first.color_index, second.color_index) == (0, 1)
    renamed = update_business_unit_specific_name(
        establishment_id=establishment.id, business_unit_id=first.id, specific_name="Food Court"
    )
    assert renamed.color_index == 0
    BusinessUnit.objects.filter(id=second.id).update(active=False)
    third = create("Terrasse")
    assert third.color_index == 2
    restored = reactivate_business_unit(
        establishment_id=establishment.id, business_unit_id=second.id
    )
    assert restored.color_index == 1
    assert serialize_business_unit_ref(business_unit=renamed)["color_index"] == 0
    other = _create_business_unit_core(
        establishment=create_establishment(), catalog_business_unit=catalog, specific_name="Bar"
    )
    assert other.color_index == 0
    with pytest.raises(IntegrityError), transaction.atomic():
        BusinessUnit.objects.filter(id=third.id).update(color_index=0)


def test_backfill_assigns_existing_and_inactive_poles_in_creation_order(imported_catalog):
    establishment = create_establishment()
    catalog = CatalogBusinessUnit.objects.get(key="restaurant")
    units = [
        _create_business_unit_core(
            establishment=establishment, catalog_business_unit=catalog, specific_name=name
        )
        for name in ["Restaurant", "Bar", "Terrasse"]
    ]
    BusinessUnit.objects.filter(establishment=establishment).update(color_index=None)
    BusinessUnit.objects.filter(id=units[1].id).update(active=False)
    migration = importlib.import_module(
        "houston.establishments.migrations.0040_business_unit_color_index"
    )
    migration.assign_existing_colors(apps, SimpleNamespace(connection=connection))
    for index, unit in enumerate(units):
        unit.refresh_from_db()
        assert unit.color_index == index
