"""Field start latency while extraction, capture, and a provider hold run.

The API memory gate and the 2 000-candidate worker RSS gate are staging measurements.
"""

from __future__ import annotations

import math
import resource
import threading
import time
from pathlib import Path

import pytest
from django.conf import settings

from houston.brain.capture import capture_dossier
from houston.brain.extract import extract_document
from houston.brain.tests.test_runtime import _allow_publish, _prepare
from houston.signals.services import run_observation_pipeline
from houston.testing.factories import create_membership
from houston.testing.pipeline import create_observation

pytestmark = [pytest.mark.django_db(transaction=True), pytest.mark.slow]


class _StopAfterStart:
    provider = "fake"

    def propose(self, *, input_payload):
        del input_payload
        raise RuntimeError("stop after the field pipeline has started")


def test_observation_start_stays_on_its_queue_and_within_the_local_gate(monkeypatch):
    _allow_publish(monkeypatch)
    route = settings.CELERY_TASK_ROUTES["houston.signals.tasks.process_observation_task"]["queue"]
    assert route == "ai_interactive"
    assert route != "brain_analysis"

    analysis = _prepare(settings, ["Charge locale."])
    membership = create_membership(establishment=analysis.establishment)
    baseline = _samples(membership, 5)
    provider_wait = _during(_provider_hold, membership)
    extraction_wait, extraction_rss_mb, extraction_seconds = _during_extraction(membership)
    capture_wait = _during(lambda: _capture(analysis.id), membership)
    baseline_p95 = _p95(baseline)
    measured = {
        "baseline_p95_s": round(baseline_p95, 4),
        "provider_hold_p95_s": round(_p95(provider_wait), 4),
        "extraction_p95_s": round(_p95(extraction_wait), 4),
        "capture_p95_s": round(_p95(capture_wait), 4),
        "extraction_seconds": round(extraction_seconds, 3),
        "extraction_process_rss_mb": extraction_rss_mb,
    }
    Path("/tmp/houston-brain-load.txt").write_text(str(measured), encoding="utf-8")
    limit = baseline_p95 + 0.5
    assert measured["provider_hold_p95_s"] <= limit, measured
    assert measured["extraction_p95_s"] <= limit, measured
    assert measured["capture_p95_s"] <= limit, measured


def _samples(membership, count: int) -> list[float]:
    delays = []
    for _ in range(count):
        observation = create_observation(membership=membership)
        try:
            run_observation_pipeline(observation.id, provider=_StopAfterStart())
        except RuntimeError:
            pass
        processing = observation.processing
        processing.refresh_from_db()
        assert processing.processing_started_at is not None
        delays.append((processing.processing_started_at - processing.queued_at).total_seconds())
    return delays


def _during(work, membership) -> list[float]:
    error: list[BaseException] = []

    def _run() -> None:
        try:
            work()
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=_run)
    thread.start()
    time.sleep(0.3)
    try:
        delays = _samples(membership, 5)
    finally:
        thread.join(timeout=30)
    if error:
        raise error[0]
    return delays


def _during_extraction(membership) -> tuple[list[float], int, float]:
    raw = _ceiling_csv()
    stop = threading.Event()
    error: list[BaseException] = []
    started = time.perf_counter()

    def _run() -> None:
        try:
            while not stop.is_set():
                extract_document(raw, "csv")
        except BaseException as exc:
            error.append(exc)

    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    thread = threading.Thread(target=_run)
    thread.start()
    try:
        delays = _samples(membership, 5)
    finally:
        stop.set()
        thread.join(timeout=60)
    elapsed = time.perf_counter() - started
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if error:
        raise error[0]
    # Linux ru_maxrss is kilobytes. This process is the test runner, not an isolated worker.
    rss_mb = int(max(before, after) / 1024)
    return delays, rss_mb, elapsed


def _provider_hold() -> None:
    time.sleep(2)


def _capture(analysis_id) -> None:
    capture_dossier(analysis_id, _pauses=(3,))


def _ceiling_csv() -> bytes:
    row = "Libelle;" + ("A" * 180) + ";note terrain\n"
    count = min(2_000, (6 * 1024 * 1024) // len(row.encode()))
    header = "Libelle;Valeur;Note\n"
    return (header + row * count).encode()


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]
