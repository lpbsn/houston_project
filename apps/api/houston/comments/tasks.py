from __future__ import annotations

import logging
import uuid

from celery import shared_task
from django.conf import settings

from houston.comments.upload_services import (
    cleanup_expired_action_plan_comment_retention,
    cleanup_expired_action_plan_comment_uploads,
    generate_action_plan_comment_upload_thumbnail,
)
from houston.core.observability import build_celery_task_failure_log_context

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_action_plan_comment_upload_thumbnail_task(self, upload_id: str) -> None:
    try:
        generate_action_plan_comment_upload_thumbnail(upload_id=uuid.UUID(upload_id))
    except Exception as exc:
        logger.warning(
            "action_plan_comment_upload_thumbnail_task_failed",
            extra={
                "event": "action_plan_comment_upload_thumbnail_task_failed",
                "upload_id": upload_id,
                "exception_class": type(exc).__name__,
            },
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def cleanup_action_plan_comment_media_task(self) -> int:
    try:
        orphaned = cleanup_expired_action_plan_comment_uploads()
        retained = cleanup_expired_action_plan_comment_retention()
    except Exception as exc:
        logger.warning(
            "action_plan_comment_media_cleanup_failed",
            extra=build_celery_task_failure_log_context(
                exception_class=type(exc).__name__,
                task_name="cleanup_action_plan_comment_media_task",
            ),
        )
        raise self.retry(exc=exc)
    deleted = orphaned + retained
    logger.info(
        "action_plan_comment_media_cleanup_completed",
        extra={
            "event": "action_plan_comment_media_cleanup_completed",
            "orphaned_count": orphaned,
            "retention_count": retained,
            "deleted_count": deleted,
        },
    )
    return deleted
