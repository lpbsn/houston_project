from __future__ import annotations

import logging
import uuid

from celery import shared_task
from django.conf import settings

from houston.ai.observation_pipeline import (
    ObservationPipelineTimeoutError,
    ObservationPipelineUnavailableError,
)
from houston.core.observability import (
    build_observation_processing_failure_log_context,
    build_observation_processing_log_context,
)
from houston.observations.models import ObservationProcessing
from houston.signals.services import (
    recover_observation_processing_batch,
    run_observation_pipeline,
)

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=settings.HOUSTON_CELERY_OBSERVATION_PIPELINE_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_OBSERVATION_PIPELINE_TIME_LIMIT_SECONDS,
)
def process_observation_task(self, observation_id: str) -> None:
    logger.info(
        "observation_pipeline_task_started",
        extra={"observation_id": observation_id, "event": "observation_pipeline_task_started"},
    )
    try:
        run_observation_pipeline(uuid.UUID(observation_id))
    except (ObservationPipelineUnavailableError, ObservationPipelineTimeoutError):
        processing = ObservationProcessing.objects.filter(
            observation_id=observation_id,
        ).first()
        if processing is not None and processing.status == ObservationProcessing.Status.RETRYING:
            logger.warning(
                "observation_pipeline_task_retrying",
                extra=build_observation_processing_log_context(
                    processing=processing,
                    event="observation_pipeline_task_retrying",
                ),
            )
            raise self.retry() from None
        return
    except Exception as exc:
        processing = ObservationProcessing.objects.filter(
            observation_id=observation_id,
        ).first()
        logger.error(
            "observation_pipeline_task_failed",
            extra=build_observation_processing_failure_log_context(
                processing=processing,
                observation_id=observation_id,
                event="observation_pipeline_task_failed",
                exception_class=type(exc).__name__,
            ),
            exc_info=False,
        )
        raise


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def recover_stuck_observation_processing_task() -> int:
    batch_result = recover_observation_processing_batch()
    recovered_count = batch_result["stuck_acted_on"] + batch_result["orphan_enqueued"]
    logger.info(
        "observation_pipeline_stuck_recovery_sweep_completed",
        extra={
            "recovered_count": recovered_count,
            "stuck_acted_on": batch_result["stuck_acted_on"],
            "orphan_enqueued": batch_result["orphan_enqueued"],
            "event": "observation_pipeline_stuck_recovery_sweep_completed",
        },
    )
    return recovered_count
