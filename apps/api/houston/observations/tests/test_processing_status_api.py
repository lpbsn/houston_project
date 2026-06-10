from __future__ import annotations

import json
import uuid

import pytest
from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.observations.selectors import resolve_ux_status
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import apply_pipeline_output, run_observation_pipeline
from houston.signals.tests.conftest import (
    GOLDEN_OBSERVATION_TEXT,
    create_observation,
    create_restaurant_v3_taxonomy,
    golden_two_candidate_pipeline_output,
)
from houston.testing.factories import build_membership
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def processing_status_url(establishment_id, observation_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/observations/"
        f"{observation_id}/processing-status/"
    )


def login(api_client: APIClient, *, user) -> str:
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


def test_resolve_ux_status_mapping():
    assert (
        resolve_ux_status(
            status=ObservationProcessing.Status.QUEUED,
            outcome="",
        )
        == "analysis_queued"
    )
    assert (
        resolve_ux_status(
            status=ObservationProcessing.Status.PROCESSED,
            outcome=ObservationProcessing.Outcome.SIGNALS_CREATED,
        )
        == "signal_created"
    )
    assert (
        resolve_ux_status(
            status=ObservationProcessing.Status.PROCESSED,
            outcome=ObservationProcessing.Outcome.SIGNAL_AGGREGATED,
        )
        == "signal_updated"
    )
    assert (
        resolve_ux_status(
            status=ObservationProcessing.Status.PROCESSED,
            outcome=ObservationProcessing.Outcome.NO_SIGNAL_CREATED,
        )
        == "no_signal_created"
    )
    assert (
        resolve_ux_status(
            status=ObservationProcessing.Status.FAILED,
            outcome="",
        )
        == "analysis_failed"
    )


def test_processing_status_returns_queued_without_raw_text(api_client):
    membership = build_membership()
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    observation = create_observation(membership=membership)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        processing_status_url(membership.establishment_id, observation.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["observation_id"] == str(observation.id)
    assert body["status"] == ObservationProcessing.Status.QUEUED
    assert body["ux_status"] == "analysis_queued"
    assert body["signal_ids"] == []
    assert body["signals"] == []
    assert "raw_text" not in body
    assert "text" not in body
    assert "validated_text" not in body


def test_processing_status_404_for_other_establishment(api_client):
    membership = build_membership()
    other = build_membership()
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    observation = create_observation(membership=other)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        processing_status_url(membership.establishment_id, observation.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 404


def test_processing_status_after_pipeline_includes_signal_ids(api_client):
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    hotel = create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hotel",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    observation = create_observation(membership=membership)

    run_observation_pipeline(observation.id, provider=FakeObservationPipelineProvider())

    token = login(api_client, user=membership.user)
    response = api_client.get(
        processing_status_url(membership.establishment_id, observation.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ObservationProcessing.Status.PROCESSED
    assert body["outcome"] == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert body["ux_status"] == "signal_created"
    assert len(body["signal_ids"]) == 1
    signal_id = uuid.UUID(body["signal_ids"][0])
    assert Signal.objects.filter(id=signal_id).exists()
    assert CandidateSignal.objects.filter(
        observation=observation,
        result_signal_id=signal_id,
    ).exists()
    assert len(body["signals"]) == 1
    assert body["signals"][0]["id"] == str(signal_id)
    assert "affected_business_unit_key" in body["signals"][0]
    assert "responsible_business_unit_key" in body["signals"][0]
    assert "activity_subject_key" in body["signals"][0]
    assert "module_key" not in body["signals"][0]
    assert "operational_module_key" not in body["signals"][0]
    assert "raw_text" not in json.dumps(body["signals"])


def test_processing_status_lists_two_linked_signals_with_taxonomy(api_client):
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text=GOLDEN_OBSERVATION_TEXT)
    apply_pipeline_output(
        observation=observation,
        output=golden_two_candidate_pipeline_output(taxonomy=taxonomy),
    )

    token = login(api_client, user=membership.user)
    response = api_client.get(
        processing_status_url(membership.establishment_id, observation.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["signal_ids"]) == 2
    assert len(body["signals"]) == 2
    assert body["signals"][0]["responsible_business_unit_label"]
    assert body["signals"][0]["activity_subject_label"]
    location_texts = {entry["location_text"] for entry in body["signals"]}
    assert "Entrée restaurant" in location_texts
    assert "Bar" in location_texts
    assert "raw_text" not in response.content.decode()
    assert GOLDEN_OBSERVATION_TEXT not in response.content.decode()


def test_processing_status_failed(api_client):
    membership = build_membership()
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    observation = create_observation(membership=membership)
    processing = observation.processing
    processing.status = ObservationProcessing.Status.FAILED
    processing.last_error_code = "provider_timeout"
    processing.save(update_fields=["status", "last_error_code", "updated_at"])

    token = login(api_client, user=membership.user)
    response = api_client.get(
        processing_status_url(membership.establishment_id, observation.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == ObservationProcessing.Status.FAILED
    assert body["ux_status"] == "analysis_failed"
    assert body["last_error_code"] == "provider_timeout"
