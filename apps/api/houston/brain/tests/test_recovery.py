"""Normal queue wait is not transport recovery. A beat proves a live process, not a lost message."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from houston.brain.admission import admit_brain_work
from houston.brain.models import (
    BrainAnalysis,
    BrainSlot,
    BrainWorkerBeat,
)
from houston.brain.recovery import recover_brain_works
from houston.brain.runtime import claim_analysis
from houston.brain.tests.test_admission import _reporting
from houston.brain.tests.test_support import allow_publish, prepare

pytestmark = pytest.mark.django_db


def _beat(name: str, *, in_flight: int, concurrency: int, at):
    BrainWorkerBeat.objects.update_or_create(
        process_name=name,
        defaults={"beat_at": at, "concurrency": concurrency, "in_flight": in_flight},
    )


def _queued(monkeypatch, settings, name: str) -> BrainAnalysis:
    allow_publish(monkeypatch)
    return prepare(settings, [name])


def test_a_queued_analysis_behind_full_processes_stays_queued(monkeypatch, settings):
    settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS = 120
    settings.HOUSTON_BRAIN_WORKER_BEAT_STALE_SECONDS = 1_000
    now = timezone.now()
    held = [_queued(monkeypatch, settings, f"occupe {index}") for index in (1, 2)]
    for analysis in held:
        analysis.status = BrainAnalysis.Status.RUNNING
        analysis.claimed_at = now
        analysis.lease_expires_at = now + timedelta(seconds=900)
        analysis.save()
    waiting = _queued(monkeypatch, settings, "en attente")
    _beat("child-a", in_flight=1, concurrency=1, at=now)
    _beat("child-b", in_flight=1, concurrency=1, at=now)
    result = recover_brain_works(now=now + timedelta(seconds=300))
    waiting.refresh_from_db()
    assert waiting.status == BrainAnalysis.Status.QUEUED
    assert waiting.transport_stall_since is None
    assert waiting.transport_republish_count == 0
    assert waiting.transient_retries_used == 0
    assert waiting.failure_code == ""
    assert result["transport_republished"] == 0
    assert result["transport_lost"] == 0


def test_no_fresh_beat_does_not_start_transport_recovery(monkeypatch, settings):
    settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS = 120
    settings.HOUSTON_BRAIN_WORKER_BEAT_STALE_SECONDS = 60
    waiting = _queued(monkeypatch, settings, "redemarrage")
    now = timezone.now()
    result = recover_brain_works(now=now + timedelta(seconds=600))
    waiting.refresh_from_db()
    assert waiting.status == BrainAnalysis.Status.QUEUED
    assert waiting.transport_republish_count == 0
    assert waiting.transport_stall_since is None
    assert waiting.failure_code == ""
    assert result["transport_lost"] == 0


def test_a_free_beat_that_disappears_before_the_stall_does_not_republish(monkeypatch, settings):
    settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS = 120
    settings.HOUSTON_BRAIN_WORKER_BEAT_STALE_SECONDS = 60
    waiting = _queued(monkeypatch, settings, "battement court")
    start = timezone.now()
    _beat("child-a", in_flight=0, concurrency=1, at=start)
    assert recover_brain_works(now=start)["transport_republished"] == 0
    waiting.refresh_from_db()
    assert waiting.transport_stall_since is not None
    BrainWorkerBeat.objects.all().delete()
    result = recover_brain_works(now=start + timedelta(seconds=120))
    waiting.refresh_from_db()
    assert result["transport_republished"] == 0
    assert waiting.transport_republish_count == 0
    assert waiting.transport_stall_since is None
    assert waiting.transient_retries_used == 0


def test_a_waiter_behind_a_running_analysis_does_not_block_another_establishment(
    monkeypatch, settings
):
    settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS = 120
    settings.HOUSTON_BRAIN_WORKER_BEAT_STALE_SECONDS = 1_000
    published = []

    def _publish(analysis_id, attempt_token):
        published.append(str(analysis_id))
        return True

    monkeypatch.setattr("houston.brain.recovery.publish_brain_analysis", _publish)
    waiter = prepare(settings, ["file interne"])
    reporting = _reporting(waiter.establishment, waiter.author)
    reporting.storage_key = f"{reporting.storage_key}-cours"
    reporting.content_sha256 = "c" * 64
    reporting.save(update_fields=["storage_key", "content_sha256", "updated_at"])
    reporting.extractions.update(source_sha256="c" * 64)
    running = admit_brain_work(
        user=waiter.author,
        establishment_id=waiter.establishment_id,
        reporting_id=reporting.id,
        idempotency_key="en-cours",
    )
    now = timezone.now()
    running.status = BrainAnalysis.Status.RUNNING
    running.claimed_at = now
    running.lease_expires_at = now + timedelta(seconds=900)
    running.save()
    victim = prepare(settings, ["autre hotel"])
    published.clear()
    start = timezone.now()
    _beat("child-a", in_flight=0, concurrency=1, at=start)
    recover_brain_works(now=start)
    result = recover_brain_works(now=start + timedelta(seconds=120))
    victim.refresh_from_db()
    waiter.refresh_from_db()
    assert result["transport_republished"] == 1
    assert published == [str(victim.id)]
    assert victim.transport_republish_count == 1
    assert waiter.status == BrainAnalysis.Status.QUEUED
    assert waiter.transport_republish_count == 0
    assert waiter.failure_code == ""


def test_continuous_free_beat_republishes_once(monkeypatch, settings):
    settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS = 120
    settings.HOUSTON_BRAIN_WORKER_BEAT_STALE_SECONDS = 1_000
    published = []

    def _publish(analysis_id, attempt_token):
        published.append(str(analysis_id))
        return True

    monkeypatch.setattr("houston.brain.recovery.publish_brain_analysis", _publish)
    waiting = prepare(settings, ["perte prouvee"])
    published.clear()
    start = timezone.now()
    _beat("child-a", in_flight=0, concurrency=1, at=start)
    recover_brain_works(now=start)
    result = recover_brain_works(now=start + timedelta(seconds=120))
    waiting.refresh_from_db()
    assert result["transport_republished"] == 1
    assert published == [str(waiting.id)]
    assert waiting.transport_republish_count == 1
    assert waiting.transient_retries_used == 0
    assert waiting.status == BrainAnalysis.Status.QUEUED


def test_transport_loss_does_not_change_the_execution_retry_counter(monkeypatch, settings):
    settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS = 120
    settings.HOUSTON_BRAIN_TRANSPORT_REPUBLISH_MAX = 5
    settings.HOUSTON_BRAIN_WORKER_BEAT_STALE_SECONDS = 1_000
    allow_publish(monkeypatch)
    waiting = prepare(settings, ["plafond transport"])
    start = timezone.now()
    waiting.transport_republish_count = 5
    waiting.transport_stall_since = start - timedelta(seconds=120)
    waiting.transient_retries_used = 0
    waiting.save()
    _beat("child-a", in_flight=0, concurrency=1, at=start)
    recover_brain_works(now=start)
    waiting.refresh_from_db()
    assert waiting.status == BrainAnalysis.Status.FAILED
    assert waiting.failure_code == "transport_lost"
    assert waiting.transient_retries_used == 0
    assert not BrainSlot.objects.filter(analysis=waiting).exists()


def test_an_expired_lease_requeues_once_and_the_old_token_cannot_write(monkeypatch, settings):
    allow_publish(monkeypatch)
    analysis = prepare(settings, ["bail expire"])
    now = timezone.now()
    original = analysis.attempt_token
    trace = [{"kind": "tool", "tool": "search_signals", "envelope": {"kept": True}}]
    analysis.status = BrainAnalysis.Status.RUNNING
    analysis.claimed_at = now - timedelta(seconds=300)
    analysis.lease_expires_at = now - timedelta(seconds=1)
    analysis.transient_retries_used = 0
    analysis.transport_republish_count = 4
    analysis.trace = trace
    analysis.save()
    recover_brain_works(now=now)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.QUEUED
    assert analysis.attempt_token != original
    assert analysis.transient_retries_used == 1
    assert analysis.transport_republish_count == 4
    assert analysis.claimed_at is None
    assert analysis.trace == trace
    assert claim_analysis(analysis.id, original) is False
    assert uuid.UUID(str(analysis.attempt_token))
