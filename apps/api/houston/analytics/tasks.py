from __future__ import annotations

import logging
import uuid

from celery import shared_task
from config.celery_routing import QUEUE_AI_BACKGROUND
from django.conf import settings

from houston.analytics.retry_policy import analytics_pattern_task_retry_policy
from houston.analytics.scheduling import (
    publish_signal_pattern_classification,
    republish_due_signal_pattern_classifications,
)
from houston.analytics.services import (
    PatternClassificationRetryableError,
    classify_signal_pattern,
    finalize_retryable_pattern_classification_error,
)
from houston.signals.models import Signal

logger = logging.getLogger(__name__)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_ANALYTICS_PATTERN_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_ANALYTICS_PATTERN_TIME_LIMIT_SECONDS,
)
def classify_signal_pattern_task(signal_id: str) -> None:
    logger.info(
        "analytics_pattern_classification_task_started",
        extra={
            "signal_id": signal_id,
            "event": "analytics_pattern_classification_task_started",
            "queue": QUEUE_AI_BACKGROUND,
        },
    )
    try:
        classify_signal_pattern(uuid.UUID(signal_id))
    except PatternClassificationRetryableError as exc:
        signal = Signal.objects.filter(pk=signal_id).first()
        if signal is None:
            return

        policy = analytics_pattern_task_retry_policy()
        finalization = finalize_retryable_pattern_classification_error(
            signal=signal,
            exc=exc,
            retries=max(0, exc.attempt_count - 1),
            max_retries=policy.max_retries,
            retry_delay_seconds=policy.retry_delay_seconds,
        )
        if finalization.outcome == "retry":
            publish_signal_pattern_classification(
                uuid.UUID(signal_id),
                countdown=policy.retry_delay_seconds,
            )
    except Exception:
        logger.exception(
            "analytics_pattern_classification_task_failed",
            extra={
                "signal_id": signal_id,
                "event": "analytics_pattern_classification_task_failed",
            },
        )
        raise


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def recover_due_signal_pattern_classifications_task() -> int:
    published = republish_due_signal_pattern_classifications()
    logger.info(
        "analytics_pattern_classification_recovery_sweep_completed",
        extra={
            "event": "analytics_pattern_classification_recovery_sweep_completed",
            "recovered_count": published,
            "queue": "operational",
        },
    )
    return published
