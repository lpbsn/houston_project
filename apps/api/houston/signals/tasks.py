from __future__ import annotations

import logging
import uuid

from celery import shared_task

from houston.ai.observation_pipeline import (
    ObservationPipelineTimeoutError,
    ObservationPipelineUnavailableError,
)
from houston.core.observability import (
    build_observation_processing_failure_log_context,
    build_observation_processing_log_context,
)
from houston.observations.models import ObservationProcessing
from houston.signals.services import run_observation_pipeline

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
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
