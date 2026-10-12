"""Heartbeats from Brain worker processes. Other pools do not write them."""

from __future__ import annotations

import logging
import os
import socket
import sys
import threading

from django.db import close_old_connections
from django.utils import timezone

from houston.brain.models import BrainWorkerBeat

logger = logging.getLogger(__name__)

_installed = False
_write_lock = threading.Lock()


class _BeatState:
    process_name: str | None = None
    concurrency: int = 1
    in_flight: int = 0
    stop: bool = False


_beat = _BeatState()


def register_worker_beat() -> None:
    global _installed
    if _installed:
        return
    _installed = True
    from celery.signals import (
        task_postrun,
        task_prerun,
        worker_process_init,
        worker_process_shutdown,
        worker_ready,
    )

    worker_process_init.connect(_on_process_init)
    worker_process_shutdown.connect(_on_process_shutdown)
    worker_ready.connect(_on_worker_ready)
    task_prerun.connect(_on_task_prerun)
    task_postrun.connect(_on_task_postrun)


def record_beat(*, process_name: str, concurrency: int, in_flight: int) -> None:
    close_old_connections()
    BrainWorkerBeat.objects.update_or_create(
        process_name=process_name,
        defaults={
            "beat_at": timezone.now(),
            "concurrency": concurrency,
            "in_flight": in_flight,
        },
    )


def _on_process_init(**kwargs) -> None:
    del kwargs
    close_old_connections()
    if not _consumes_brain_queue():
        return
    # A prefork child runs one task. Its own capacity is 1, not the parent's --concurrency.
    _start(concurrency=1)


def _on_worker_ready(sender=None, **kwargs) -> None:
    del kwargs
    if not _consumes_brain_queue() or _pool_name(sender) == "prefork":
        return
    _start(concurrency=_concurrency(sender))


def _on_process_shutdown(**kwargs) -> None:
    del kwargs
    name = _beat.process_name
    if not name:
        return
    _beat.stop = True
    close_old_connections()
    BrainWorkerBeat.objects.filter(process_name=name).delete()


def _on_task_prerun(**kwargs) -> None:
    del kwargs
    if not _beat.process_name:
        return
    with _write_lock:
        _beat.in_flight += 1
    _write()


def _on_task_postrun(**kwargs) -> None:
    del kwargs
    if not _beat.process_name:
        return
    with _write_lock:
        _beat.in_flight = max(0, _beat.in_flight - 1)
    _write()


def _start(*, concurrency: int) -> None:
    if _beat.process_name:
        return
    _beat.process_name = f"{socket.gethostname()}:{os.getpid()}"
    _beat.concurrency = max(1, concurrency)
    _beat.in_flight = 0
    _beat.stop = False
    _write()
    thread = threading.Thread(target=_loop, name="houston-brain-worker-beat", daemon=True)
    thread.start()


def _loop() -> None:
    import time

    from django.conf import settings

    while not _beat.stop:
        interval = int(settings.HOUSTON_BRAIN_WORKER_BEAT_INTERVAL_SECONDS)
        time.sleep(interval if interval > 0 else 30)
        if _beat.stop:
            return
        try:
            _write()
        except Exception:
            logger.exception("brain_worker_beat_failed")


def _write() -> None:
    name = _beat.process_name
    if not name:
        return
    with _write_lock:
        in_flight = _beat.in_flight
        concurrency = _beat.concurrency
    record_beat(process_name=name, concurrency=concurrency, in_flight=in_flight)


def _consumes_brain_queue() -> bool:
    from config.celery_routing import QUEUE_BRAIN_ANALYSIS

    args = sys.argv
    for index, arg in enumerate(args):
        if arg == "-Q" and index + 1 < len(args):
            return QUEUE_BRAIN_ANALYSIS in args[index + 1].split(",")
        if arg.startswith("--queues="):
            return QUEUE_BRAIN_ANALYSIS in arg.split("=", 1)[1].split(",")
    return False


def _pool_name(sender) -> str:
    app = getattr(sender, "app", None)
    if app is None:
        return "prefork"
    return str(getattr(app.conf, "worker_pool", None) or "prefork")


def _concurrency(sender) -> int:
    controller = getattr(sender, "controller", None)
    value = getattr(controller, "concurrency", None)
    if isinstance(value, int) and value > 0:
        return value
    app = getattr(sender, "app", None)
    configured = getattr(getattr(app, "conf", None), "worker_concurrency", None)
    if isinstance(configured, int) and configured > 0:
        return configured
    return 1
