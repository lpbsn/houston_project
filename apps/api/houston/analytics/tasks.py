from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from houston.analytics.services import (
    PatternClassificationRetryableError,
    classify_signal_pattern,
    mark_assignment_permanently_failed,
    mark_assignment_temporary_failed,
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

        if self.request.retries < (self.max_retries or 0):
            retry_delay = self.default_retry_delay or 0
            mark_assignment_temporary_failed(
                signal=signal,
                error_code=exc.error_code,
                expected_attempt_count=exc.attempt_count,
                pending_signature=exc.pending_signature,
                pending_classifier_version=exc.pending_classifier_version,
                next_retry_at=timezone.now() + timedelta(seconds=retry_delay),
            )
            raise self.retry(exc=exc) from exc

        mark_assignment_permanently_failed(
            signal=signal,
            error_code="retry_exhausted",
            expected_attempt_count=exc.attempt_count,
            pending_signature=exc.pending_signature,
            pending_classifier_version=exc.pending_classifier_version,
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
