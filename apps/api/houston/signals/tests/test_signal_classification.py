from __future__ import annotations

import pytest

from houston.establishments.models import BusinessUnit
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.models import Signal
from houston.signals.signal_classification import (
    InvalidSignalClassificationError,
    routing_status_for_classification,
    validate_partial_signal_routing,
    validate_signal_classification,
)
from houston.testing.factories import create_establishment


@pytest.mark.django_db
def test_validate_signal_classification_accepts_dedicated_different_from_affected():
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
def test_validate_signal_classification_rejects_subject_outside_responsible():
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
        business_unit=hotel,
        label="Menage",
    )

    with pytest.raises(
        InvalidSignalClassificationError,
        match="activity_subject must belong to responsible_business_unit",
    ):
        validate_signal_classification(
            establishment=establishment,
            affected_business_unit=hotel,
            responsible_business_unit=restaurant,
            activity_subject=subject,
        )


@pytest.mark.django_db
def test_validate_partial_signal_routing_accepts_affected_only():
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )

    validate_partial_signal_routing(
        establishment=establishment,
        affected_business_unit=hotel,
        responsible_business_unit=None,
        activity_subject=None,
    )


@pytest.mark.django_db
def test_validate_partial_signal_routing_rejects_subject_without_responsible():
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Menage",
    )

    with pytest.raises(
        InvalidSignalClassificationError,
        match="activity_subject requires responsible_business_unit",
    ):
        validate_partial_signal_routing(
            establishment=establishment,
            affected_business_unit=hotel,
            responsible_business_unit=None,
            activity_subject=subject,
        )


@pytest.mark.django_db
def test_routing_status_for_classification_resolved_for_complete_coherent_triplet():
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Menage",
    )

    assert (
        routing_status_for_classification(
            establishment=establishment,
            affected_business_unit=hotel,
            responsible_business_unit=hotel,
            activity_subject=subject,
        )
        == Signal.RoutingStatus.RESOLVED
    )


@pytest.mark.django_db
def test_routing_status_for_classification_unassigned_for_valid_partial():
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )

    assert (
        routing_status_for_classification(
            establishment=establishment,
            affected_business_unit=hotel,
            responsible_business_unit=None,
            activity_subject=None,
        )
        == Signal.RoutingStatus.UNASSIGNED
    )


@pytest.mark.django_db
def test_routing_status_for_classification_raises_on_incoherent_state():
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
        business_unit=hotel,
        label="Menage",
    )

    with pytest.raises(InvalidSignalClassificationError):
        routing_status_for_classification(
            establishment=establishment,
            affected_business_unit=hotel,
            responsible_business_unit=restaurant,
            activity_subject=subject,
        )
