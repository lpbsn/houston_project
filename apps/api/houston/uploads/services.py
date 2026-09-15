from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from houston.accounts.models import User
from houston.establishments.models import Establishment
from houston.uploads.exceptions import UploadNotDeletableError, UploadNotFoundError
from houston.uploads.models import TemporaryUpload
from houston.uploads.photo_keys import (
    observation_photo_storage_keys,
    observation_photo_thumbnail_storage_key,
)
from houston.uploads.photo_normalization import normalize_observation_photo_pair
from houston.uploads.private_storage import (
    delete_private_media_object_idempotent,
)
from houston.uploads.validators import validate_observation_photo_upload


def create_temporary_photo_upload(
    *,
    establishment: Establishment,
    uploaded_by: User,
    uploaded_file,
    declared_content_type: str | None,
) -> TemporaryUpload:
    validate_observation_photo_upload(
        uploaded_file=uploaded_file,
        declared_content_type=declared_content_type,
    )
    uploaded_file.seek(0)
    raw_bytes = uploaded_file.read()
    uploaded_file.seek(0)
    principal, thumbnail = normalize_observation_photo_pair(raw_bytes=raw_bytes)
    expires_at = timezone.now() + timedelta(hours=settings.HOUSTON_TEMPORARY_UPLOAD_TTL_HOURS)

    upload = TemporaryUpload(
        establishment=establishment,
        uploaded_by=uploaded_by,
        content_type=principal.content_type,
        stored_extension=principal.stored_extension,
        size_bytes=principal.size_bytes,
        status=TemporaryUpload.Status.VALIDATED,
        expires_at=expires_at,
    )
    written_keys: list[str] = []
    try:
        upload.file.save(
            f"photo.{principal.stored_extension}",
            principal.content_file,
            save=False,
        )
        written_keys.append(upload.file.name)
        thumbnail_key = observation_photo_thumbnail_storage_key(upload.file.name)
        stored_thumbnail_key = (
            upload.file.storage._save(thumbnail_key, thumbnail.content_file) or thumbnail_key
        )
        written_keys.append(stored_thumbnail_key)
        upload.save()
    except Exception:
        for storage_key in written_keys:
            delete_private_media_object_idempotent(storage_key=storage_key)
        raise
    return upload


def delete_temporary_upload(
    *,
    establishment_id: uuid.UUID,
    upload_id: uuid.UUID,
    actor: User,
) -> None:
    upload = (
        TemporaryUpload.objects.filter(
            id=upload_id,
            establishment_id=establishment_id,
        )
        .select_related("establishment")
        .first()
    )
    if upload is None:
        raise UploadNotFoundError("Upload not found.")
    if upload.uploaded_by_id != actor.id:
        raise UploadNotFoundError("Upload not found.")
    if upload.status == TemporaryUpload.Status.LINKED:
        raise UploadNotDeletableError("Upload is already linked.")
    if upload.status == TemporaryUpload.Status.DELETED:
        return

    if upload.file:
        _delete_temporary_upload_storage(upload)
    upload.status = TemporaryUpload.Status.DELETED
    upload.save(update_fields=["status", "updated_at"])


def _delete_temporary_upload_storage(upload: TemporaryUpload) -> None:
    storage_key = upload.file.name if upload.file else ""
    upload.file.delete(save=False)
    for key in observation_photo_storage_keys(storage_key):
        if key == storage_key:
            continue
        delete_private_media_object_idempotent(storage_key=key)


@transaction.atomic
def cleanup_expired_uploads(*, now=None) -> int:
    current_time = now or timezone.now()
    expired_uploads = TemporaryUpload.objects.filter(
        status=TemporaryUpload.Status.VALIDATED,
        expires_at__lt=current_time,
    )
    deleted_count = 0
    for upload in expired_uploads.iterator():
        if upload.file:
            _delete_temporary_upload_storage(upload)
        upload.status = TemporaryUpload.Status.DELETED
        upload.save(update_fields=["status", "updated_at"])
        deleted_count += 1
    return deleted_count
