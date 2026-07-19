from __future__ import annotations

import logging
import uuid

from celery import shared_task
from django.conf import settings

from houston.action_plans.lifecycle_promotion import run_scheduled_execution_lifecycle_tick
from houston.action_plans.materialization import materialize_schedules_horizon
from houston.core.observability import build_celery_task_failure_log_context

logger = logging.getLogger(__name__)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def materialize_action_plan_schedules_horizon_task(
    establishment_id: str | None = None,
    horizon_days: int = 14,
) -> int:
    try:
        parsed_establishment_id = uuid.UUID(establishment_id) if establishment_id else None
        return materialize_schedules_horizon(
            establishment_id=parsed_establishment_id,
            horizon_days=horizon_days,
        )
    except Exception as exc:
        logger.error(
            "action_plan_schedule_horizon_materialization_failed",
            extra=build_celery_task_failure_log_context(
                establishment_id=establishment_id,
                horizon_days=horizon_days,
                exception_class=type(exc).__name__,
                task_name="materialize_action_plan_schedules_horizon_task",
            ),
            exc_info=False,
        )
        raise


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def promote_scheduled_action_plan_executions_task() -> dict[str, int]:
    try:
        return run_scheduled_execution_lifecycle_tick()
    except Exception as exc:
        logger.error(
            "action_plan_execution_lifecycle_tick_failed",
            extra=build_celery_task_failure_log_context(
                exception_class=type(exc).__name__,
                task_name="promote_scheduled_action_plan_executions_task",
            ),
            exc_info=False,
        )
        raise
