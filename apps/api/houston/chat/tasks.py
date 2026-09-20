from __future__ import annotations

import logging
import uuid

from celery import shared_task
from django.conf import settings
from houston.chat.purge import purge_chat_messages
from houston.chat.upload_services import (
    chat_object_keys_for_uploads,
    delete_chat_storage_keys,
    generate_chat_upload_thumbnail,
)
from houston.core.observability import build_celery_task_failure_log_context

logger = logging.getLogger(__name__)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def purge_chat_messages_task(
    establishment_id: str | None = None,
) -> int:
    try:
        parsed_establishment_id = uuid.UUID(establishment_id) if establishment_id else None
        result = purge_chat_messages(establishment_id=parsed_establishment_id, dry_run=False)
        logger.info(
            "chat_message_purge_task_completed",
            extra={
                "establishment_id": establishment_id,
                "deleted_count": result.deleted_count,
                "batch_count": result.batch_count,
                "event": "chat_message_purge_task_completed",
            },
        )
        return result.deleted_count
    except Exception as exc:
        logger.error(
            "chat_message_purge_task_failed",
            extra=build_celery_task_failure_log_context(
                establishment_id=establishment_id,
                exception_class=type(exc).__name__,
                task_name="purge_chat_messages_task",
            ),
            exc_info=False,
        )
        raise


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_chat_upload_thumbnail_task(self, upload_id: str) -> None:
    try:
        generate_chat_upload_thumbnail(upload_id=uuid.UUID(upload_id))
    except Exception as exc:
        logger.warning(
            "chat_upload_thumbnail_task_failed",
            extra={
                "event": "chat_upload_thumbnail_task_failed",
                "upload_id": upload_id,
                "exception_class": type(exc).__name__,
            },
        )
        raise self.retry(exc=exc)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def cleanup_chat_upload_orphans_task() -> int:
    from django.utils import timezone
    from houston.chat.models import ChatUpload

    now = timezone.now()
    orphans = list(
        ChatUpload.objects.filter(status__in=[ChatUpload.Status.RESERVED, ChatUpload.Status.VALIDATED])
        .filter(expires_at__lt=now)
    )
    keys = chat_object_keys_for_uploads(orphans)
    deleted = 0
    if orphans:
        deleted, _ = ChatUpload.objects.filter(id__in=[item.id for item in orphans]).delete()
    if keys:
        try:
            delete_chat_storage_keys(keys)
        except Exception:
            logger.warning(
                "chat_orphan_cleanup_storage_failed",
                extra={"event": "chat_orphan_cleanup_storage_failed", "orphans": len(orphans)},
            )
            raise
    logger.info(
        "chat_orphan_cleanup_completed",
        extra={"event": "chat_orphan_cleanup_completed", "deleted_count": deleted},
    )
    return deleted
