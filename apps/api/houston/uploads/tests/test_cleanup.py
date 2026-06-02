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
from houston.uploads.services import cleanup_expired_uploads

pytestmark = pytest.mark.django_db


def test_cleanup_expired_uploads_deletes_validated_orphans():
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    establishment = Establishment.objects.create(
        name="Cleanup Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    user = User.objects.create_user(
        username=f"cleanup_{uuid.uuid4().hex[:8]}",
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
        expires_at=timezone.now() - timedelta(hours=1),
    )
    upload.file.save(
        "photo.png",
        SimpleUploadedFile("photo.png", b"\x89PNG\r\n\x1a\n", content_type="image/png"),
        save=False,
    )
    upload.save()

    deleted_count = cleanup_expired_uploads()
    assert deleted_count == 1
    upload.refresh_from_db()
    assert upload.status == TemporaryUpload.Status.DELETED
