from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from houston.accounts.models import User
from houston.ai.transcription import (
    TranscriptionResult,
    TranscriptionServiceError,
)
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.organizations.models import Organization
from houston.uploads.models import TemporaryUpload
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _establishment() -> Establishment:
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name="Transcription Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )


def _staff(api_client: APIClient, establishment: Establishment) -> tuple[User, str]:
    user = User.objects.create_user(
        username=f"staff_{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    csrf = api_client.get("/api/v1/auth/csrf/").cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": user.email, "password": TEST_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    return user, response.json()["access_token"]


def transcriptions_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/transcriptions/"


def test_transcription_does_not_create_temporary_upload(api_client):
    establishment = _establishment()
    _, token = _staff(api_client, establishment)

    audio = SimpleUploadedFile("note.webm", b"fake-audio", content_type="audio/webm")
    with patch(
        "houston.uploads.api.transcription_views.transcribe_audio_file",
        return_value=TranscriptionResult(
            text="Problème de climatisation dans le couloir.",
            language="fr",
            correlation_id=uuid.uuid4(),
            provider="openai",
            model="gpt-4o-transcribe",
            latency_ms=50,
        ),
    ):
        response = api_client.post(
            transcriptions_url(establishment.id),
            {"file": audio},
            format="multipart",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    assert response.status_code == 200
    assert TemporaryUpload.objects.count() == 0


@patch("houston.uploads.api.transcription_views.transcribe_audio_file")
def test_transcription_deletes_temp_file_on_provider_failure(
    mock_transcribe,
    api_client,
    tmp_path,
    monkeypatch,
):
    establishment = _establishment()
    _, token = _staff(api_client, establishment)
    created_paths: list[Path] = []
    original_named = __import__("tempfile").NamedTemporaryFile

    def tracking_named(*args, **kwargs):
        handle = original_named(*args, **kwargs)
        created_paths.append(Path(handle.name))
        return handle

    monkeypatch.setattr(
        "houston.uploads.api.transcription_views.tempfile.NamedTemporaryFile",
        tracking_named,
    )
    mock_transcribe.side_effect = TranscriptionServiceError("failed")

    audio = SimpleUploadedFile("note.webm", b"fake-audio", content_type="audio/webm")
    response = api_client.post(
        transcriptions_url(establishment.id),
        {"file": audio},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 400
    assert created_paths
    assert all(not path.exists() for path in created_paths)
