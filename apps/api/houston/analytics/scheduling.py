from __future__ import annotations

import uuid

from django.db import transaction

from houston.analytics.signature import build_signal_pattern_signature
from houston.signals.models import Signal


def schedule_signal_pattern_classification_on_commit(signal_id: uuid.UUID) -> None:
    serialized_signal_id = str(signal_id)

    def _enqueue() -> None:
        from houston.analytics.tasks import classify_signal_pattern_task

        classify_signal_pattern_task.delay(serialized_signal_id)

    transaction.on_commit(_enqueue)


def schedule_reclassification_if_signature_changed(
    *,
    signal: Signal,
    before_signature: str,
) -> bool:
    signal = Signal.objects.only("id", "merged_into").get(pk=signal.pk)
    if signal.merged_into_id is not None:
        return False
    after_signature = build_signal_pattern_signature(signal)
    if before_signature == after_signature:
        return False
    schedule_signal_pattern_classification_on_commit(signal.id)
    return True
