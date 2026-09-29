from __future__ import annotations

import logging
import threading
from collections.abc import Sequence

from django.conf import settings

logger = logging.getLogger(__name__)

_PUBLISH_RETRY_POLICY = {
    "max_retries": 0,
    "interval_start": 0,
    "interval_step": 0,
    "interval_max": 0,
}


def publish_celery_task(task, *, args: Sequence[object], countdown: int | None = None) -> bool:
    """Publish one task and wait for the broker confirm, bounded by a short timeout.

    A timeout or broker error is logged and swallowed. Callers keep the durable
    PostgreSQL state and let the sweep republish.
    """
    timeout_seconds = settings.HOUSTON_CELERY_PUBLISH_TIMEOUT_SECONDS
    outcome: dict[str, object] = {}

    def _send() -> None:
        try:
            task.apply_async(
                args=tuple(args),
                countdown=countdown,
                retry=False,
                retry_policy=_PUBLISH_RETRY_POLICY,
            )
        except Exception as exc:
            outcome["exc"] = exc
            return
        outcome["ok"] = True

    worker = threading.Thread(target=_send, name="houston-celery-publish", daemon=True)
    worker.start()
    worker.join(timeout_seconds)
    task_name = getattr(task, "name", "")
    if worker.is_alive():
        logger.error(
            "celery_publish_timed_out",
            extra={
                "event": "celery_publish_timed_out",
                "task_name": task_name,
                "exception_class": "PublishTimeout",
            },
        )
        return False
    error = outcome.get("exc")
    if error is not None:
        logger.error(
            "celery_publish_failed",
            extra={
                "event": "celery_publish_failed",
                "task_name": task_name,
                "exception_class": type(error).__name__,
            },
        )
        return False
    return True
