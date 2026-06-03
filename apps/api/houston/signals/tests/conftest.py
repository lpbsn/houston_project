from __future__ import annotations

import uuid
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
    Establishment,
    EstablishmentMembership,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
)
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.test_permissions import build_membership
from houston.observations.models import Observation, ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION

GOLDEN_OBSERVATION_TEXT = (
    "La lumière clignote à l'entrée de restaurant. Il n'y a plus de sirop mojito au bar."
)

RESTAURANT_MODULE_KEY = "restaurant"
RESTAURANT_SALLE_DOMAIN_KEY = "restaurant__salle"
RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY = "restaurant__salle__maintenance"
RESTAURANT_BAR_DOMAIN_KEY = "restaurant__bar"
RESTAURANT_BAR_STOCK_SUBJECT_KEY = "restaurant__bar__stocks_approvisionnement"


@dataclass(frozen=True)
class RestaurantLightingBarStockTaxonomy:
    module: OperationalModule
    salle_domain: OperationalDomain
    bar_domain: OperationalDomain
    salle_maintenance_subject: OperationalSubject | None
    bar_stock_subject: OperationalSubject | None


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


def create_taxonomy(establishment: Establishment):
    suffix = uuid.uuid4().hex[:8]
    module_key = f"hotel_{suffix}"
    domain_key = f"{module_key}__hebergement"
    subject_key = f"{domain_key}__maintenance"
    module = OperationalModule.objects.create(
        establishment=establishment,
        key=module_key,
        label="Hotel",
        active=True,
    )
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key=domain_key,
        label="Hebergement",
        active=True,
    )
    subject = OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=domain,
        key=subject_key,
        label="Maintenance",
        active=True,
    )
    return module, domain, subject


def create_restaurant_lighting_bar_stock_taxonomy(
    establishment: Establishment,
    *,
    include_salle_maintenance: bool = True,
    include_bar_stock: bool = True,
) -> RestaurantLightingBarStockTaxonomy:
    """
    Catalogue keys from docs/catalogue/arborescence.csv (stable, no random suffix).
    """
    module = OperationalModule.objects.create(
        establishment=establishment,
        key=RESTAURANT_MODULE_KEY,
        label="Restaurant",
        active=True,
    )
    salle_domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key=RESTAURANT_SALLE_DOMAIN_KEY,
        label="Salle",
        active=True,
    )
    bar_domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key=RESTAURANT_BAR_DOMAIN_KEY,
        label="Bar",
        active=True,
    )
    salle_maintenance_subject = None
    bar_stock_subject = None
    if include_salle_maintenance:
        salle_maintenance_subject = OperationalSubject.objects.create(
            establishment=establishment,
            operational_domain=salle_domain,
            key=RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY,
            label="Maintenance",
            active=True,
        )
    if include_bar_stock:
        bar_stock_subject = OperationalSubject.objects.create(
            establishment=establishment,
            operational_domain=bar_domain,
            key=RESTAURANT_BAR_STOCK_SUBJECT_KEY,
            label="Stocks & approvisionnement",
            active=True,
        )
    return RestaurantLightingBarStockTaxonomy(
        module=module,
        salle_domain=salle_domain,
        bar_domain=bar_domain,
        salle_maintenance_subject=salle_maintenance_subject,
        bar_stock_subject=bar_stock_subject,
    )


def golden_two_candidate_pipeline_output(
    *,
    taxonomy: RestaurantLightingBarStockTaxonomy,
) -> ObservationPipelineOutput:
    assert taxonomy.salle_maintenance_subject is not None
    assert taxonomy.bar_stock_subject is not None
    return ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Lumière clignote à l'entrée du restaurant",
                structured_summary=(
                    "Éclairage instable signalé à l'entrée du restaurant, "
                    "intervention maintenance requise."
                ),
                operational_module_key=RESTAURANT_MODULE_KEY,
                operational_domain_key=taxonomy.salle_domain.key,
                operational_subject_key=taxonomy.salle_maintenance_subject.key,
                operational_unit_key=None,
                location_text="Entrée restaurant",
                aggregate_into_signal_id=None,
            ),
            PipelineCandidateOutput(
                title="Rupture de sirop mojito au bar",
                structured_summary=(
                    "Plus de sirop mojito disponible au bar, réassort stock nécessaire."
                ),
                operational_module_key=RESTAURANT_MODULE_KEY,
                operational_domain_key=taxonomy.bar_domain.key,
                operational_subject_key=taxonomy.bar_stock_subject.key,
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
