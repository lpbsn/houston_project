"""Queue wait and transport recovery are separate. A worker beat is not proof of a lost message."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from houston.brain.models import BrainAnalysis, BrainSlot, BrainWorkerBeat
from houston.brain.runtime import publish_brain_analysis

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
    rows = BrainAnalysis.objects.filter(
        status__in=(_QUEUED, _RUNNING),
        cancel_requested_at__isnull=False,
    )
    for analysis_id, token in rows.values_list("id", "attempt_token"):
        if _terminal_cancel(analysis_id, token):
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
            if _fail_running(analysis_id, token, "transient_exhausted"):
                exhausted += 1
            continue
        if _requeue_attempt(analysis_id, token):
            retried += 1
    return retried, exhausted


def _recover_transport(now) -> tuple[int, int]:
    republished = 0
    lost = 0
    queued = list(
        BrainAnalysis.objects.filter(status=_QUEUED, cancel_requested_at__isnull=True).order_by(
            "created_at",
            "id",
        )
    )
    capacity = _fresh_capacity(now)
    for index, analysis in enumerate(queued):
        at_head = index == 0
        proven = (
            analysis.claimed_at is None
            and at_head
            and capacity == "free"
        )
        if not proven:
            _clear_stall(analysis.id, analysis.attempt_token)
            continue
        outcome = _transport_head(analysis.id, analysis.attempt_token, now)
        if outcome == "republished":
            republished += 1
        elif outcome == "lost":
            lost += 1
    return republished, lost


def _transport_head(analysis_id, token, now) -> str:
    stall_seconds = int(settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS)
    limit = int(settings.HOUSTON_BRAIN_TRANSPORT_REPUBLISH_MAX)
    with transaction.atomic():
        row = (
            BrainAnalysis.objects.select_for_update()
            .filter(id=analysis_id, attempt_token=token, status=_QUEUED)
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
            row.status = BrainAnalysis.Status.FAILED
            row.failure_code = "transport_lost"
            row.lease_expires_at = None
            row.save(
                update_fields=["status", "failure_code", "lease_expires_at", "updated_at"]
            )
            BrainSlot.objects.filter(analysis_id=row.id).delete()
            return "lost"
        row.transport_republish_count += 1
        row.transport_stall_since = None
        row.save(
            update_fields=["transport_republish_count", "transport_stall_since", "updated_at"]
        )
        publish_token = row.attempt_token
    publish_brain_analysis(analysis_id, publish_token)
    return "republished"


def _head_is_free(row: BrainAnalysis, now) -> bool:
    if row.claimed_at is not None:
        return False
    older = BrainAnalysis.objects.filter(status=_QUEUED, created_at__lt=row.created_at).exclude(
        id=row.id
    )
    if older.exists():
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


def _clear_stall(analysis_id, token) -> None:
    BrainAnalysis.objects.filter(
        id=analysis_id,
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
        row.attempt_token = new_token
        row.status = _QUEUED
        row.claimed_at = None
        row.lease_expires_at = None
        row.published_at = None
        row.transport_stall_since = None
        row.transient_retries_used = 1
        row.save(
            update_fields=[
                "attempt_token",
                "status",
                "claimed_at",
                "lease_expires_at",
                "published_at",
                "transport_stall_since",
                "transient_retries_used",
                "updated_at",
            ]
        )
        slot = BrainSlot.objects.select_for_update().filter(analysis_id=row.id).first()
        if slot is None:
            BrainSlot.objects.create(
                establishment_id=row.establishment_id,
                analysis=row,
                kind=BrainSlot.Kind.ANALYSIS,
                status=_QUEUED,
                token=new_token,
            )
        else:
            slot.token = new_token
            slot.status = _QUEUED
            slot.save(update_fields=["token", "status", "updated_at"])
    publish_brain_analysis(analysis_id, new_token)
    return True


def _fail_running(analysis_id, token, failure_code: str) -> bool:
    with transaction.atomic():
        updated = BrainAnalysis.objects.filter(
            id=analysis_id,
            attempt_token=token,
            status=_RUNNING,
        ).update(
            status=BrainAnalysis.Status.FAILED,
            failure_code=failure_code,
            lease_expires_at=None,
            updated_at=timezone.now(),
        )
        if not updated:
            return False
        BrainSlot.objects.filter(analysis_id=analysis_id).delete()
        return True


def _terminal_cancel(analysis_id, token) -> bool:
    with transaction.atomic():
        row = (
            BrainAnalysis.objects.select_for_update()
            .filter(id=analysis_id, attempt_token=token, status__in=(_QUEUED, _RUNNING))
            .first()
        )
        if row is None or row.cancel_requested_at is None:
            return False
        row.status = BrainAnalysis.Status.CANCELED
        row.failure_code = row.failure_code or "cancel_requested"
        row.lease_expires_at = None
        row.save(update_fields=["status", "failure_code", "lease_expires_at", "updated_at"])
        BrainSlot.objects.filter(analysis_id=analysis_id).delete()
        return True
