from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from houston.analytics.models import SignalPatternAssignment
from houston.analytics.services import get_or_create_assignment_for_signal
from houston.analytics.signature import build_signal_pattern_signature
from houston.signals.models import Signal

logger = logging.getLogger(__name__)

_RECOVERY_BATCH_SIZE = 50


def publish_signal_pattern_classification(
    signal_id: uuid.UUID,
    *,
    countdown: int | None = None,
) -> bool:
    from houston.analytics.tasks import classify_signal_pattern_task
    from houston.core.celery_publish import publish_celery_task

    published = publish_celery_task(
        classify_signal_pattern_task,
        args=(str(signal_id),),
        countdown=countdown,
    )
    if not published:
        return False
    SignalPatternAssignment.objects.filter(signal_id=signal_id).update(
        published_at=timezone.now(),
    )
    return True


def schedule_signal_pattern_classification_on_commit(signal_id: uuid.UUID) -> None:
    signal = Signal.objects.filter(pk=signal_id).first()
    if signal is not None:
        get_or_create_assignment_for_signal(signal)

    def _enqueue() -> None:
        publish_signal_pattern_classification(signal_id)

    transaction.on_commit(_enqueue)


def schedule_reclassification_if_signature_changed(
    *,
    signal: Signal,
    before_signature: str,
) -> bool:
    after_signature = build_signal_pattern_signature(signal)
    if before_signature == after_signature:
        return False
    schedule_signal_pattern_classification_on_commit(signal.id)
    return True


def republish_due_signal_pattern_classifications(
    *,
    batch_size: int = _RECOVERY_BATCH_SIZE,
) -> int:
    now = timezone.now()
    stale_cutoff = now - timedelta(
        seconds=settings.HOUSTON_ANALYTICS_PATTERN_PROCESSING_STALE_SECONDS,
    )
    # A confirm inside the stale window is still the current broker message.
    publish_due = Q(published_at__isnull=True) | Q(published_at__lt=stale_cutoff)
    signal_ids: list[uuid.UUID] = []
    not_started = (
        SignalPatternAssignment.objects.filter(
            classification_status=SignalPatternAssignment.ClassificationStatus.NOT_STARTED,
        )
        .filter(publish_due)
        .order_by("created_at", "id")
    )
    signal_ids.extend(not_started.values_list("signal_id", flat=True)[:batch_size])

    remaining = batch_size - len(signal_ids)
    if remaining > 0:
        due_retry = (
            SignalPatternAssignment.objects.filter(
                classification_status=SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED,
                next_retry_at__lte=now,
            )
            .filter(publish_due)
            .order_by("next_retry_at", "id")
        )
        signal_ids.extend(due_retry.values_list("signal_id", flat=True)[:remaining])

    remaining = batch_size - len(signal_ids)
    if remaining > 0:
        stale_processing = (
            SignalPatternAssignment.objects.filter(
                classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
            )
            .filter(Q(last_attempted_at__isnull=True) | Q(last_attempted_at__lt=stale_cutoff))
            .filter(publish_due)
            .order_by("last_attempted_at", "id")
        )
        signal_ids.extend(stale_processing.values_list("signal_id", flat=True)[:remaining])

    published = 0
    for signal_id in signal_ids:
        if publish_signal_pattern_classification(signal_id):
            published += 1
        else:
            logger.error(
                "analytics_pattern_classification_republish_failed",
                extra={
                    "event": "analytics_pattern_classification_republish_failed",
                    "signal_id": str(signal_id),
                },
            )
    return published
