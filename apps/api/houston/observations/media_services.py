from __future__ import annotations

import uuid
from pathlib import Path

from django.db import transaction

from houston.observations.models import ObservationMedia
from houston.uploads.models import TemporaryUpload
from houston.uploads.private_storage import get_private_media_storage


def _delete_storage_file_idempotent(*, storage_key: str) -> None:
    if not storage_key:
        return
    storage = get_private_media_storage()
    try:
        if storage.exists(storage_key):
            storage.delete(storage_key)
    except OSError:
        return
    media_root = Path(storage.location)
    file_path = media_root / storage_key
    if file_path.is_file():
        file_path.unlink(missing_ok=True)


def _schedule_storage_file_deletion(*, storage_key: str) -> None:
    transaction.on_commit(lambda: _delete_storage_file_idempotent(storage_key=storage_key))


@transaction.atomic
def delete_observation_media_permanently(*, media: ObservationMedia) -> None:
    upload = media.temporary_upload
    storage_key = media.storage_key or (upload.file.name if upload.file else "")

    media.delete()

    if upload.status != TemporaryUpload.Status.DELETED:
        upload.status = TemporaryUpload.Status.DELETED
        upload.save(update_fields=["status", "updated_at"])

    if storage_key:
        _schedule_storage_file_deletion(storage_key=storage_key)


def delete_all_observation_media(*, observation_id: uuid.UUID) -> None:
    media_items = list(
        ObservationMedia.objects.filter(observation_id=observation_id).select_related(
            "temporary_upload",
        )
    )
    for media in media_items:
        delete_observation_media_permanently(media=media)
