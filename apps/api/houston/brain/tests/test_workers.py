"""Recovery through a real local Celery worker. Database fixtures alone do not stand in for it."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone

from houston.ai.models import AIUsageLog
from houston.brain.configuration import digest
from houston.brain.lots import plan_lots, sections_from_payload
from houston.brain.models import BrainAnalysis, BrainLot, BrainWorkerBeat
from houston.brain.recovery import recover_brain_works
from houston.brain.runtime import publish_brain_analysis, write_validated_lot
from houston.brain.tests.test_runtime import _prepare

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.slow]


class BrainWorker:
    def __init__(self, *, concurrency: int, hold_seconds: int):
        self.log = open(os.devnull, "w+b")  # replaced in start
        self.proc: subprocess.Popen | None = None
        self.concurrency = concurrency
        self.hold_seconds = hold_seconds

    def start(self) -> None:
        env = os.environ.copy()
        env["POSTGRES_DB"] = settings.DATABASES["default"]["NAME"]
        env["HOUSTON_BRAIN_WORKER_BEAT_INTERVAL_SECONDS"] = "1"
        env["HOUSTON_BRAIN_FAKE_HOLD_SECONDS"] = str(self.hold_seconds)
        env["HOUSTON_BRAIN_FAKE_MODE"] = "ok"
        self.log = open(f"/tmp/houston-brain-worker-{uuid.uuid4().hex}.log", "w+b")
        self.proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "celery",
                "-A",
                "config",
                "worker",
                "-l",
                "warning",
                "-n",
                f"houston-brain-test-{os.getpid()}-{uuid.uuid4().hex[:6]}@%h",
                "-Q",
                "brain_analysis",
                "--prefetch-multiplier=1",
                "--concurrency",
                str(self.concurrency),
                "--pool",
                "prefork",
            ],
            cwd=str(settings.BASE_DIR),
            env=env,
            stdout=self.log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    def stop(self) -> None:
        proc = self.proc
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=15)
        self.proc = None
        if self.log and not self.log.closed:
            self.log.close()

    def tail(self) -> str:
        if self.log.closed:
            return ""
        self.log.seek(0)
        return self.log.read().decode(errors="replace")[-2500:]


def _purge() -> None:
    from kombu import Connection

    with Connection(settings.CELERY_BROKER_URL) as connection:
        connection.connect()
        channel = connection.channel()
        try:
            channel.queue_purge("brain_analysis")
        except Exception:
            return


def _wait_until(predicate, timeout: float, message: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.2)
    raise AssertionError(message)


def test_saturated_workers_leave_the_next_analysis_queued():
    worker = BrainWorker(concurrency=2, hold_seconds=8)
    worker.start()
    try:
        _wait_until(
            lambda: BrainWorkerBeat.objects.count() >= 1,
            25,
            worker.tail(),
        )
        _purge()
        analyses = [_prepare(settings, [f"occupe {index} " * 5]) for index in range(3)]
        _wait_until(
            lambda: BrainAnalysis.objects.filter(
                id__in=[item.id for item in analyses],
                status=BrainAnalysis.Status.RUNNING,
            ).count()
            >= 2,
            20,
            worker.tail(),
        )
        result = recover_brain_works()
        waiting = [item for item in analyses if _status(item) == BrainAnalysis.Status.QUEUED]
        assert len(waiting) == 1
        waiting[0].refresh_from_db()
        assert waiting[0].transport_republish_count == 0
        assert waiting[0].transient_retries_used == 0
        assert result["transport_republished"] == 0
        assert result["transport_lost"] == 0
    finally:
        worker.stop()


def test_restart_without_a_fresh_beat_does_not_republish(settings):
    settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS = 2
    settings.HOUSTON_BRAIN_WORKER_BEAT_STALE_SECONDS = 2
    worker = BrainWorker(concurrency=1, hold_seconds=0)
    worker.start()
    try:
        _wait_until(lambda: _free_beat() is not None, 25, worker.tail())
        _purge()
        analysis = _prepare_without_publish(settings)
        assert recover_brain_works()["transport_republished"] == 0
        analysis.refresh_from_db()
        assert analysis.transport_stall_since is not None
        worker.stop()
        time.sleep(2.5)
        result = recover_brain_works()
        analysis.refresh_from_db()
        assert result["transport_republished"] == 0
        assert analysis.status == BrainAnalysis.Status.QUEUED
        assert analysis.transport_republish_count == 0
        assert analysis.failure_code == ""
    finally:
        worker.stop()


def test_a_lost_publish_is_delivered_by_a_live_idle_worker(settings):
    settings.HOUSTON_BRAIN_TRANSPORT_STALL_SECONDS = 2
    settings.HOUSTON_BRAIN_WORKER_BEAT_STALE_SECONDS = 30
    worker = BrainWorker(concurrency=1, hold_seconds=0)
    worker.start()
    try:
        _wait_until(lambda: _free_beat() is not None, 25, worker.tail())
        _purge()
        analysis = _prepare_without_publish(settings)
        assert analysis.published_at is None
        assert recover_brain_works()["transport_republished"] == 0
        time.sleep(2.2)
        result = recover_brain_works()
        assert result["transport_republished"] == 1
        _wait_until(
            lambda: _status(analysis) == BrainAnalysis.Status.COMPLETED,
            25,
            worker.tail(),
        )
        analysis.refresh_from_db()
        assert analysis.transient_retries_used == 0
    finally:
        worker.stop()


def test_killing_the_worker_retries_once_and_the_old_token_cannot_write(settings):
    settings.HOUSTON_BRAIN_LEASE_SECONDS = 3
    analysis = _prepare_without_publish(settings)
    original = analysis.attempt_token
    worker = BrainWorker(concurrency=1, hold_seconds=20)
    worker.start()
    try:
        _wait_until(lambda: BrainWorkerBeat.objects.exists(), 25, worker.tail())
        _purge()
        assert publish_brain_analysis(analysis.id, analysis.attempt_token) is True
        _wait_until(lambda: _status(analysis) == BrainAnalysis.Status.RUNNING, 20, worker.tail())
        worker.stop()
        time.sleep(4)
        result = recover_brain_works()
        analysis.refresh_from_db()
        assert result["execution_retried"] == 1
        assert analysis.transient_retries_used == 1
        assert analysis.attempt_token != original
        assert analysis.status == BrainAnalysis.Status.QUEUED
        assert write_validated_lot(
            analysis_id=analysis.id,
            attempt_token=original,
            stable_key="lot-stolen",
            input_hash="a" * 64,
            configuration_hash="b" * 64,
            output={"stolen": True},
            reserved_input_tokens=1,
        ) is False
        follower = BrainWorker(concurrency=1, hold_seconds=0)
        follower.start()
        try:
            assert publish_brain_analysis(analysis.id, analysis.attempt_token) is True
            _wait_until(
                lambda: _status(analysis) == BrainAnalysis.Status.COMPLETED,
                25,
                follower.tail(),
            )
        finally:
            follower.stop()
        analysis.refresh_from_db()
        assert analysis.transient_retries_used == 1
        lot = BrainLot.objects.get(analysis=analysis)
        assert lot.attempt_token == analysis.attempt_token
        assert lot.attempt_token != original
    finally:
        worker.stop()


def test_a_live_worker_reuses_a_validated_lot_without_calling_the_provider(settings):
    analysis = _prepare_without_publish(settings)
    sections = sections_from_payload(analysis.reporting.extractions.get().payload)
    ceilings = analysis.configuration["ceilings"]
    planned = plan_lots(
        sections,
        per_call_input_tokens=ceilings["per_call_input_tokens"],
        total_input_tokens=ceilings["total_input_tokens"],
        max_calls=ceilings["max_calls"],
    )
    lot = planned[0]
    writer = uuid.uuid4()
    BrainLot.objects.create(
        analysis=analysis,
        stable_key=lot.stable_key,
        input_hash=lot.input_hash,
        configuration_hash=digest(analysis.configuration),
        status=BrainLot.Status.VALIDATED,
        output={"kept": True},
        attempt_token=writer,
        reserved_input_tokens=lot.reserved_input_tokens,
    )
    worker = BrainWorker(concurrency=1, hold_seconds=0)
    worker.start()
    try:
        _wait_until(lambda: BrainWorkerBeat.objects.exists(), 25, worker.tail())
        _purge()
        assert publish_brain_analysis(analysis.id, analysis.attempt_token) is True
        _wait_until(
            lambda: _status(analysis) == BrainAnalysis.Status.COMPLETED,
            25,
            worker.tail(),
        )
        stored = BrainLot.objects.get(analysis=analysis)
        assert stored.output == {"kept": True}
        assert stored.attempt_token == writer
        assert AIUsageLog.objects.filter(correlation_id=analysis.id).count() == 0
    finally:
        worker.stop()


def test_double_delivery_claims_once(settings):
    worker = BrainWorker(concurrency=2, hold_seconds=0)
    worker.start()
    try:
        _wait_until(lambda: BrainWorkerBeat.objects.count() >= 1, 25, worker.tail())
        _purge()
        analysis = _prepare_without_publish(settings)
        assert publish_brain_analysis(analysis.id, analysis.attempt_token) is True
        assert publish_brain_analysis(analysis.id, analysis.attempt_token) is True
        _wait_until(
            lambda: _status(analysis) == BrainAnalysis.Status.COMPLETED,
            25,
            worker.tail(),
        )
        analysis.refresh_from_db()
        assert analysis.attempt_count == 1
        assert BrainLot.objects.filter(analysis=analysis).count() == 1
        assert AIUsageLog.objects.filter(correlation_id=analysis.id).count() == 1
    finally:
        worker.stop()


def _prepare_without_publish(settings):
    published = {"allow": False}

    def _publish(analysis_id, attempt_token):
        if not published["allow"]:
            return False
        return publish_brain_analysis(analysis_id, attempt_token)

    from houston.brain import runtime

    original = runtime.publish_brain_analysis
    runtime.publish_brain_analysis = _publish
    try:
        analysis = _prepare(settings, ["worker lot"])
    finally:
        runtime.publish_brain_analysis = original
    analysis.refresh_from_db()
    return analysis


def _status(analysis: BrainAnalysis) -> str:
    analysis.refresh_from_db()
    return analysis.status


def _free_beat():
    cutoff = timezone.now() - timedelta(seconds=30)
    return (
        BrainWorkerBeat.objects.filter(beat_at__gte=cutoff, in_flight=0)
        .order_by("-beat_at")
        .first()
    )
