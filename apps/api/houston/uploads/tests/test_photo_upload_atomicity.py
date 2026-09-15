from __future__ import annotations

import io
import uuid
from pathlib import Path

import pytest
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from houston.accounts.models import User
from houston.establishments.models import Establishment
from houston.organizations.models import Organization
from houston.uploads.models import TemporaryUpload
from houston.uploads.photo_keys import observation_photo_thumbnail_storage_key
from houston.uploads.private_storage import get_private_media_storage
from houston.uploads.services import create_temporary_photo_upload, delete_temporary_upload
from PIL import Image

pytestmark = pytest.mark.django_db


def _jpeg_upload() -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (48, 32), color="orange").save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile("photo.jpg", buffer.read(), content_type="image/jpeg")


def _actor_and_establishment():
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    establishment = Establishment.objects.create(
        name="Atomic Upload Hotel",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    user = User.objects.create_user(
        username=f"atomic_{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        password="secret-password-12",
        status=User.Status.ACTIVE,
    )
    return establishment, user


def test_create_temporary_photo_upload_writes_principal_and_thumbnail():
    establishment, user = _actor_and_establishment()
    upload = create_temporary_photo_upload(
        establishment=establishment,
        uploaded_by=user,
        uploaded_file=_jpeg_upload(),
        declared_content_type="image/jpeg",
    )
    storage = get_private_media_storage()
    thumbnail_key = observation_photo_thumbnail_storage_key(upload.file.name)
    assert storage.exists(upload.file.name)
    assert storage.exists(thumbnail_key)
    assert TemporaryUpload.objects.filter(
        id=upload.id,
        status=TemporaryUpload.Status.VALIDATED,
    ).exists()


def test_thumb_save_failure_leaves_no_row_and_no_storage_objects(monkeypatch):
    establishment, user = _actor_and_establishment()
    storage = get_private_media_storage()
    root = Path(storage._inner.location)
    before = {path for path in root.rglob("*") if path.is_file()} if root.exists() else set()
    original_save = FileSystemStorage._save

    def fail_thumbnail(self, name, content):
        if str(name).endswith(".thumb.jpg"):
            raise RuntimeError("thumb failed")
        return original_save(self, name, content)

    monkeypatch.setattr(FileSystemStorage, "_save", fail_thumbnail)

    with pytest.raises(RuntimeError, match="thumb failed"):
        create_temporary_photo_upload(
            establishment=establishment,
            uploaded_by=user,
            uploaded_file=_jpeg_upload(),
            declared_content_type="image/jpeg",
        )

    assert not TemporaryUpload.objects.filter(establishment=establishment).exists()
    after = {path for path in root.rglob("*") if path.is_file()} if root.exists() else set()
    assert after == before


def test_delete_temporary_upload_removes_principal_and_thumbnail():
    establishment, user = _actor_and_establishment()
    upload = create_temporary_photo_upload(
        establishment=establishment,
        uploaded_by=user,
        uploaded_file=_jpeg_upload(),
        declared_content_type="image/jpeg",
    )
    storage = get_private_media_storage()
    principal_key = upload.file.name
    thumbnail_key = observation_photo_thumbnail_storage_key(principal_key)

    delete_temporary_upload(
        establishment_id=establishment.id,
        upload_id=upload.id,
        actor=user,
    )

    upload.refresh_from_db()
    assert upload.status == TemporaryUpload.Status.DELETED
    assert not storage.exists(principal_key)
    assert not storage.exists(thumbnail_key)
