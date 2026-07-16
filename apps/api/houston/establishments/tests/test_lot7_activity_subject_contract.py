"""Lot 7 — ActivitySubject generic/free contract on current dual-write base."""

from __future__ import annotations

import pytest

from houston.core.exceptions import DomainValidationError
from houston.establishments.business_unit_domain_service import (
    create_onboarding_business_unit,
    create_runtime_activity_subject,
    create_runtime_business_unit,
)
from houston.establishments.business_unit_identity import (
    normalize_generic_activity_subject_name,
    validate_activity_subject_catalog_coherence,
)
from houston.establishments.models import (
    ActivitySubject,
    CatalogActivitySubject,
    CatalogBusinessUnit,
)
from houston.testing.factories import create_establishment

pytestmark = pytest.mark.django_db


def _catalog(key: str) -> CatalogBusinessUnit:
    return CatalogBusinessUnit.objects.get(key=key)


def test_generic_activity_subject_uses_catalog_routing_key_and_source(imported_catalog):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    catalog_subject = CatalogActivitySubject.objects.get(key="restaurant__stock")

    business_unit = create_onboarding_business_unit(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Food Court",
        generic_activity_subject_keys=["restaurant__stock"],
    )

    subject = ActivitySubject.objects.get(
        business_unit=business_unit,
        routing_key="restaurant__stock",
    )
    assert subject.catalog_activity_subject_id == catalog_subject.id
    assert subject.source == ActivitySubject.Source.CATALOG_SUGGESTION
    assert subject.routing_key == catalog_subject.key
    assert subject.normalized_name == normalize_generic_activity_subject_name(
        catalog_subject.label
    )
    assert subject.label == catalog_subject.label
    assert subject.establishment_id == establishment.id


def test_free_activity_subject_uses_custom_routing_key_and_manual_source(
    imported_catalog,
):
    establishment = create_establishment()
    restaurant = _catalog("restaurant")
    business_unit = create_runtime_business_unit(
        establishment=establishment,
        catalog_business_unit=restaurant,
        specific_name="Rooftop",
    )

    subject = create_runtime_activity_subject(
        establishment_id=establishment.id,
        business_unit_id=business_unit.id,
        label="Terrasse VIP",
        description="Zone privée",
    )

    assert subject.catalog_activity_subject_id is None
    assert subject.source == ActivitySubject.Source.MANUAL
    assert subject.routing_key.startswith("custom--terrasse-vip--")
    assert subject.label == "Terrasse VIP"
    assert subject.establishment_id == establishment.id


def test_catalog_subject_business_unit_mismatch_rejected(imported_catalog):
    establishment = create_establishment()
    restaurant = create_runtime_business_unit(
        establishment=establishment,
        catalog_business_unit=_catalog("restaurant"),
        specific_name="Food Court",
    )
    hotel_subject = CatalogActivitySubject.objects.get(key="hotel__menage")

    with pytest.raises(DomainValidationError) as exc_info:
        validate_activity_subject_catalog_coherence(
            business_unit=restaurant,
            catalog_activity_subject=hotel_subject,
        )
    assert exc_info.value.code == "catalog_subject_business_unit_mismatch"


def test_free_subject_routing_key_is_immutable_when_label_updated_without_rekey(
    imported_catalog,
):
    establishment = create_establishment()
    business_unit = create_runtime_business_unit(
        establishment=establishment,
        catalog_business_unit=_catalog("restaurant"),
        specific_name="Food Court",
    )
    subject = create_runtime_activity_subject(
        establishment_id=establishment.id,
        business_unit_id=business_unit.id,
        label="Terrasse VIP",
    )
    original_routing_key = subject.routing_key

    subject.label = "Terrasse Premium"
    subject.save(update_fields=["label", "updated_at"])
    subject.refresh_from_db()

    assert subject.label == "Terrasse Premium"
    assert subject.routing_key == original_routing_key
    assert subject.routing_key.startswith("custom--terrasse-vip--")
