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
from houston.uploads.photo_normalization import normalize_observation_photo
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
    normalized = normalize_observation_photo(raw_bytes=raw_bytes)
    expires_at = timezone.now() + timedelta(hours=settings.HOUSTON_TEMPORARY_UPLOAD_TTL_HOURS)

    upload = TemporaryUpload(
        establishment=establishment,
        uploaded_by=uploaded_by,
        content_type=normalized.content_type,
        stored_extension=normalized.stored_extension,
        size_bytes=normalized.size_bytes,
        status=TemporaryUpload.Status.VALIDATED,
        expires_at=expires_at,
    )
    upload.file.save(
        f"photo.{normalized.stored_extension}",
        normalized.content_file,
        save=False,
    )
    upload.save()
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
        upload.file.delete(save=False)
    upload.status = TemporaryUpload.Status.DELETED
    upload.save(update_fields=["status", "updated_at"])


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
            upload.file.delete(save=False)
        upload.status = TemporaryUpload.Status.DELETED
        upload.save(update_fields=["status", "updated_at"])
        deleted_count += 1
    return deleted_count
