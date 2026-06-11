from __future__ import annotations

import logging
import uuid

from celery import shared_task

from houston.checklists.materialization import materialize_assignments_horizon
from houston.core.observability import build_celery_task_failure_log_context

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def materialize_checklist_assignments_horizon_task(
    self,
    establishment_id: str | None = None,
    horizon_days: int = 14,
) -> int:
    try:
        parsed_establishment_id = uuid.UUID(establishment_id) if establishment_id else None
        return materialize_assignments_horizon(
            establishment_id=parsed_establishment_id,
            horizon_days=horizon_days,
        )
    except Exception as exc:
        logger.error(
            "checklist_assignment_horizon_materialization_failed",
            extra=build_celery_task_failure_log_context(
                establishment_id=establishment_id,
                horizon_days=horizon_days,
                exception_class=type(exc).__name__,
            ),
            exc_info=False,
        )
        raise
