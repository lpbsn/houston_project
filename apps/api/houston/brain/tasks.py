from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

from houston.brain.followups import run_brain_follow_up
from houston.brain.recovery import recover_brain_works
from houston.brain.runtime import run_brain_analysis
from houston.brain.services import cleanup_abandoned_reporting_drafts
from houston.core.observability import build_celery_task_failure_log_context

logger = logging.getLogger(__name__)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def cleanup_abandoned_reporting_drafts_task() -> int:
    try:
        deleted_count = cleanup_abandoned_reporting_drafts()
        logger.info(
            "brain_draft_cleanup_task_completed",
            extra={
                "deleted_count": deleted_count,
                "event": "brain_draft_cleanup_task_completed",
            },
        )
        return deleted_count
    except Exception as exc:
        logger.error(
            "brain_draft_cleanup_task_failed",
            extra=build_celery_task_failure_log_context(
                exception_class=type(exc).__name__,
                task_name="cleanup_abandoned_reporting_drafts_task",
            ),
            exc_info=False,
        )
        raise


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_BRAIN_ATTEMPT_SOFT_SECONDS,
    time_limit=settings.HOUSTON_BRAIN_ATTEMPT_HARD_SECONDS,
)
def run_brain_analysis_task(analysis_id: str, attempt_token: str) -> None:
    run_brain_analysis(analysis_id, attempt_token)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_BRAIN_ATTEMPT_SOFT_SECONDS,
    time_limit=settings.HOUSTON_BRAIN_ATTEMPT_HARD_SECONDS,
)
def run_brain_follow_up_task(message_id: str, attempt_token: str) -> None:
    run_brain_follow_up(message_id, attempt_token)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def recover_brain_analysis_task() -> dict[str, int]:
    result = recover_brain_works()
    logger.info(
        "brain_analysis_recovery_sweep_completed",
        extra={"event": "brain_analysis_recovery_sweep_completed", **result},
    )
    return result
