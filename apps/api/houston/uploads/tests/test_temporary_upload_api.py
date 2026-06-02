from __future__ import annotations

import io
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.organizations.models import Organization
from PIL import Image
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
        name="JPEG Upload Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )


def _login(api_client: APIClient, establishment: Establishment) -> str:
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
    return response.json()["access_token"]


def _jpeg_upload(
    *,
    filename: str = "IMG_0299.jpeg",
    content_type: str = "image/jpeg",
) -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color="yellow").save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile(filename, buffer.read(), content_type=content_type)


def uploads_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/temporary-uploads/"


def test_api_accepts_valid_jpeg_named_img_0299(api_client):
    establishment = _establishment()
    token = _login(api_client, establishment)

    response = api_client.post(
        uploads_url(establishment.id),
        {"file": _jpeg_upload(filename="IMG_0299.jpeg")},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "validated"
    assert "url" not in body


def test_api_accepts_valid_jpg_filename(api_client):
    establishment = _establishment()
    token = _login(api_client, establishment)

    response = api_client.post(
        uploads_url(establishment.id),
        {"file": _jpeg_upload(filename="IMG_0300.jpg")},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201


def test_api_accepts_valid_jpeg_with_octet_stream_content_type(api_client):
    establishment = _establishment()
    token = _login(api_client, establishment)

    response = api_client.post(
        uploads_url(establishment.id),
        {"file": _jpeg_upload(content_type="application/octet-stream")},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "validated"


def test_api_accepts_valid_jpeg_with_missing_content_type(api_client):
    establishment = _establishment()
    token = _login(api_client, establishment)

    response = api_client.post(
        uploads_url(establishment.id),
        {"file": _jpeg_upload(content_type="")},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201


def test_api_accepts_jpeg_content_with_png_filename(api_client):
    establishment = _establishment()
    token = _login(api_client, establishment)

    response = api_client.post(
        uploads_url(establishment.id),
        {"file": _jpeg_upload(filename="IMG_0301.png", content_type="image/png")},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201
    assert response.json()["status"] == "validated"


def test_api_rejects_audio_file_for_temporary_upload(api_client):
    establishment = _establishment()
    token = _login(api_client, establishment)

    response = api_client.post(
        uploads_url(establishment.id),
        {"file": SimpleUploadedFile("note.webm", b"fake-audio", content_type="audio/webm")},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] in {"invalid_image", "unsupported_image_type"}
    assert isinstance(body["detail"], str)


def test_api_rejects_missing_file_for_temporary_upload(api_client):
    establishment = _establishment()
    token = _login(api_client, establishment)

    response = api_client.post(
        uploads_url(establishment.id),
        {},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 400
    assert response.json() == {
        "code": "missing_file",
        "detail": "A file is required.",
    }
