from __future__ import annotations

import io
import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.organizations.models import Organization
from houston.uploads.models import TemporaryUpload
from PIL import Image
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _establishment(*, name: str = "JPEG Upload Hotel") -> Establishment:
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name=name,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )


def _create_staff(
    *,
    establishment: Establishment,
    username_prefix: str = "staff",
) -> tuple[User, str]:
    user = User.objects.create_user(
        username=f"{username_prefix}_{uuid.uuid4().hex[:8]}",
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
    return user, TEST_PASSWORD


def _login(api_client: APIClient, *, user: User) -> str:
    csrf = api_client.get("/api/v1/auth/csrf/").cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": user.email, "password": TEST_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def _login_for_establishment(api_client: APIClient, establishment: Establishment) -> str:
    user, _ = _create_staff(establishment=establishment)
    return _login(api_client, user=user)


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


def upload_detail_url(establishment_id, upload_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/temporary-uploads/{upload_id}/"


def observations_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/observations/"


def _create_upload(api_client: APIClient, *, establishment: Establishment, token: str) -> str:
    response = api_client.post(
        uploads_url(establishment.id),
        {"file": _jpeg_upload()},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_requires_authentication(api_client):
    establishment = _establishment()

    response = api_client.post(
        uploads_url(establishment.id),
        {"file": _jpeg_upload()},
        format="multipart",
    )

    assert response.status_code == 401


def test_create_returns_403_for_foreign_establishment(api_client):
    home = _establishment(name="Home Hotel")
    foreign = _establishment(name="Foreign Hotel")
    user, _ = _create_staff(establishment=home, username_prefix="home_staff")
    token = _login(api_client, user=user)

    response = api_client.post(
        uploads_url(foreign.id),
        {"file": _jpeg_upload()},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 403


def test_delete_requires_authentication(api_client):
    establishment = _establishment()
    token = _login_for_establishment(api_client, establishment)
    upload_id = _create_upload(api_client, establishment=establishment, token=token)

    response = api_client.delete(upload_detail_url(establishment.id, upload_id))

    assert response.status_code == 401


def test_delete_returns_403_for_foreign_establishment(api_client):
    home = _establishment(name="Delete Home")
    foreign = _establishment(name="Delete Foreign")
    user, _ = _create_staff(establishment=home, username_prefix="delete_home")
    token = _login(api_client, user=user)
    upload_id = _create_upload(api_client, establishment=home, token=token)

    response = api_client.delete(
        upload_detail_url(foreign.id, upload_id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 403


def test_delete_returns_404_for_other_users_upload(api_client):
    establishment = _establishment()
    owner, _ = _create_staff(establishment=establishment, username_prefix="upload_owner")
    intruder, _ = _create_staff(establishment=establishment, username_prefix="upload_intruder")
    owner_token = _login(api_client, user=owner)
    intruder_token = _login(api_client, user=intruder)
    upload_id = _create_upload(api_client, establishment=establishment, token=owner_token)

    response = api_client.delete(
        upload_detail_url(establishment.id, upload_id),
        HTTP_AUTHORIZATION=f"Bearer {intruder_token}",
    )

    assert response.status_code == 404


def test_delete_own_unlinked_upload(api_client):
    establishment = _establishment()
    user, _ = _create_staff(establishment=establishment)
    token = _login(api_client, user=user)
    upload_id = _create_upload(api_client, establishment=establishment, token=token)

    response = api_client.delete(
        upload_detail_url(establishment.id, upload_id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 204
    upload = TemporaryUpload.objects.get(id=upload_id)
    assert upload.status == TemporaryUpload.Status.DELETED


def test_linked_upload_cannot_be_deleted(api_client):
    establishment = _establishment()
    user, _ = _create_staff(establishment=establishment)
    token = _login(api_client, user=user)
    upload_id = _create_upload(api_client, establishment=establishment, token=token)

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

    delete_response = api_client.delete(
        upload_detail_url(establishment.id, upload_id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert delete_response.status_code == 400
    assert delete_response.json()["code"] == "upload_not_deletable"


def test_upload_transitions_to_linked_on_observation_submit(api_client):
    establishment = _establishment()
    user, _ = _create_staff(establishment=establishment)
    token = _login(api_client, user=user)
    upload_id = _create_upload(api_client, establishment=establishment, token=token)

    submit_response = api_client.post(
        observations_url(establishment.id),
        {
            "text": "Fuite d'eau visible au niveau du couloir principal.",
            "temporary_upload_ids": [upload_id],
        },
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert submit_response.status_code == 201
    assert submit_response.json()["media_count"] == 1

    upload = TemporaryUpload.objects.get(id=upload_id)
    assert upload.status == TemporaryUpload.Status.LINKED
    assert upload.linked_at is not None


def test_api_accepts_valid_jpeg_named_img_0299(api_client):
    establishment = _establishment()
    token = _login_for_establishment(api_client, establishment)

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
    token = _login_for_establishment(api_client, establishment)

    response = api_client.post(
        uploads_url(establishment.id),
        {"file": _jpeg_upload(filename="IMG_0300.jpg")},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201


def test_api_accepts_valid_jpeg_with_octet_stream_content_type(api_client):
    establishment = _establishment()
    token = _login_for_establishment(api_client, establishment)

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
    token = _login_for_establishment(api_client, establishment)

    response = api_client.post(
        uploads_url(establishment.id),
        {"file": _jpeg_upload(content_type="")},
        format="multipart",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )

    assert response.status_code == 201


def test_api_accepts_jpeg_content_with_png_filename(api_client):
    establishment = _establishment()
    token = _login_for_establishment(api_client, establishment)

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
    token = _login_for_establishment(api_client, establishment)

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
    token = _login_for_establishment(api_client, establishment)

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
