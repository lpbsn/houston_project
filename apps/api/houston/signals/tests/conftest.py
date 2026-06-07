from __future__ import annotations

from dataclasses import dataclass

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
)
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.test_permissions import build_membership
from houston.observations.models import Observation, ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import Signal

GOLDEN_OBSERVATION_TEXT = (
    "La lumière clignote à l'entrée de restaurant. Il n'y a plus de sirop mojito au bar."
)

RESTAURANT_MODULE_KEY = "restaurant"


@dataclass(frozen=True)
class RestaurantBusinessUnits:
    restaurant: BusinessUnit
    maintenance: BusinessUnit
    bar: BusinessUnit


@dataclass(frozen=True)
class RestaurantV3Taxonomy:
    restaurant: BusinessUnit
    maintenance: BusinessUnit | None
    bar: BusinessUnit
    lighting_subject: ActivitySubject | None
    stock_subject: ActivitySubject | None


def build_api_membership(**kwargs) -> EstablishmentMembership:
    membership = build_membership(**kwargs)
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    return membership


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def login(api_client: APIClient, *, user: User) -> str:
    identifier = user.email if user.email else user.username
    csrf = api_client.get("/api/v1/auth/csrf/").cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": TEST_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _get_or_create_business_unit(
    *,
    establishment: Establishment,
    key: str,
    label: str,
    unit_type: str = BusinessUnit.UnitType.DEDICATED,
) -> BusinessUnit:
    business_unit, _ = BusinessUnit.objects.get_or_create(
        establishment=establishment,
        key=key,
        defaults={
            "label": label,
            "unit_type": unit_type,
            "source": BusinessUnit.Source.MANUAL,
            "active": True,
        },
    )
    return business_unit


def _get_or_create_activity_subject(
    *,
    establishment: Establishment,
    business_unit: BusinessUnit,
    label: str,
) -> ActivitySubject:
    from houston.establishments.taxonomy_normalization import (
        normalize_activity_subject_name,
    )

    normalized_name = normalize_activity_subject_name(label)
    subject, _ = ActivitySubject.objects.get_or_create(
        business_unit=business_unit,
        normalized_name=normalized_name,
        defaults={
            "establishment": establishment,
            "label": label,
            "source": ActivitySubject.Source.MANUAL,
            "active": True,
        },
    )
    return subject


def create_restaurant_business_units(
    establishment: Establishment,
) -> RestaurantBusinessUnits:
    return RestaurantBusinessUnits(
        restaurant=_get_or_create_business_unit(
            establishment=establishment,
            key=RESTAURANT_MODULE_KEY,
            label="Restaurant",
        ),
        maintenance=_get_or_create_business_unit(
            establishment=establishment,
            key="maintenance",
            label="Maintenance",
            unit_type=BusinessUnit.UnitType.TRANSVERSAL,
        ),
        bar=_get_or_create_business_unit(
            establishment=establishment,
            key="bar",
            label="Bar",
        ),
    )


def classify_golden_restaurant_signals(
    *,
    establishment: Establishment,
    business_units: RestaurantBusinessUnits,
) -> None:
    lighting = Signal.objects.filter(
        establishment=establishment,
        title__icontains="lumière",
    ).first()
    if lighting is not None:
        lighting.affected_business_unit = business_units.restaurant
        lighting.responsible_business_unit = business_units.maintenance
        lighting.save(
            update_fields=[
                "affected_business_unit",
                "responsible_business_unit",
                "updated_at",
            ]
        )

    syrup = Signal.objects.filter(
        establishment=establishment,
        title__icontains="mojito",
    ).first()
    if syrup is not None:
        syrup.affected_business_unit = business_units.bar
        syrup.responsible_business_unit = business_units.bar
        syrup.save(
            update_fields=[
                "affected_business_unit",
                "responsible_business_unit",
                "updated_at",
            ]
        )


def create_restaurant_v3_taxonomy(
    establishment: Establishment,
    *,
    include_maintenance_transversal: bool = True,
    include_lighting_subject: bool = True,
    include_bar_stock: bool = True,
) -> RestaurantV3Taxonomy:
    restaurant = _get_or_create_business_unit(
        establishment=establishment,
        key=RESTAURANT_MODULE_KEY,
        label="Restaurant",
    )
    maintenance = None
    lighting_subject = None
    if include_maintenance_transversal:
        maintenance = _get_or_create_business_unit(
            establishment=establishment,
            key="maintenance",
            label="Maintenance",
            unit_type=BusinessUnit.UnitType.TRANSVERSAL,
        )
        if include_lighting_subject:
            lighting_subject = _get_or_create_activity_subject(
                establishment=establishment,
                business_unit=maintenance,
                label="Électricité",
            )
    bar = _get_or_create_business_unit(
        establishment=establishment,
        key="bar",
        label="Bar",
    )
    stock_subject = None
    if include_bar_stock:
        stock_subject = _get_or_create_activity_subject(
            establishment=establishment,
            business_unit=bar,
            label="Stock",
        )
    return RestaurantV3Taxonomy(
        restaurant=restaurant,
        maintenance=maintenance,
        bar=bar,
        lighting_subject=lighting_subject,
        stock_subject=stock_subject,
    )


def golden_two_candidate_pipeline_output(
    *,
    taxonomy: RestaurantV3Taxonomy,
) -> ObservationPipelineOutput:
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assert taxonomy.stock_subject is not None
    return ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière clignote à l'entrée du restaurant",
                structured_summary=(
                    "Éclairage instable signalé à l'entrée du restaurant, "
                    "intervention maintenance requise."
                ),
                affected_business_unit_key=RESTAURANT_MODULE_KEY,
                responsible_business_unit_key="maintenance",
                activity_subject_key=taxonomy.lighting_subject.normalized_name,
                operational_unit_key=None,
                location_text="Entrée restaurant",
                aggregate_into_signal_id=None,
            ),
            PipelineCandidateOutput(
                title="Rupture de sirop mojito au bar",
                structured_summary=(
                    "Plus de sirop mojito disponible au bar, réassort stock nécessaire."
                ),
                affected_business_unit_key="bar",
                responsible_business_unit_key="bar",
                activity_subject_key=taxonomy.stock_subject.normalized_name,
                operational_unit_key=None,
                location_text="Bar",
                aggregate_into_signal_id=None,
            ),
        ],
    )


def create_observation(*, membership: EstablishmentMembership, text: str = "A" * 20) -> Observation:
    now = timezone.now()
    observation = Observation.objects.create(
        establishment=membership.establishment,
        submitted_by_membership=membership,
        raw_text=text,
        submitted_at=now,
    )
    ObservationProcessing.objects.create(
        observation=observation,
        status=ObservationProcessing.Status.QUEUED,
        queued_at=now,
    )
    return observation


def signal_feed_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/signal-feed/"


def signal_detail_url(establishment_id, signal_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/signals/{signal_id}/"


def create_v3_signal(
    establishment: Establishment,
    *,
    affected_business_unit: BusinessUnit,
    responsible_business_unit: BusinessUnit,
    activity_subject: ActivitySubject,
    title: str = "Signal title",
    structured_summary: str = "Structured summary safe.",
    status: str = Signal.Status.OPEN,
    location_text: str = "",
) -> Signal:
    now = timezone.now()
    return Signal.objects.create(
        establishment=establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
        title=title,
        structured_summary=structured_summary,
        location_text=location_text,
        status=status,
        last_activity_at=now,
    )


def create_minimal_v3_signal(
    membership: EstablishmentMembership,
    *,
    title: str = "Signal title",
    status: str = Signal.Status.OPEN,
) -> Signal:
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    return create_v3_signal(
        membership.establishment,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        title=title,
        status=status,
    )
