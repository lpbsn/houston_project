from __future__ import annotations

import uuid

from django.db import transaction

from houston.observations.models import ObservationMedia
from houston.uploads.models import TemporaryUpload
from houston.uploads.photo_keys import observation_photo_storage_keys
from houston.uploads.private_storage import delete_private_media_object_idempotent


def _delete_storage_file_idempotent(*, storage_key: str) -> None:
    delete_private_media_object_idempotent(storage_key=storage_key)


def schedule_storage_files_deletion(*, storage_keys: list[str]) -> None:
    keys = [key for key in storage_keys if key]
    if not keys:
        return

    def _delete_all() -> None:
        for storage_key in keys:
            _delete_storage_file_idempotent(storage_key=storage_key)

    transaction.on_commit(_delete_all)


@transaction.atomic
def delete_observation_media_permanently(*, media: ObservationMedia) -> None:
    upload = media.temporary_upload
    storage_key = media.storage_key or (upload.file.name if upload.file else "")

    media.delete()

    if upload.status != TemporaryUpload.Status.DELETED:
        upload.status = TemporaryUpload.Status.DELETED
        upload.save(update_fields=["status", "updated_at"])

    if storage_key:
        schedule_storage_files_deletion(storage_keys=observation_photo_storage_keys(storage_key))


def delete_all_observation_media(*, observation_id: uuid.UUID) -> None:
    media_items = list(
        ObservationMedia.objects.filter(observation_id=observation_id).select_related(
            "temporary_upload",
        )
    )
    for media in media_items:
        delete_observation_media_permanently(media=media)
