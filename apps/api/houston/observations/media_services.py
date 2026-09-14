from __future__ import annotations

import logging
import uuid

from django.db import transaction

from houston.observations.models import ObservationMedia
from houston.uploads.models import TemporaryUpload
from houston.uploads.private_storage import get_private_media_storage

logger = logging.getLogger(__name__)


def _is_missing_storage_object_error(exc: BaseException) -> bool:
    if isinstance(exc, FileNotFoundError):
        return True
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return False
    error = response.get("Error") or {}
    code = str(error.get("Code") or "")
    return code in {"404", "NoSuchKey", "NotFound"}


def _delete_storage_file_idempotent(*, storage_key: str) -> None:
    if not storage_key:
        return
    storage = get_private_media_storage()
    try:
        storage.delete(storage_key)
    except Exception as exc:
        if _is_missing_storage_object_error(exc):
            return
        logger.warning(
            "storage_file_delete_failed",
            extra={
                "event": "storage_file_delete_failed",
                "storage_key": storage_key,
                "exception_class": type(exc).__name__,
            },
        )


def _schedule_storage_file_deletion(*, storage_key: str) -> None:
    transaction.on_commit(lambda: _delete_storage_file_idempotent(storage_key=storage_key))


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
        _schedule_storage_file_deletion(storage_key=storage_key)


def delete_all_observation_media(*, observation_id: uuid.UUID) -> None:
    media_items = list(
        ObservationMedia.objects.filter(observation_id=observation_id).select_related(
            "temporary_upload",
        )
    )
    for media in media_items:
        delete_observation_media_permanently(media=media)
