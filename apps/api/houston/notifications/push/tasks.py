from __future__ import annotations

import logging
import uuid

from celery import shared_task
from django.conf import settings

from houston.core.observability import build_celery_task_failure_log_context
from houston.notifications.push.services import run_push_for_notification

logger = logging.getLogger(__name__)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def send_push_for_notification_task(notification_id: str) -> int:
    try:
        created_count = run_push_for_notification(uuid.UUID(notification_id))
        logger.info(
            "send_push_for_notification_task_completed",
            extra={
                "event": "send_push_for_notification_task_completed",
                "notification_id": notification_id,
                "created_count": created_count,
            },
        )
        return created_count
    except Exception as exc:
        logger.error(
            "send_push_for_notification_task_failed",
            extra=build_celery_task_failure_log_context(
                exception_class=type(exc).__name__,
                task_name="send_push_for_notification_task",
            ),
            exc_info=False,
        )
        raise
