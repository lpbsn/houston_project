from __future__ import annotations

import pytest

from houston.establishments.models import ActivitySubject, BusinessUnit, Establishment
from houston.establishments.taxonomy_normalization import normalize_activity_subject_name
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.organizations.models import Organization
from houston.signals.signal_classification import (
    InvalidSignalClassificationError,
    validate_signal_classification,
)
from houston.testing.factories import create_establishment


@pytest.mark.django_db
def test_validate_signal_classification_rejects_non_transversal_responsible():
    org = Organization.objects.create(name="Org")
    establishment = Establishment.objects.create(organization=org, name="Est")
    hotel = BusinessUnit.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
        unit_type=BusinessUnit.UnitType.DEDICATED,
    )
    restaurant = BusinessUnit.objects.create(
        establishment=establishment,
        key="restaurant",
        label="Restaurant",
        unit_type=BusinessUnit.UnitType.DEDICATED,
    )
    subject = ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=restaurant,
        normalized_name=normalize_activity_subject_name("Service"),
        label="Service",
    )

    with pytest.raises(InvalidSignalClassificationError):
        validate_signal_classification(
            establishment=establishment,
            affected_business_unit=hotel,
            responsible_business_unit=restaurant,
            activity_subject=subject,
        )


@pytest.mark.django_db
def test_validate_signal_classification_accepts_transversal_responsible():
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
    subject = ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=maintenance,
        normalized_name=normalize_activity_subject_name("Climatisation"),
        label="Climatisation",
    )

    validate_signal_classification(
        establishment=establishment,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=subject,
    )


@pytest.mark.django_db
def test_validate_signal_classification_follows_catalog_unit_type_on_divergence():
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
        unit_type=BusinessUnit.UnitType.DEDICATED,
    )
    maintenance = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.TRANSVERSAL,
    )
    catalog = maintenance.catalog_business_unit
    assert catalog is not None
    catalog.unit_type = BusinessUnit.UnitType.TRANSVERSAL
    catalog.save(update_fields=["unit_type", "updated_at"])
    maintenance.unit_type = BusinessUnit.UnitType.DEDICATED
    maintenance.save(update_fields=["unit_type", "updated_at"])
    assert catalog.unit_type == BusinessUnit.UnitType.TRANSVERSAL
    assert maintenance.unit_type == BusinessUnit.UnitType.DEDICATED
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=maintenance,
        label="Climatisation",
    )

    validate_signal_classification(
        establishment=establishment,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=subject,
    )


@pytest.mark.django_db
def test_validate_signal_classification_legacy_bu_without_catalog_uses_unit_type():
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
        catalog_business_unit=None,
    )
    assert maintenance.catalog_business_unit_id is None
    subject = ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=maintenance,
        normalized_name=normalize_activity_subject_name("Climatisation"),
        label="Climatisation",
    )

    validate_signal_classification(
        establishment=establishment,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=subject,
    )

    restaurant = BusinessUnit.objects.create(
        establishment=establishment,
        key="restaurant",
        label="Restaurant",
        unit_type=BusinessUnit.UnitType.DEDICATED,
        catalog_business_unit=None,
    )
    restaurant_subject = ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=restaurant,
        normalized_name=normalize_activity_subject_name("Service"),
        label="Service",
    )
    with pytest.raises(InvalidSignalClassificationError):
        validate_signal_classification(
            establishment=establishment,
            affected_business_unit=hotel,
            responsible_business_unit=restaurant,
            activity_subject=restaurant_subject,
        )
