from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from houston.accounts.models import User
from houston.establishments.models import Establishment
from houston.organizations.models import Organization
from houston.uploads.models import TemporaryUpload

pytestmark = pytest.mark.django_db


def _establishment() -> Establishment:
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name="Upload Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )


def test_temporary_upload_persists_private_file():
    establishment = _establishment()
    user = User.objects.create_user(
        username=f"uploader_{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        password="secret-password-12",
        status=User.Status.ACTIVE,
    )
    upload = TemporaryUpload(
        establishment=establishment,
        uploaded_by=user,
        content_type="image/png",
        stored_extension="png",
        size_bytes=4,
        expires_at=timezone.now() + timedelta(hours=24),
    )
    upload.file.save(
        "ignored.png",
        SimpleUploadedFile("ignored.png", b"\x89PNG\r\n\x1a\n", content_type="image/png"),
        save=False,
    )
    upload.save()

    upload.refresh_from_db()
    assert upload.file.name
    assert str(establishment.id) in upload.file.name
