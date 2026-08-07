from __future__ import annotations

import logging
import uuid

from celery import shared_task
from django.conf import settings

from houston.analytics.services import (
    PatternClassificationRetryableError,
    classify_signal_pattern,
    finalize_retryable_pattern_classification_error,
)
from houston.signals.models import Signal

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=settings.HOUSTON_CELERY_ANALYTICS_PATTERN_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_ANALYTICS_PATTERN_TIME_LIMIT_SECONDS,
)
def classify_signal_pattern_task(self, signal_id: str) -> None:
    logger.info(
        "analytics_pattern_classification_task_started",
        extra={
            "signal_id": signal_id,
            "event": "analytics_pattern_classification_task_started",
        },
    )
    try:
        classify_signal_pattern(uuid.UUID(signal_id))
    except PatternClassificationRetryableError as exc:
        signal = Signal.objects.filter(pk=signal_id).first()
        if signal is None:
            return

        finalization = finalize_retryable_pattern_classification_error(
            signal=signal,
            exc=exc,
            retries=self.request.retries,
            max_retries=self.max_retries or 0,
            retry_delay_seconds=self.default_retry_delay or 0,
        )
        if finalization.outcome == "retry":
            raise self.retry(exc=exc) from exc
    except Exception:
        logger.exception(
            "analytics_pattern_classification_task_failed",
            extra={
                "signal_id": signal_id,
                "event": "analytics_pattern_classification_task_failed",
            },
        )
        raise
