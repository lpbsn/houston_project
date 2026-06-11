from __future__ import annotations

import logging
import uuid

from celery import shared_task
from django.conf import settings
from houston.chat.purge import purge_chat_messages
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
