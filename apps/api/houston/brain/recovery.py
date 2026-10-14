"""Queue wait and transport recovery are separate. A worker beat is not proof of a lost message."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from houston.brain.models import BrainAnalysis, BrainMessage, BrainSlot, BrainWorkerBeat
from houston.brain.runtime import (
    _retarget_slot,
    _rotate_queued_attempt,
    publish_brain_analysis,
    publish_brain_follow_up,
    requeue_message,
)

_QUEUED = BrainAnalysis.Status.QUEUED
_RUNNING = BrainAnalysis.Status.RUNNING


def recover_brain_works(now=None) -> dict[str, int]:
    moment = now or timezone.now()
    canceled = _cancel_requested()
    retried, exhausted = _retry_expired_leases(moment)
    republished, lost = _recover_transport(moment)
    return {
        "canceled": canceled,
        "execution_retried": retried,
        "transient_exhausted": exhausted,
        "transport_republished": republished,
        "transport_lost": lost,
    }


def _cancel_requested() -> int:
    acted = 0
    for model in (BrainAnalysis, BrainMessage):
        rows = model.objects.filter(
            status__in=(_QUEUED, _RUNNING),
            cancel_requested_at__isnull=False,
        )
        for work_id, token in rows.values_list("id", "attempt_token"):
            if _terminal_cancel(model, work_id, token):
                acted += 1
    return acted


def _retry_expired_leases(now) -> tuple[int, int]:
    retried = 0
    exhausted = 0
    expired = BrainAnalysis.objects.filter(
        status=_RUNNING,
        lease_expires_at__lt=now,
        cancel_requested_at__isnull=True,
    )
    for analysis_id, token, used in expired.values_list(
        "id",
        "attempt_token",
        "transient_retries_used",
    ):
        if used >= 1:
            if _fail_running(BrainAnalysis, analysis_id, token, "transient_exhausted"):
                exhausted += 1
            continue
        if _requeue_attempt(analysis_id, token):
            retried += 1
    messages = BrainMessage.objects.filter(
        status=_RUNNING,
        lease_expires_at__lt=now,
        cancel_requested_at__isnull=True,
    )
    for message_id, token, used in messages.values_list(
        "id",
        "attempt_token",
        "transient_retries_used",
    ):
        if used >= 1:
            if _fail_running(BrainMessage, message_id, token, "transient_exhausted"):
                exhausted += 1
            continue
        if requeue_message(message_id, token):
            retried += 1
    return retried, exhausted


def _recover_transport(now) -> tuple[int, int]:
    republished = 0
    lost = 0
    queued = _queued_works()
    capacity = _fresh_capacity(now)
    for index, (kind, work) in enumerate(queued):
        at_head = index == 0
        proven = work.claimed_at is None and at_head and capacity == "free"
        if not proven:
            _clear_stall(kind, work.id, work.attempt_token)
            continue
        outcome = _transport_head(kind, work.id, work.attempt_token, now)
        if outcome == "republished":
            republished += 1
        elif outcome == "lost":
            lost += 1
    return republished, lost


def _queued_works():
    analyses = [
        ("analysis", row)
        for row in BrainAnalysis.objects.filter(
            status=_QUEUED,
            cancel_requested_at__isnull=True,
        )
    ]
    messages = [
        ("follow_up", row)
        for row in BrainMessage.objects.filter(
            status=_QUEUED,
            cancel_requested_at__isnull=True,
        )
    ]
    rows = analyses + messages
    rows.sort(key=lambda item: (item[1].created_at, str(item[1].id)))
    return rows


def _transport_head(kind, work_id, token, now) -> str:
    stall_seconds = int(settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS)
    limit = int(settings.HOUSTON_BRAIN_TRANSPORT_REPUBLISH_MAX)
    model = BrainMessage if kind == "follow_up" else BrainAnalysis
    with transaction.atomic():
        row = (
            model.objects.select_for_update()
            .filter(id=work_id, attempt_token=token, status=_QUEUED)
            .first()
        )
        if row is None or row.claimed_at is not None or row.cancel_requested_at is not None:
            return "skipped"
        if not _head_is_free(row, now):
            if row.transport_stall_since is not None:
                row.transport_stall_since = None
                row.save(update_fields=["transport_stall_since", "updated_at"])
            return "waiting"
        if row.transport_stall_since is None:
            row.transport_stall_since = now
            row.save(update_fields=["transport_stall_since", "updated_at"])
            return "marked"
        elapsed = (now - row.transport_stall_since).total_seconds()
        if elapsed < stall_seconds:
            return "waiting"
        if row.transport_republish_count >= limit:
            row.status = model.Status.FAILED
            row.failure_code = "transport_lost"
            row.lease_expires_at = None
            row.save(
                update_fields=["status", "failure_code", "lease_expires_at", "updated_at"]
            )
            _release_slot(model, row)
            return "lost"
        row.transport_republish_count += 1
        row.transport_stall_since = None
        row.save(
            update_fields=["transport_republish_count", "transport_stall_since", "updated_at"]
        )
        publish_token = row.attempt_token
    if kind == "follow_up":
        publish_brain_follow_up(work_id, publish_token)
    else:
        publish_brain_analysis(work_id, publish_token)
    return "republished"


def _head_is_free(row, now) -> bool:
    if row.claimed_at is not None:
        return False
    older_analysis = BrainAnalysis.objects.filter(
        status=_QUEUED,
        created_at__lt=row.created_at,
    ).exclude(id=row.id)
    older_message = BrainMessage.objects.filter(
        status=_QUEUED,
        created_at__lt=row.created_at,
    ).exclude(id=row.id)
    if older_analysis.exists() or older_message.exists():
        return False
    return _fresh_capacity(now) == "free"


def _fresh_capacity(now) -> str:
    """free only when a fresh beat reports spare room on that process. No beat means no proof."""
    stale_before = now - timedelta(seconds=int(settings.HOUSTON_BRAIN_WORKER_BEAT_STALE_SECONDS))
    beats = list(BrainWorkerBeat.objects.filter(beat_at__gte=stale_before))
    if not beats:
        return "none"
    if any(beat.in_flight < beat.concurrency for beat in beats):
        return "free"
    return "full"


def _clear_stall(kind, work_id, token) -> None:
    model = BrainMessage if kind == "follow_up" else BrainAnalysis
    model.objects.filter(
        id=work_id,
        attempt_token=token,
        status=_QUEUED,
        transport_stall_since__isnull=False,
    ).update(transport_stall_since=None, updated_at=timezone.now())


def _requeue_attempt(analysis_id, token) -> bool:
    new_token = uuid.uuid4()
    with transaction.atomic():
        row = (
            BrainAnalysis.objects.select_for_update()
            .filter(
                id=analysis_id,
                attempt_token=token,
                status=_RUNNING,
                transient_retries_used=0,
                cancel_requested_at__isnull=True,
            )
            .first()
        )
        if row is None:
            return False
        _rotate_queued_attempt(row, new_token)
        _retarget_slot(row, new_token)
    publish_brain_analysis(analysis_id, new_token)
    return True


def _fail_running(model, work_id, token, failure_code: str) -> bool:
    with transaction.atomic():
        updated = model.objects.filter(
            id=work_id,
            attempt_token=token,
            status=_RUNNING,
        ).update(
            status=model.Status.FAILED,
            failure_code=failure_code,
            lease_expires_at=None,
            updated_at=timezone.now(),
        )
        if not updated:
            return False
        if model is BrainMessage:
            BrainSlot.objects.filter(message_id=work_id).delete()
        else:
            BrainSlot.objects.filter(analysis_id=work_id).delete()
        return True


def _terminal_cancel(model, work_id, token) -> bool:
    with transaction.atomic():
        row = (
            model.objects.select_for_update()
            .filter(id=work_id, attempt_token=token, status__in=(_QUEUED, _RUNNING))
            .first()
        )
        if row is None or row.cancel_requested_at is None:
            return False
        row.status = model.Status.CANCELED
        row.failure_code = row.failure_code or "cancel_requested"
        row.lease_expires_at = None
        row.save(update_fields=["status", "failure_code", "lease_expires_at", "updated_at"])
        _release_slot(model, row)
        return True


def _release_slot(model, row) -> None:
    if model is BrainMessage:
        BrainSlot.objects.filter(message_id=row.id).delete()
        return
    BrainSlot.objects.filter(analysis_id=row.id).delete()
