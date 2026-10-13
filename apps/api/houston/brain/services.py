from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import date, timedelta
from typing import BinaryIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import connection, transaction
from django.utils import timezone

from houston.brain.bounded import extract_bounded
from houston.brain.errors import (
    BrainAccessDenied,
    BrainWorkError,
    ExtractionRejected,
    ReportingRejected,
)
from houston.brain.models import BrainAnalysis, BrainExtraction, BrainReporting
from houston.brain.records import EXTRACTOR_ID, EXTRACTOR_VERSION
from houston.brain.sniff import sniff_format
from houston.establishments.permissions import resolve_establishment_admin_actor
from houston.uploads.private_storage import (
    delete_private_media_object_idempotent,
    get_private_media_storage,
)

logger = logging.getLogger(__name__)

_CONTENT_TYPES = {
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_TOO_LARGE = "Le fichier dépasse la taille maximale acceptée."
_EMPTY = "Le fichier ne contient pas de contenu analysable."
_PERIOD = "La période confirmée doit avoir un début et une fin."
_PERIOD_ORDER = "La fin de période est exclue et doit être postérieure au début."


def prepare_reporting(
    *,
    establishment,
    author,
    filename: str,
    content: bytes | BinaryIO,
    period_start: date | None = None,
    period_end: date | None = None,
) -> BrainReporting:
    """Store one original and extract it. Does not start an analysis."""
    _validate_period(period_start, period_end)
    original_filename = _basename(filename)
    raw = _read_bounded(content)
    if not raw:
        raise ReportingRejected(code="empty_document", message=_EMPTY)
    source_format = sniff_format(filename, raw)
    reporting_id = uuid.uuid4()
    storage_key = f"brain/reportings/{establishment.id}/{reporting_id}/original"
    reporting = BrainReporting.objects.create(
        id=reporting_id,
        establishment=establishment,
        author=author,
        original_filename=original_filename,
        content_type=_CONTENT_TYPES[source_format],
        source_format=source_format,
        content_sha256=hashlib.sha256(raw).hexdigest(),
        storage_key=storage_key,
        byte_size=len(raw),
        status=BrainReporting.Status.DRAFT,
        period_start=period_start,
        period_end=period_end,
        period_confirmed_at=timezone.now() if period_start and period_end else None,
    )
    _acquire_extraction_lock(reporting.id)
    try:
        try:
            stored_name = get_private_media_storage().save(storage_key, ContentFile(raw))
        except Exception:
            reporting.delete()
            raise
        if stored_name != reporting.storage_key:
            reporting.storage_key = stored_name
            reporting.save(update_fields=["storage_key", "updated_at"])
        try:
            result = extract_bounded(raw, source_format)
        except ExtractionRejected as exc:
            _mark_rejected(reporting, code=exc.code, message=exc.message)
            return reporting
        except Exception as exc:
            logger.error(
                "brain_reporting_extraction_failed",
                extra={
                    "event": "brain_reporting_extraction_failed",
                    "reporting_id": str(reporting.id),
                    "exception_class": type(exc).__name__,
                },
                exc_info=False,
            )
            _mark_rejected(
                reporting,
                code="extraction_failed",
                message="La préparation du fichier a échoué.",
            )
            return reporting
        with transaction.atomic():
            locked = (
                BrainReporting.objects.select_for_update()
                .filter(pk=reporting.pk, status=BrainReporting.Status.DRAFT)
                .first()
            )
            if locked is None:
                current = BrainReporting.objects.filter(pk=reporting.pk).first()
                if current is not None:
                    return current
                raise ExtractionRejected(
                    code="reporting_removed",
                    message="Le reporting n'est plus disponible.",
                )
            BrainExtraction.objects.create(
                reporting=locked,
                extractor_id=EXTRACTOR_ID,
                extractor_version=EXTRACTOR_VERSION,
                source_sha256=locked.content_sha256,
                payload=result.as_payload(),
            )
            locked.status = BrainReporting.Status.READY
            locked.rejection_code = ""
            locked.rejection_message = ""
            locked.save(
                update_fields=["status", "rejection_code", "rejection_message", "updated_at"]
            )
    finally:
        _release_extraction_lock(reporting.id)
    logger.info(
        "brain_reporting_ready",
        extra={
            "event": "brain_reporting_ready",
            "reporting_id": str(reporting.id),
            "source_format": source_format,
            "byte_size": len(raw),
        },
    )
    reporting.refresh_from_db()
    return reporting


def confirm_reporting_period(
    *,
    user,
    establishment_id,
    reporting_id,
    period_start: date,
    period_end: date,
) -> BrainReporting:
    """Confirm the business period once. A later change is a new reporting."""
    if resolve_establishment_admin_actor(user, establishment_id) is None:
        raise BrainAccessDenied()
    _validate_period(period_start, period_end)
    with transaction.atomic():
        reporting = (
            BrainReporting.objects.select_for_update()
            .filter(pk=reporting_id, establishment_id=establishment_id)
            .first()
        )
        if reporting is None or reporting.status != BrainReporting.Status.READY:
            raise BrainWorkError(
                code="reporting_not_ready",
                message="Le reporting n'est pas prêt pour une période.",
            )
        if reporting.period_confirmed_at is not None:
            if reporting.period_start == period_start and reporting.period_end == period_end:
                return reporting
            raise BrainWorkError(
                code="period_already_confirmed",
                message=(
                    "La période confirmée ne se modifie pas. "
                    "Importez un nouveau reporting."
                ),
            )
        if BrainAnalysis.objects.filter(reporting_id=reporting.id).exists():
            raise BrainWorkError(
                code="period_already_confirmed",
                message=(
                    "La période confirmée ne se modifie pas. "
                    "Importez un nouveau reporting."
                ),
            )
        reporting.period_start = period_start
        reporting.period_end = period_end
        reporting.period_confirmed_at = timezone.now()
        reporting.save(
            update_fields=["period_start", "period_end", "period_confirmed_at", "updated_at"]
        )
        return reporting


def cleanup_abandoned_reporting_drafts(*, now=None) -> int:
    """Delete drafts older than the technical TTL, and only those drafts."""
    current = now or timezone.now()
    cutoff = current - timedelta(seconds=int(settings.HOUSTON_BRAIN_DRAFT_TTL_SECONDS))
    batch = int(settings.HOUSTON_BRAIN_DRAFT_CLEANUP_BATCH)
    candidate_ids = list(
        BrainReporting.objects.filter(
            status=BrainReporting.Status.DRAFT,
            created_at__lt=cutoff,
        )
        .order_by("created_at")
        .values_list("id", flat=True)[:batch]
    )
    deleted = 0
    for reporting_id in candidate_ids:
        if _delete_abandoned_draft(reporting_id):
            deleted += 1
    if deleted:
        logger.info(
            "brain_draft_cleanup_completed",
            extra={
                "event": "brain_draft_cleanup_completed",
                "deleted_count": deleted,
            },
        )
    return deleted


def _delete_abandoned_draft(reporting_id) -> bool:
    with transaction.atomic():
        reporting = (
            BrainReporting.objects.select_for_update(skip_locked=True)
            .filter(pk=reporting_id, status=BrainReporting.Status.DRAFT)
            .first()
        )
        if reporting is None:
            return False
        if BrainExtraction.objects.filter(reporting_id=reporting.pk).exists():
            return False
        if not _try_acquire_extraction_lock(reporting.id):
            return False
        try:
            storage_key = reporting.storage_key
            if storage_key and not _storage_key_removed(storage_key):
                return False
            deleted_count, _ = BrainReporting.objects.filter(
                pk=reporting.pk,
                status=BrainReporting.Status.DRAFT,
            ).delete()
            return deleted_count > 0
        finally:
            _release_extraction_lock(reporting.id)


def _storage_key_removed(storage_key: str) -> bool:
    storage = get_private_media_storage()
    try:
        delete_private_media_object_idempotent(storage_key=storage_key, storage=storage)
        return not storage.exists(storage_key)
    except Exception as exc:
        logger.warning(
            "brain_reporting_storage_delete_failed",
            extra={
                "event": "brain_reporting_storage_delete_failed",
                "exception_class": type(exc).__name__,
            },
        )
        return False


def _mark_rejected(reporting: BrainReporting, *, code: str, message: str) -> None:
    reporting.status = BrainReporting.Status.REJECTED
    reporting.rejection_code = code
    reporting.rejection_message = message
    reporting.save(
        update_fields=["status", "rejection_code", "rejection_message", "updated_at"]
    )


def _validate_period(period_start: date | None, period_end: date | None) -> None:
    if (period_start is None) ^ (period_end is None):
        raise ReportingRejected(code="period_incomplete", message=_PERIOD)
    if period_start is not None and period_end is not None and period_end <= period_start:
        raise ReportingRejected(code="period_invalid", message=_PERIOD_ORDER)


def _read_bounded(content: bytes | BinaryIO) -> bytes:
    ceiling = int(settings.HOUSTON_BRAIN_MAX_UPLOAD_BYTES)
    if isinstance(content, (bytes, bytearray, memoryview)):
        if len(content) > ceiling:
            raise ReportingRejected(code="file_too_large", message=_TOO_LARGE)
        return bytes(content)
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = content.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > ceiling:
            raise ReportingRejected(code="file_too_large", message=_TOO_LARGE)
        chunks.append(chunk)
    return b"".join(chunks)


def _advisory_key(reporting_id) -> int:
    return int.from_bytes(reporting_id.bytes[:8], "big", signed=True)


def _acquire_extraction_lock(reporting_id) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s)", [_advisory_key(reporting_id)])
        cursor.fetchone()


def _try_acquire_extraction_lock(reporting_id) -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [_advisory_key(reporting_id)])
        return bool(cursor.fetchone()[0])


def _release_extraction_lock(reporting_id) -> None:
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_unlock(%s)", [_advisory_key(reporting_id)])
        cursor.fetchone()


def _basename(filename: str) -> str:
    name = (filename or "").replace("\\", "/").split("/")[-1].replace("\x00", "").strip()
    if not name:
        raise ReportingRejected(
            code="invalid_filename",
            message="Le fichier n'a pas de nom exploitable.",
        )
    return name[:255]
