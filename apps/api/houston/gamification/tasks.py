from __future__ import annotations

import logging
import uuid

from celery import shared_task
from django.conf import settings

from houston.core.observability import build_celery_task_failure_log_context
from houston.establishments.models import Establishment
from houston.gamification.services import rollover_establishment_if_due

logger = logging.getLogger(__name__)


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def rollover_gamification_seasons_task(
    establishment_id: str | None = None,
) -> int:
    """Scan establishments and rollover seasons whose local month has advanced."""
    try:
        if establishment_id:
            establishments = Establishment.objects.filter(
                id=uuid.UUID(establishment_id),
                status=Establishment.Status.ACTIVE,
            )
        else:
            establishments = Establishment.objects.filter(
                status=Establishment.Status.ACTIVE,
            ).order_by("id")

        processed = 0
        failed = 0
        for establishment in establishments.iterator():
            try:
                rollover_establishment_if_due(establishment)
                processed += 1
            except Exception as exc:
                failed += 1
                logger.error(
                    "gamification_rollover_establishment_failed",
                    extra=build_celery_task_failure_log_context(
                        establishment_id=str(establishment.id),
                        exception_class=type(exc).__name__,
                        task_name="rollover_gamification_seasons_task",
                    ),
                    exc_info=False,
                )

        logger.info(
            "gamification_rollover_task_completed",
            extra={
                "establishment_id": establishment_id,
                "processed_count": processed,
                "failed_count": failed,
                "event": "gamification_rollover_task_completed",
            },
        )
        if failed:
            logger.error(
                "gamification_rollover_task_partial_failure",
                extra=build_celery_task_failure_log_context(
                    establishment_id=establishment_id,
                    exception_class="PartialFailure",
                    task_name="rollover_gamification_seasons_task",
                ),
                exc_info=False,
            )
            raise RuntimeError(
                f"gamification rollover failed for {failed} establishment(s)"
            )
        return processed
    except Exception as exc:
        if isinstance(exc, RuntimeError) and str(exc).startswith(
            "gamification rollover failed"
        ):
            raise
        logger.error(
            "gamification_rollover_task_failed",
            extra=build_celery_task_failure_log_context(
                establishment_id=establishment_id,
                exception_class=type(exc).__name__,
                task_name="rollover_gamification_seasons_task",
            ),
            exc_info=False,
        )
        raise
