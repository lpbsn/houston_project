from __future__ import annotations

import logging
import uuid

from celery import shared_task

from houston.ai.observation_pipeline import (
    ObservationPipelineTimeoutError,
    ObservationPipelineUnavailableError,
)
from houston.observations.models import ObservationProcessing
from houston.signals.services import run_observation_pipeline

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def process_observation_task(self, observation_id: str) -> None:
    try:
        run_observation_pipeline(uuid.UUID(observation_id))
    except (ObservationPipelineUnavailableError, ObservationPipelineTimeoutError):
        processing = ObservationProcessing.objects.filter(
            observation_id=observation_id,
        ).first()
        if processing is not None and processing.status == ObservationProcessing.Status.RETRYING:
            raise self.retry() from None
        return
    except Exception:
        logger.exception(
            "Observation pipeline failed",
            extra={"observation_id": observation_id},
        )
        raise
