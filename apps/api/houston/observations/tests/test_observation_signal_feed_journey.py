from __future__ import annotations

import pytest
from houston.establishments.models import EstablishmentMembership
from houston.observations.models import ObservationProcessing
from houston.signals.tasks import process_observation_task
from houston.signals.tests.pipeline_helpers import setup_hotel_taxonomy
from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.factories import create_establishment, create_membership
from houston.testing.pipeline import signal_feed_url
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

OBSERVATION_TEXT = (
    "La climatisation ne fonctionne plus dans le couloir principal du rez-de-chaussée."
)


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def observations_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/observations/"


def switch_establishment(api_client, *, token: str, establishment_id) -> str:
    response = api_client.post(
        "/api/v1/auth/switch_establishment/",
        {"establishment_id": str(establishment_id)},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 200
    return token


def test_submit_observation_fake_pipeline_surfaces_signal_in_general_feed(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    setup_hotel_taxonomy(membership.establishment)
    token = login(api_client, user=membership.user)

    submit_response = api_client.post(
        observations_url(membership.establishment_id),
        {"text": OBSERVATION_TEXT, "temporary_upload_ids": []},
        format="json",
        **auth_headers(token),
    )
    assert submit_response.status_code == 201
    observation_id = submit_response.json()["id"]
    assert submit_response.json()["processing_status"] == ObservationProcessing.Status.QUEUED

    process_observation_task.run(observation_id)

    feed_response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert feed_response.status_code == 200
    feed_items = feed_response.json()["items"]
    assert len(feed_items) == 1
    assert feed_items[0]["title"] == "Structured issue"
    assert "raw_text" not in feed_response.content.decode()

    processing = ObservationProcessing.objects.get(observation_id=observation_id)
    assert processing.status == ObservationProcessing.Status.PROCESSED
    assert processing.outcome == ObservationProcessing.Outcome.SIGNALS_CREATED


def test_submit_observation_signal_not_visible_in_other_establishment_feed(api_client):
    membership_a = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    establishment_a = membership_a.establishment
    establishment_b = create_establishment(name="Journey Hotel B")
    create_membership(
        establishment=establishment_b,
        user=membership_a.user,
        role=EstablishmentMembership.Role.STAFF,
    )
    setup_hotel_taxonomy(establishment_a)
    setup_hotel_taxonomy(establishment_b)
    token = login(api_client, user=membership_a.user)
    token = switch_establishment(
        api_client,
        token=token,
        establishment_id=establishment_a.id,
    )

    submit_response = api_client.post(
        observations_url(establishment_a.id),
        {"text": OBSERVATION_TEXT, "temporary_upload_ids": []},
        format="json",
        **auth_headers(token),
    )
    assert submit_response.status_code == 201
    observation_id = submit_response.json()["id"]

    process_observation_task.run(observation_id)

    feed_a = api_client.get(
        signal_feed_url(establishment_a.id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert feed_a.status_code == 200
    assert len(feed_a.json()["items"]) == 1

    token = switch_establishment(
        api_client,
        token=token,
        establishment_id=establishment_b.id,
    )
    feed_b = api_client.get(
        signal_feed_url(establishment_b.id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert feed_b.status_code == 200
    assert feed_b.json()["items"] == []
