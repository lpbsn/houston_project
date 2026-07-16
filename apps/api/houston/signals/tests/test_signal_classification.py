from __future__ import annotations

import pytest

from houston.establishments.models import BusinessUnit
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.signal_classification import (
    InvalidSignalClassificationError,
    validate_signal_classification,
)
from houston.testing.factories import create_establishment


@pytest.mark.django_db
def test_validate_signal_classification_rejects_non_transversal_responsible():
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    restaurant = create_business_unit(
        establishment=establishment,
        key="restaurant",
        label="Restaurant",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=restaurant,
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
    establishment = create_establishment()
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
def test_validate_signal_classification_uses_catalog_unit_type():
    establishment = create_establishment()
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
    catalog = maintenance.catalog_business_unit
    assert catalog is not None
    assert catalog.unit_type == BusinessUnit.UnitType.TRANSVERSAL
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
def test_validate_signal_classification_rejects_responsible_without_catalog():
    establishment = create_establishment()
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
    maintenance.catalog_business_unit_id = None
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=maintenance,
        label="Climatisation",
    )

    with pytest.raises(InvalidSignalClassificationError, match="catalog business unit"):
        validate_signal_classification(
            establishment=establishment,
            affected_business_unit=hotel,
            responsible_business_unit=maintenance,
            activity_subject=subject,
        )
