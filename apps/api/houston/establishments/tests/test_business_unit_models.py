from __future__ import annotations

import uuid

import pytest
from django.db import IntegrityError

from houston.establishments.business_unit_identity import (
    build_business_unit_routing_key,
    build_free_activity_subject_routing_key,
    normalize_business_unit_specific_name,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogBusinessUnit,
    Establishment,
)
from houston.establishments.taxonomy_normalization import normalize_activity_subject_name
from houston.organizations.models import Organization
from houston.testing.taxonomy import create_activity_subject, create_business_unit


def _raw_business_unit(
    *,
    establishment: Establishment,
    catalog_key: str,
    specific_name: str,
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
        routing_key=build_business_unit_routing_key(
            business_unit_id=business_unit_id,
            catalog_key=catalog.key,
            specific_name=specific_name,
        ),
        instance_description="",
        source=BusinessUnit.Source.MANUAL,
        active=True,
    )


@pytest.mark.django_db
def test_business_unit_unique_normalized_specific_name_per_establishment(imported_catalog):
    org = Organization.objects.create(name="Org")
    establishment = Establishment.objects.create(organization=org, name="Est")
    _raw_business_unit(
        establishment=establishment,
        catalog_key="hotel",
        specific_name="Hotel",
    )
    with pytest.raises(IntegrityError):
        _raw_business_unit(
            establishment=establishment,
            catalog_key="hotel",
            specific_name="Hotel",
        )


@pytest.mark.django_db
def test_activity_subject_unique_per_business_unit_not_establishment(imported_catalog):
    org = Organization.objects.create(name="Org")
    establishment = Establishment.objects.create(organization=org, name="Est")
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    maintenance = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.TRANSVERSAL,
    )
    normalized = normalize_activity_subject_name("Climatisation")
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=hotel,
        normalized_name=normalized,
        label="Climatisation",
        routing_key=build_free_activity_subject_routing_key(
            activity_subject_id=uuid.uuid4(),
            label="Climatisation",
        ),
    )
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=maintenance,
        normalized_name=normalized,
        label="Climatisation",
        routing_key=build_free_activity_subject_routing_key(
            activity_subject_id=uuid.uuid4(),
            label="Climatisation",
        ),
    )
    with pytest.raises(IntegrityError):
        create_activity_subject(
            establishment=establishment,
            business_unit=hotel,
            label="Climatisation",
        )
