from __future__ import annotations

import logging
import uuid

from celery import shared_task
from houston.chat.purge import purge_chat_messages

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def purge_chat_messages_task(
    self,
    establishment_id: str | None = None,
) -> int:
    try:
        parsed_establishment_id = uuid.UUID(establishment_id) if establishment_id else None
        result = purge_chat_messages(establishment_id=parsed_establishment_id, dry_run=False)
        logger.info(
            "Chat message purge task completed",
            extra={
                "establishment_id": establishment_id,
                "deleted_count": result.deleted_count,
                "batch_count": result.batch_count,
            },
        )
        return result.deleted_count
    except Exception:
        logger.exception(
            "Chat message purge task failed",
            extra={"establishment_id": establishment_id},
        )
        raise
