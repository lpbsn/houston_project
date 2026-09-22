from __future__ import annotations

import io
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageOps

from houston.action_plans.constants import (
    ACTIVE_EXECUTION_STATUSES,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
)
from houston.action_plans.models import ActionPlanExecution
from houston.comments.constants import (
    ACTION_PLAN_COMMENT_ATTACHMENT_MAX_BYTES,
    ACTION_PLAN_COMMENT_ATTACHMENTS_MAX_PER_COMMENT,
    ACTION_PLAN_COMMENT_PURGE_BATCH_SIZE,
    ACTION_PLAN_COMMENT_RETENTION_DAYS,
    ACTION_PLAN_COMMENT_UPLOAD_TTL_HOURS,
    ATTACHMENT_ALREADY_USED_ERROR_DETAIL,
    ATTACHMENT_EXPIRED_ERROR_DETAIL,
    ATTACHMENT_INVALID_CONTENT_ERROR_DETAIL,
    ATTACHMENT_INVALID_ERROR_DETAIL,
    ATTACHMENT_MAX_COUNT_ERROR_DETAIL,
    ATTACHMENT_MISSING_OBJECT_ERROR_DETAIL,
    ATTACHMENT_NOT_OWNED_ERROR_DETAIL,
    ATTACHMENT_NOT_READY_ERROR_DETAIL,
    ATTACHMENT_TOO_LARGE_ERROR_DETAIL,
    ATTACHMENT_UNSUPPORTED_TYPE_ERROR_DETAIL,
    ATTACHMENT_WRONG_EXECUTION_ERROR_DETAIL,
    ATTACHMENTS_NOT_ALLOWED_ERROR_DETAIL,
)
from houston.comments.exceptions import CommentValidationError
from houston.comments.models import ActionPlanCommentAttachment, ActionPlanCommentUpload, Comment
from houston.establishments.models import EstablishmentMembership
from houston.uploads.photo_keys import observation_photo_thumbnail_storage_key
from houston.uploads.photo_normalization import _encode_thumbnail
from houston.uploads.private_storage import (
    PRIVATE_MEDIA_BACKEND_S3,
    _is_missing_storage_object_error,
    generate_private_media_presigned_get_url,
    generate_private_media_presigned_put_url,
    get_action_plan_comment_private_media_storage,
)
from houston.uploads.validators import (
    ImageValidationError,
    UnsupportedImageTypeError,
    _canonical_from_detected_format,
    _detect_image_metadata,
    _ensure_heif_opener_registered,
)

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF"


def action_plan_comment_upload_storage_key(
    *,
    establishment_id: uuid.UUID,
    execution_id: uuid.UUID,
    upload_id: uuid.UUID,
    filename: str,
) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    if len(extension) > 8 or "/" in extension:
        extension = "bin"
    return (
        f"establishments/{establishment_id}/action-plans/{execution_id}/"
        f"{upload_id}/original.{extension}"
    )


def _ttl_hours() -> int:
    return int(
        getattr(
            settings,
            "HOUSTON_ACTION_PLAN_COMMENT_UPLOAD_TTL_HOURS",
            ACTION_PLAN_COMMENT_UPLOAD_TTL_HOURS,
        )
    )


def _presign_ttl_seconds() -> int:
    return int(
        getattr(settings, "HOUSTON_ACTION_PLAN_COMMENT_UPLOAD_PRESIGN_TTL_SECONDS", 900)
    )


def _retention_days() -> int:
    return int(
        getattr(
            settings,
            "HOUSTON_ACTION_PLAN_COMMENT_RETENTION_DAYS",
            ACTION_PLAN_COMMENT_RETENTION_DAYS,
        )
    )


def _is_s3_backend() -> bool:
    backend = getattr(settings, "HOUSTON_PRIVATE_MEDIA_BACKEND", "filesystem")
    return (backend or "").strip().lower() == PRIVATE_MEDIA_BACKEND_S3


def execution_accepts_comment_attachments(execution: ActionPlanExecution) -> bool:
    return execution.status in ACTIVE_EXECUTION_STATUSES


def execution_comment_attachments_are_available(
    execution: ActionPlanExecution,
    *,
    now=None,
) -> bool:
    current_time = now or timezone.now()
    if execution.status == EXECUTION_STATUS_CANCELED:
        return False
    if execution.status == EXECUTION_STATUS_DONE:
        closed_at = execution.validated_at or execution.marked_done_at
        if closed_at is None:
            return False
        return current_time < closed_at + timedelta(days=_retention_days())
    return True


def _require_attachable_execution(execution: ActionPlanExecution) -> None:
    if not execution_accepts_comment_attachments(execution):
        raise CommentValidationError(ATTACHMENTS_NOT_ALLOWED_ERROR_DETAIL)


def _read_storage_bytes(*, storage_key: str) -> bytes:
    storage = get_action_plan_comment_private_media_storage()
    if not storage.exists(storage_key):
        raise CommentValidationError(ATTACHMENT_MISSING_OBJECT_ERROR_DETAIL)
    with storage.open(storage_key, "rb") as handle:
        payload = handle.read()
    return payload


def reserve_action_plan_comment_upload(
    *,
    actor_membership: EstablishmentMembership,
    execution: ActionPlanExecution,
    original_filename: str,
    content_type: str,
    size_bytes: int,
) -> ActionPlanCommentUpload:
    _require_attachable_execution(execution)
    if size_bytes < 1 or size_bytes > ACTION_PLAN_COMMENT_ATTACHMENT_MAX_BYTES:
        raise CommentValidationError(ATTACHMENT_TOO_LARGE_ERROR_DETAIL)
    filename = (original_filename or "file").strip()[:255] or "file"
    declared_type = (content_type or "application/octet-stream").strip()[:120]
    upload = ActionPlanCommentUpload(
        establishment_id=actor_membership.establishment_id,
        action_plan_execution=execution,
        uploaded_by_membership=actor_membership,
        original_filename=filename,
        declared_content_type=declared_type,
        declared_size_bytes=size_bytes,
        storage_key="",
        expires_at=timezone.now() + timedelta(hours=_ttl_hours()),
    )
    upload.save()
    upload.storage_key = action_plan_comment_upload_storage_key(
        establishment_id=actor_membership.establishment_id,
        execution_id=execution.id,
        upload_id=upload.id,
        filename=filename,
    )
    upload.save(update_fields=["storage_key", "updated_at"])
    return upload


def get_reserved_action_plan_comment_upload(
    *,
    actor_membership: EstablishmentMembership,
    execution: ActionPlanExecution,
    upload_id: uuid.UUID,
) -> ActionPlanCommentUpload:
    _require_attachable_execution(execution)
    upload = ActionPlanCommentUpload.objects.filter(
        id=upload_id,
        establishment_id=actor_membership.establishment_id,
        action_plan_execution_id=execution.id,
        uploaded_by_membership_id=actor_membership.id,
    ).first()
    if upload is None:
        raise CommentValidationError(ATTACHMENT_INVALID_ERROR_DETAIL)
    if upload.status != ActionPlanCommentUpload.Status.RESERVED:
        raise CommentValidationError(ATTACHMENT_NOT_READY_ERROR_DETAIL)
    if upload.expires_at <= timezone.now():
        raise CommentValidationError(ATTACHMENT_EXPIRED_ERROR_DETAIL)
    return upload


def build_action_plan_comment_upload_put_url(*, upload: ActionPlanCommentUpload) -> str:
    if _is_s3_backend():
        return generate_private_media_presigned_put_url(
            name=upload.storage_key,
            content_type=upload.declared_content_type or "application/octet-stream",
            storage=get_action_plan_comment_private_media_storage(),
            expires_in=_presign_ttl_seconds(),
        )
    return ""


def store_action_plan_comment_upload_content(
    *,
    upload: ActionPlanCommentUpload,
    payload: bytes,
) -> None:
    if upload.status != ActionPlanCommentUpload.Status.RESERVED:
        raise CommentValidationError(ATTACHMENT_NOT_READY_ERROR_DETAIL)
    if upload.expires_at <= timezone.now():
        raise CommentValidationError(ATTACHMENT_EXPIRED_ERROR_DETAIL)
    if len(payload) > ACTION_PLAN_COMMENT_ATTACHMENT_MAX_BYTES:
        raise CommentValidationError(ATTACHMENT_TOO_LARGE_ERROR_DETAIL)
    storage = get_action_plan_comment_private_media_storage()
    storage.save(upload.storage_key, ContentFile(payload))


def _detect_kind(payload: bytes) -> tuple[str, str]:
    if payload.startswith(_PDF_MAGIC):
        return ActionPlanCommentUpload.Kind.DOCUMENT, "application/pdf"
    _ensure_heif_opener_registered()
    try:
        metadata = _detect_image_metadata(payload)
        content_type, _extension = _canonical_from_detected_format(metadata.image_format)
    except UnsupportedImageTypeError as exc:
        raise CommentValidationError(ATTACHMENT_UNSUPPORTED_TYPE_ERROR_DETAIL) from exc
    except ImageValidationError as exc:
        raise CommentValidationError(ATTACHMENT_INVALID_CONTENT_ERROR_DETAIL) from exc
    return ActionPlanCommentUpload.Kind.IMAGE, content_type


@transaction.atomic
def complete_action_plan_comment_upload(
    *,
    actor_membership: EstablishmentMembership,
    execution: ActionPlanExecution,
    upload_id: uuid.UUID,
) -> ActionPlanCommentUpload:
    _require_attachable_execution(execution)
    upload = (
        ActionPlanCommentUpload.objects.select_for_update()
        .filter(
            id=upload_id,
            establishment_id=actor_membership.establishment_id,
            action_plan_execution_id=execution.id,
            uploaded_by_membership_id=actor_membership.id,
        )
        .first()
    )
    if upload is None:
        raise CommentValidationError(ATTACHMENT_INVALID_ERROR_DETAIL)
    if upload.status == ActionPlanCommentUpload.Status.VALIDATED:
        return upload
    if upload.status != ActionPlanCommentUpload.Status.RESERVED:
        raise CommentValidationError(ATTACHMENT_NOT_READY_ERROR_DETAIL)
    if upload.expires_at <= timezone.now():
        upload.status = ActionPlanCommentUpload.Status.EXPIRED
        upload.save(update_fields=["status", "updated_at"])
        raise CommentValidationError(ATTACHMENT_EXPIRED_ERROR_DETAIL)

    started = timezone.now()
    payload = _read_storage_bytes(storage_key=upload.storage_key)
    if len(payload) > ACTION_PLAN_COMMENT_ATTACHMENT_MAX_BYTES:
        raise CommentValidationError(ATTACHMENT_TOO_LARGE_ERROR_DETAIL)
    kind, content_type = _detect_kind(payload)
    upload.kind = kind
    upload.content_type = content_type
    upload.size_bytes = len(payload)
    upload.status = ActionPlanCommentUpload.Status.VALIDATED
    upload.save(update_fields=["kind", "content_type", "size_bytes", "status", "updated_at"])
    elapsed_ms = int((timezone.now() - started).total_seconds() * 1000)
    logger.info(
        "action_plan_comment_upload_complete",
        extra={
            "event": "action_plan_comment_upload_complete",
            "upload_id": str(upload.id),
            "execution_id": str(upload.action_plan_execution_id),
            "kind": kind,
            "elapsed_ms": elapsed_ms,
        },
    )
    if kind == ActionPlanCommentUpload.Kind.IMAGE:
        from houston.comments.tasks import generate_action_plan_comment_upload_thumbnail_task

        transaction.on_commit(
            lambda: generate_action_plan_comment_upload_thumbnail_task.delay(str(upload.id))
        )
    return upload


def generate_action_plan_comment_upload_thumbnail(*, upload_id: uuid.UUID) -> None:
    upload = ActionPlanCommentUpload.objects.filter(id=upload_id).first()
    if upload is None or upload.kind != ActionPlanCommentUpload.Kind.IMAGE:
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
        storage = get_action_plan_comment_private_media_storage()
        storage.save(thumb_key, thumbnail.content_file)
        upload.thumbnail_storage_key = thumb_key
        upload.save(update_fields=["thumbnail_storage_key", "updated_at"])
    except Exception as exc:
        logger.warning(
            "action_plan_comment_upload_thumbnail_failed",
            extra={
                "event": "action_plan_comment_upload_thumbnail_failed",
                "upload_id": str(upload_id),
                "exception_class": type(exc).__name__,
            },
        )
        raise


def lock_validated_uploads_for_comment(
    *,
    actor_membership: EstablishmentMembership,
    execution: ActionPlanExecution,
    attachment_ids: list[uuid.UUID],
) -> list[ActionPlanCommentUpload]:
    unique_ids = list(dict.fromkeys(attachment_ids))
    if not unique_ids:
        return []
    if len(unique_ids) > ACTION_PLAN_COMMENT_ATTACHMENTS_MAX_PER_COMMENT:
        raise CommentValidationError(ATTACHMENT_MAX_COUNT_ERROR_DETAIL)
    uploads = list(
        ActionPlanCommentUpload.objects.select_for_update()
        .filter(id__in=unique_ids)
        .order_by("id")
    )
    if len(uploads) != len(unique_ids):
        raise CommentValidationError(ATTACHMENT_INVALID_ERROR_DETAIL)
    for upload in uploads:
        if upload.uploaded_by_membership_id != actor_membership.id:
            raise CommentValidationError(ATTACHMENT_NOT_OWNED_ERROR_DETAIL)
        if upload.action_plan_execution_id != execution.id:
            raise CommentValidationError(ATTACHMENT_WRONG_EXECUTION_ERROR_DETAIL)
        if upload.status == ActionPlanCommentUpload.Status.LINKED:
            raise CommentValidationError(ATTACHMENT_ALREADY_USED_ERROR_DETAIL)
        if upload.status != ActionPlanCommentUpload.Status.VALIDATED:
            raise CommentValidationError(ATTACHMENT_NOT_READY_ERROR_DETAIL)
        if upload.expires_at <= timezone.now():
            raise CommentValidationError(ATTACHMENT_EXPIRED_ERROR_DETAIL)
    uploads_by_id = {upload.id: upload for upload in uploads}
    return [uploads_by_id[upload_id] for upload_id in unique_ids]


def link_uploads_to_comment(*, comment: Comment, uploads: list[ActionPlanCommentUpload]) -> None:
    now = timezone.now()
    attachments = []
    for index, upload in enumerate(uploads):
        upload.status = ActionPlanCommentUpload.Status.LINKED
        upload.linked_at = now
        upload.save(update_fields=["status", "linked_at", "updated_at"])
        attachments.append(
            ActionPlanCommentAttachment(
                comment=comment,
                upload=upload,
                action_plan_execution_id=upload.action_plan_execution_id,
                position=index,
                kind=upload.kind,
                content_type=upload.content_type,
                size_bytes=upload.size_bytes or 0,
                original_filename=upload.original_filename,
            )
        )
    if attachments:
        ActionPlanCommentAttachment.objects.bulk_create(attachments)


def action_plan_comment_object_keys_for_uploads(
    uploads: list[ActionPlanCommentUpload],
) -> list[str]:
    keys: list[str] = []
    for upload in uploads:
        if upload.storage_key:
            keys.append(upload.storage_key)
        if upload.thumbnail_storage_key:
            keys.append(upload.thumbnail_storage_key)
    return keys


def _delete_action_plan_comment_storage_keys(*, keys: list[str], raise_on_error: bool) -> None:
    storage = get_action_plan_comment_private_media_storage()
    for key in keys:
        if not key:
            continue
        try:
            storage.delete(key)
        except Exception as exc:
            if _is_missing_storage_object_error(exc):
                continue
            logger.warning(
                "action_plan_comment_storage_delete_failed",
                extra={
                    "event": "action_plan_comment_storage_delete_failed",
                    "exception_class": type(exc).__name__,
                },
            )
            if raise_on_error:
                raise


def delete_action_plan_comment_storage_keys(keys: list[str]) -> None:
    _delete_action_plan_comment_storage_keys(keys=keys, raise_on_error=False)


def delete_action_plan_comment_storage_keys_or_raise(keys: list[str]) -> None:
    _delete_action_plan_comment_storage_keys(keys=keys, raise_on_error=True)


def generate_action_plan_comment_attachment_presigned_get(*, storage_key: str) -> str:
    return generate_private_media_presigned_get_url(
        name=storage_key,
        storage=get_action_plan_comment_private_media_storage(),
        expires_in=int(settings.HOUSTON_OBSERVATION_MEDIA_S3_PRESIGN_TTL_SECONDS),
    )


def _purge_uploads(*, uploads: list[ActionPlanCommentUpload]) -> int:
    if not uploads:
        return 0
    keys = action_plan_comment_object_keys_for_uploads(uploads)
    upload_ids = [upload.id for upload in uploads]
    ActionPlanCommentAttachment.objects.filter(upload_id__in=upload_ids).delete()
    deleted, _ = ActionPlanCommentUpload.objects.filter(id__in=upload_ids).delete()
    transaction.on_commit(lambda: delete_action_plan_comment_storage_keys(keys))
    return deleted


def purge_action_plan_comment_media_for_execution(*, execution_id: uuid.UUID) -> int:
    uploads = list(ActionPlanCommentUpload.objects.filter(action_plan_execution_id=execution_id))
    return _purge_uploads(uploads=uploads)


def cleanup_expired_action_plan_comment_uploads(*, now=None, batch_size: int | None = None) -> int:
    current_time = now or timezone.now()
    effective_batch_size = batch_size or getattr(
        settings,
        "HOUSTON_ACTION_PLAN_COMMENT_PURGE_BATCH_SIZE",
        ACTION_PLAN_COMMENT_PURGE_BATCH_SIZE,
    )
    deleted_count = 0
    last_id = None
    first_storage_error: Exception | None = None

    while True:
        queryset = ActionPlanCommentUpload.objects.filter(
            status__in=[
                ActionPlanCommentUpload.Status.RESERVED,
                ActionPlanCommentUpload.Status.VALIDATED,
                ActionPlanCommentUpload.Status.EXPIRED,
            ],
            expires_at__lt=current_time,
        ).order_by("id")
        if last_id is not None:
            queryset = queryset.filter(id__gt=last_id)
        candidate_ids = list(queryset.values_list("id", flat=True)[:effective_batch_size])
        if not candidate_ids:
            break
        for upload_id in candidate_ids:
            last_id = upload_id
            with transaction.atomic():
                upload = (
                    ActionPlanCommentUpload.objects.select_for_update(skip_locked=True)
                    .filter(id=upload_id)
                    .first()
                )
                if upload is None:
                    continue
                if upload.status == ActionPlanCommentUpload.Status.LINKED:
                    continue
                if ActionPlanCommentAttachment.objects.filter(upload_id=upload.id).exists():
                    continue
                if upload.expires_at >= current_time:
                    continue
                keys = action_plan_comment_object_keys_for_uploads([upload])
                try:
                    delete_action_plan_comment_storage_keys_or_raise(keys)
                except Exception as exc:
                    if first_storage_error is None:
                        first_storage_error = exc
                    continue
                removed, _ = ActionPlanCommentUpload.objects.filter(
                    id=upload.id,
                    attachment__isnull=True,
                ).delete()
                if removed:
                    deleted_count += 1

    if first_storage_error is not None:
        raise first_storage_error
    return deleted_count


def cleanup_expired_action_plan_comment_retention(*, now=None) -> int:
    current_time = now or timezone.now()
    cutoff = current_time - timedelta(days=_retention_days())
    expired_execution_ids = list(
        ActionPlanExecution.objects.filter(status=EXECUTION_STATUS_DONE)
        .filter(
            models_q_closed_before(cutoff),
        )
        .values_list("id", flat=True)
    )
    deleted = 0
    for execution_id in expired_execution_ids:
        uploads = list(
            ActionPlanCommentUpload.objects.filter(
                action_plan_execution_id=execution_id,
                status=ActionPlanCommentUpload.Status.LINKED,
            )
        )
        deleted += _purge_uploads(uploads=uploads)
    return deleted


def models_q_closed_before(cutoff):
    from django.db.models import Q

    return (
        Q(validated_at__isnull=False, validated_at__lte=cutoff)
        | Q(validated_at__isnull=True, marked_done_at__isnull=False, marked_done_at__lte=cutoff)
    )
