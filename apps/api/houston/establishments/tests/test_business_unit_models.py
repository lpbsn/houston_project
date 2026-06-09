from __future__ import annotations

import pytest
from django.db import IntegrityError

from houston.establishments.models import ActivitySubject, BusinessUnit, Establishment
from houston.establishments.taxonomy_normalization import normalize_activity_subject_name
from houston.organizations.models import Organization


@pytest.mark.django_db
def test_business_unit_unique_per_establishment():
    org = Organization.objects.create(name="Org")
    establishment = Establishment.objects.create(organization=org, name="Est")
    BusinessUnit.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
        unit_type=BusinessUnit.UnitType.DEDICATED,
    )
    with pytest.raises(IntegrityError):
        BusinessUnit.objects.create(
            establishment=establishment,
            key="hotel",
            label="Hotel duplicate",
            unit_type=BusinessUnit.UnitType.DEDICATED,
        )


@pytest.mark.django_db
def test_activity_subject_unique_per_business_unit_not_establishment():
    org = Organization.objects.create(name="Org")
    establishment = Establishment.objects.create(organization=org, name="Est")
    hotel = BusinessUnit.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
        unit_type=BusinessUnit.UnitType.DEDICATED,
    )
    maintenance = BusinessUnit.objects.create(
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
    )
    ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=maintenance,
        normalized_name=normalized,
        label="Climatisation",
    )
    with pytest.raises(IntegrityError):
        ActivitySubject.objects.create(
            establishment=establishment,
            business_unit=hotel,
            normalized_name=normalized,
            label="Climatisation duplicate",
        )
