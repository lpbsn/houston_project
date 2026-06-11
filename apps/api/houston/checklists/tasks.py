from __future__ import annotations

import logging
import uuid

from celery import shared_task
from django.conf import settings

from houston.checklists.materialization import materialize_assignments_horizon
from houston.core.observability import build_celery_task_failure_log_context

logger = logging.getLogger(__name__)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def materialize_checklist_assignments_horizon_task(
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
                task_name="materialize_checklist_assignments_horizon_task",
            ),
            exc_info=False,
        )
        raise
