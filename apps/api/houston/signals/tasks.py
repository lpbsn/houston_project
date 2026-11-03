from __future__ import annotations

import logging
import uuid

from celery import shared_task
from config.celery_routing import QUEUE_AI_INTERACTIVE
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
    soft_time_limit=settings.HOUSTON_CELERY_OBSERVATION_PIPELINE_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_OBSERVATION_PIPELINE_TIME_LIMIT_SECONDS,
)
def process_observation_task(observation_id: str) -> None:
    logger.info(
        "observation_pipeline_task_started",
        extra={
            "observation_id": observation_id,
            "event": "observation_pipeline_task_started",
            "queue": QUEUE_AI_INTERACTIVE,
        },
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
                    queue=QUEUE_AI_INTERACTIVE,
                ),
            )
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
            "queue": "operational",
        },
    )
    return recovered_count


@shared_task(
    name="houston.signals.tasks.deliver_record_event_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def deliver_record_event_task(event_id):
    from houston.signals.record_notifications import deliver_record_event

    deliver_record_event(event_id)


@shared_task(name="houston.signals.tasks.record_followup_task")
def record_followup_task():
    from houston.signals.models import SignalRecordEvent
    from houston.signals.record_notifications import deliver_record_event, deliver_record_reminders

    for event_id in (
        SignalRecordEvent.objects.filter(
            notified_at__isnull=True,
            kind__in=[
                "assigned",
                "closed",
                "reopened",
                "review_requested",
                "linked",
                "taken_in_charge",
            ],
        )
        .order_by("created_at")
        .values_list("id", flat=True)[:200]
    ):
        deliver_record_event(event_id)
    deliver_record_reminders()
