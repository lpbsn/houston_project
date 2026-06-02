from __future__ import annotations

import io
import uuid
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from houston.accounts.models import User
from houston.ai.transcription import TranscriptionResult
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.observations.models import Observation, ObservationProcessing
from houston.organizations.models import Organization
from PIL import Image
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def create_user(*, username: str) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )


def create_establishment(*, status: str = Establishment.Status.ACTIVE) -> Establishment:
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name="Observation Hotel",
        organization=organization,
        status=status,
    )


def create_membership(*, user: User, establishment: Establishment) -> EstablishmentMembership:
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )


def login(api_client: APIClient, *, user: User) -> str:
    csrf = api_client.get("/api/v1/auth/csrf/").cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": user.email, "password": TEST_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _png_upload() -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile("photo.png", buffer.read(), content_type="image/png")


def observations_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/observations/"


def uploads_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/temporary-uploads/"


def transcriptions_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/transcriptions/"


def test_submit_observation_persists_raw_text_without_api_exposure(api_client):
    establishment = create_establishment()
    staff = create_user(username="obs_staff")
    create_membership(user=staff, establishment=establishment)
    token = login(api_client, user=staff)

    submitted_text = "Fuite d'eau visible au niveau du couloir principal."
    response = api_client.post(
        observations_url(establishment.id),
        {"text": submitted_text, "temporary_upload_ids": []},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body.keys()) == {
        "id",
        "submitted_at",
        "media_count",
        "processing_status",
    }
    assert body["processing_status"] == ObservationProcessing.Status.QUEUED
    assert "text" not in body
    assert "raw_text" not in body

    observation = Observation.objects.get(id=body["id"])
    assert observation.raw_text == submitted_text
    assert observation.processing.status == ObservationProcessing.Status.QUEUED


def test_submit_rejects_short_text(api_client):
    establishment = create_establishment()
    staff = create_user(username="obs_short")
    create_membership(user=staff, establishment=establishment)
    token = login(api_client, user=staff)

    response = api_client.post(
        observations_url(establishment.id),
        {"text": "court", "temporary_upload_ids": []},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["detail"] == "Request validation failed."
    assert "errors" in body
    assert "text" in body["errors"]


def test_submit_with_temporary_photo_upload(api_client):
    establishment = create_establishment()
    staff = create_user(username="obs_photo")
    create_membership(user=staff, establishment=establishment)
    token = login(api_client, user=staff)

    upload_response = api_client.post(
        uploads_url(establishment.id),
        {"file": _png_upload()},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert upload_response.status_code == 201
    upload_id = upload_response.json()["id"]
    assert "url" not in upload_response.json()

    submit_response = api_client.post(
        observations_url(establishment.id),
        {
            "text": "Tache visible sur le mur près de la réception.",
            "temporary_upload_ids": [upload_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert submit_response.status_code == 201
    assert submit_response.json()["media_count"] == 1


@patch("houston.uploads.api.transcription_views.transcribe_audio_file")
def test_transcription_returns_editable_text_without_persisting_audio(
    mock_transcribe,
    api_client,
):
    establishment = create_establishment()
    staff = create_user(username="obs_audio")
    create_membership(user=staff, establishment=establishment)
    token = login(api_client, user=staff)

    mock_transcribe.return_value = TranscriptionResult(
        text="Il y a une odeur suspecte dans le couloir.",
        language="fr",
        correlation_id=uuid.uuid4(),
        provider="openai",
        model="gpt-4o-transcribe",
        latency_ms=120,
    )

    audio = SimpleUploadedFile("note.webm", b"fake-audio-bytes", content_type="audio/webm")
    response = api_client.post(
        transcriptions_url(establishment.id),
        {"file": audio},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["text"].startswith("Il y a")
    assert "raw_text" not in body
