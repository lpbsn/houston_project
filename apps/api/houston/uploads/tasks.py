from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

from houston.core.observability import build_celery_task_failure_log_context
from houston.uploads.services import cleanup_expired_uploads

logger = logging.getLogger(__name__)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def cleanup_expired_uploads_task() -> int:
    try:
        deleted_count = cleanup_expired_uploads()
        logger.info(
            "upload_cleanup_task_completed",
            extra={
                "deleted_count": deleted_count,
                "event": "upload_cleanup_task_completed",
            },
        )
        return deleted_count
    except Exception as exc:
        logger.error(
            "upload_cleanup_task_failed",
            extra=build_celery_task_failure_log_context(
                exception_class=type(exc).__name__,
                task_name="cleanup_expired_uploads_task",
            ),
            exc_info=False,
        )
        raise
