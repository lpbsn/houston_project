from __future__ import annotations

import io
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from houston.chat.constants import (
    CHAT_ATTACHMENT_MAX_BYTES,
    CHAT_ATTACHMENTS_MAX_PER_MESSAGE,
    CHAT_UPLOAD_TTL_HOURS,
)
from houston.chat.exceptions import ChatNotFoundError, ChatPermissionError, ChatValidationError
from houston.chat.models import ChatMessageAttachment, ChatUpload
from houston.chat.permissions import can_access_chat, can_send_message
from houston.chat.selectors import get_conversation_for_participant
from houston.establishments.models import EstablishmentMembership
from houston.uploads.photo_keys import observation_photo_thumbnail_storage_key
from houston.uploads.photo_normalization import _encode_thumbnail
from houston.uploads.private_storage import (
    PRIVATE_MEDIA_BACKEND_S3,
    delete_private_media_object_idempotent,
    generate_private_media_presigned_get_url,
    generate_private_media_presigned_put_url,
    get_chat_private_media_storage,
)
from houston.uploads.validators import (
    ImageValidationError,
    UnsupportedImageTypeError,
    _canonical_from_detected_format,
    _detect_image_metadata,
    _ensure_heif_opener_registered,
)
from PIL import Image, ImageOps

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF"
_IMAGE_CONTENT_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
)


def chat_upload_storage_key(
    *,
    establishment_id: uuid.UUID,
    conversation_id: uuid.UUID,
    upload_id: uuid.UUID,
    filename: str,
) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    if len(extension) > 8 or "/" in extension:
        extension = "bin"
    return (
        f"establishments/{establishment_id}/chat/{conversation_id}/"
        f"{upload_id}/original.{extension}"
    )


def _ttl_hours() -> int:
    return int(getattr(settings, "HOUSTON_CHAT_UPLOAD_TTL_HOURS", CHAT_UPLOAD_TTL_HOURS))


def _presign_ttl_seconds() -> int:
    return int(getattr(settings, "HOUSTON_CHAT_UPLOAD_PRESIGN_TTL_SECONDS", 900))


def _is_s3_backend() -> bool:
    backend = getattr(settings, "HOUSTON_PRIVATE_MEDIA_BACKEND", "filesystem")
    return (backend or "").strip().lower() == PRIVATE_MEDIA_BACKEND_S3


def _read_storage_bytes(*, storage_key: str) -> bytes:
    storage = get_chat_private_media_storage()
    if not storage.exists(storage_key):
        raise ChatValidationError("Uploaded object is missing.")
    with storage.open(storage_key, "rb") as handle:
        payload = handle.read()
    return payload


def reserve_chat_upload(
    *,
    actor_membership: EstablishmentMembership,
    conversation_id: uuid.UUID,
    original_filename: str,
    content_type: str,
    size_bytes: int,
) -> ChatUpload:
    if not can_access_chat(actor_membership):
        raise ChatPermissionError()
    conversation = get_conversation_for_participant(
        establishment_id=actor_membership.establishment_id,
        conversation_id=conversation_id,
        membership_id=actor_membership.id,
    )
    if conversation is None:
        raise ChatNotFoundError()
    if not can_send_message(actor_membership, conversation):
        raise ChatPermissionError()
    if size_bytes < 1 or size_bytes > CHAT_ATTACHMENT_MAX_BYTES:
        raise ChatValidationError("Attachment exceeds the maximum size.")
    filename = (original_filename or "file").strip()[:255] or "file"
    declared_type = (content_type or "application/octet-stream").strip()[:120]
    upload = ChatUpload(
        establishment_id=actor_membership.establishment_id,
        conversation=conversation,
        uploaded_by_membership=actor_membership,
        original_filename=filename,
        declared_content_type=declared_type,
        declared_size_bytes=size_bytes,
        storage_key="",
        expires_at=timezone.now() + timedelta(hours=_ttl_hours()),
    )
    upload.save()
    upload.storage_key = chat_upload_storage_key(
        establishment_id=actor_membership.establishment_id,
        conversation_id=conversation.id,
        upload_id=upload.id,
        filename=filename,
    )
    upload.save(update_fields=["storage_key", "updated_at"])
    return upload


def get_reserved_chat_upload(
    *,
    actor_membership: EstablishmentMembership,
    upload_id: uuid.UUID,
) -> ChatUpload:
    if not can_access_chat(actor_membership):
        raise ChatPermissionError()
    upload = ChatUpload.objects.filter(
        id=upload_id,
        establishment_id=actor_membership.establishment_id,
        uploaded_by_membership_id=actor_membership.id,
    ).first()
    if upload is None:
        raise ChatNotFoundError()
    if upload.status != ChatUpload.Status.RESERVED:
        raise ChatValidationError("Upload can no longer accept content.")
    if upload.expires_at <= timezone.now():
        raise ChatValidationError("Upload reservation has expired.")
    conversation = get_conversation_for_participant(
        establishment_id=actor_membership.establishment_id,
        conversation_id=upload.conversation_id,
        membership_id=actor_membership.id,
    )
    if conversation is None:
        raise ChatNotFoundError()
    if not can_send_message(actor_membership, conversation):
        raise ChatPermissionError()
    return upload


def build_chat_upload_put_url(*, upload: ChatUpload, request=None) -> str:
    del request
    if _is_s3_backend():
        return generate_private_media_presigned_put_url(
            name=upload.storage_key,
            content_type=upload.declared_content_type or "application/octet-stream",
            storage=get_chat_private_media_storage(),
            expires_in=_presign_ttl_seconds(),
        )
    # Filesystem fallback is an authenticated Houston PUT to /content/, not a
    # presigned URL. Never return a Houston URL here — the client would PUT
    # without Authorization, matching the S3 contract and getting 401 locally.
    return ""


def store_chat_upload_content(*, upload: ChatUpload, payload: bytes) -> None:
    if upload.status != ChatUpload.Status.RESERVED:
        raise ChatValidationError("Upload can no longer accept content.")
    if len(payload) > CHAT_ATTACHMENT_MAX_BYTES:
        raise ChatValidationError("Attachment exceeds the maximum size.")
    storage = get_chat_private_media_storage()
    storage.save(upload.storage_key, ContentFile(payload))


def _detect_kind(payload: bytes) -> tuple[str, str]:
    if payload.startswith(_PDF_MAGIC):
        return ChatUpload.Kind.DOCUMENT, "application/pdf"
    _ensure_heif_opener_registered()
    try:
        metadata = _detect_image_metadata(payload)
        content_type, _extension = _canonical_from_detected_format(metadata.image_format)
    except UnsupportedImageTypeError as exc:
        raise ChatValidationError("Unsupported attachment type.") from exc
    except ImageValidationError as exc:
        raise ChatValidationError("Invalid attachment content.") from exc
    return ChatUpload.Kind.IMAGE, content_type


@transaction.atomic
def complete_chat_upload(
    *,
    actor_membership: EstablishmentMembership,
    upload_id: uuid.UUID,
) -> ChatUpload:
    upload = (
        ChatUpload.objects.select_for_update()
        .filter(
            id=upload_id,
            establishment_id=actor_membership.establishment_id,
            uploaded_by_membership_id=actor_membership.id,
        )
        .first()
    )
    if upload is None:
        raise ChatNotFoundError()
    if upload.status == ChatUpload.Status.VALIDATED:
        return upload
    if upload.status != ChatUpload.Status.RESERVED:
        raise ChatValidationError("Upload cannot be completed.")
    if upload.expires_at <= timezone.now():
        upload.status = ChatUpload.Status.EXPIRED
        upload.save(update_fields=["status", "updated_at"])
        raise ChatValidationError("Upload reservation has expired.")

    started = timezone.now()
    payload = _read_storage_bytes(storage_key=upload.storage_key)
    if len(payload) > CHAT_ATTACHMENT_MAX_BYTES:
        raise ChatValidationError("Attachment exceeds the maximum size.")
    kind, content_type = _detect_kind(payload)
    upload.kind = kind
    upload.content_type = content_type
    upload.size_bytes = len(payload)
    upload.status = ChatUpload.Status.VALIDATED
    upload.save(
        update_fields=["kind", "content_type", "size_bytes", "status", "updated_at"]
    )
    elapsed_ms = int((timezone.now() - started).total_seconds() * 1000)
    logger.info(
        "chat_upload_complete",
        extra={
            "event": "chat_upload_complete",
            "upload_id": str(upload.id),
            "conversation_id": str(upload.conversation_id),
            "kind": kind,
            "elapsed_ms": elapsed_ms,
        },
    )
    if kind == ChatUpload.Kind.IMAGE:
        from houston.chat.tasks import generate_chat_upload_thumbnail_task

        transaction.on_commit(
            lambda: generate_chat_upload_thumbnail_task.delay(str(upload.id))
        )
    return upload


def generate_chat_upload_thumbnail(*, upload_id: uuid.UUID) -> None:
    upload = ChatUpload.objects.filter(id=upload_id).first()
    if upload is None or upload.kind != ChatUpload.Kind.IMAGE:
        return
    try:
        payload = _read_storage_bytes(storage_key=upload.storage_key)
        _ensure_heif_opener_registered()
        with Image.open(io.BytesIO(payload)) as opened:
            opened.load()
            transposed = ImageOps.exif_transpose(opened)
            image = (transposed or opened).copy()
        thumbnail = _encode_thumbnail(image)
        thumb_key = observation_photo_thumbnail_storage_key(upload.storage_key)
        storage = get_chat_private_media_storage()
        storage.save(thumb_key, thumbnail.content_file)
        upload.thumbnail_storage_key = thumb_key
        upload.save(update_fields=["thumbnail_storage_key", "updated_at"])
    except Exception as exc:
        logger.warning(
            "chat_upload_thumbnail_failed",
            extra={
                "event": "chat_upload_thumbnail_failed",
                "upload_id": str(upload_id),
                "exception_class": type(exc).__name__,
            },
        )
        raise


def lock_validated_uploads_for_message(
    *,
    actor_membership: EstablishmentMembership,
    conversation_id: uuid.UUID,
    attachment_ids: list[uuid.UUID],
    allow_linked: bool = False,
) -> list[ChatUpload]:
    unique_ids = list(dict.fromkeys(attachment_ids))
    if len(unique_ids) > CHAT_ATTACHMENTS_MAX_PER_MESSAGE:
        raise ChatValidationError(
            f"A message accepts at most {CHAT_ATTACHMENTS_MAX_PER_MESSAGE} attachments."
        )
    uploads = list(
        ChatUpload.objects.select_for_update()
        .filter(id__in=unique_ids)
        .order_by("id")
    )
    if len(uploads) != len(unique_ids):
        raise ChatValidationError("One or more attachments are invalid.")
    for upload in uploads:
        if upload.uploaded_by_membership_id != actor_membership.id:
            raise ChatValidationError("Attachment does not belong to the sender.")
        if upload.conversation_id != conversation_id:
            raise ChatValidationError("Attachment does not belong to this conversation.")
        if upload.status == ChatUpload.Status.LINKED:
            if allow_linked:
                continue
            raise ChatValidationError("Attachment has already been used.")
        if upload.status != ChatUpload.Status.VALIDATED:
            raise ChatValidationError("Attachment is not ready.")
        if upload.expires_at <= timezone.now():
            raise ChatValidationError("Attachment reservation has expired.")
    uploads_by_id = {upload.id: upload for upload in uploads}
    return [uploads_by_id[upload_id] for upload_id in unique_ids]


def link_uploads_to_message(*, message, uploads: list[ChatUpload]) -> None:
    now = timezone.now()
    attachments = []
    for index, upload in enumerate(uploads):
        upload.status = ChatUpload.Status.LINKED
        upload.linked_at = now
        upload.save(update_fields=["status", "linked_at", "updated_at"])
        attachments.append(
            ChatMessageAttachment(
                message=message,
                upload=upload,
                position=index,
                kind=upload.kind,
                content_type=upload.content_type,
                size_bytes=upload.size_bytes or 0,
                original_filename=upload.original_filename,
            )
        )
    if attachments:
        ChatMessageAttachment.objects.bulk_create(attachments)


def chat_object_keys_for_uploads(uploads: list[ChatUpload]) -> list[str]:
    keys: list[str] = []
    for upload in uploads:
        if upload.storage_key:
            keys.append(upload.storage_key)
        if upload.thumbnail_storage_key:
            keys.append(upload.thumbnail_storage_key)
    return keys


def delete_chat_storage_keys(keys: list[str]) -> None:
    storage = get_chat_private_media_storage()
    for key in keys:
        try:
            delete_private_media_object_idempotent(storage_key=key, storage=storage)
        except Exception as exc:
            logger.warning(
                "chat_storage_delete_failed",
                extra={
                    "event": "chat_storage_delete_failed",
                    "exception_class": type(exc).__name__,
                },
            )
            raise


def generate_chat_attachment_presigned_get(*, storage_key: str) -> str:
    return generate_private_media_presigned_get_url(
        name=storage_key,
        storage=get_chat_private_media_storage(),
        expires_in=int(settings.HOUSTON_OBSERVATION_MEDIA_S3_PRESIGN_TTL_SECONDS),
    )
