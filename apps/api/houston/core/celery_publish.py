from __future__ import annotations

import logging
import threading
import time
from collections.abc import Sequence

from django.conf import settings
from kombu import Connection

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
    PostgreSQL state and let the sweep republish. The broker wait itself uses
    the same deadline, so a confirm cannot land after this function has
    returned a timeout.
    """
    timeout_seconds = settings.HOUSTON_CELERY_PUBLISH_TIMEOUT_SECONDS
    outcome: dict[str, object] = {}
    deadline = time.monotonic() + timeout_seconds

    def _send() -> None:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            outcome["exc"] = TimeoutError("PublishTimeout")
            return
        try:
            with Connection(
                settings.CELERY_BROKER_URL,
                connect_timeout=remaining,
                transport_options={"confirm_publish": True},
            ) as connection:
                connection.connect()
                confirm_timeout = deadline - time.monotonic()
                if confirm_timeout <= 0:
                    outcome["exc"] = TimeoutError("PublishTimeout")
                    return
                task.apply_async(
                    args=tuple(args),
                    countdown=countdown,
                    retry=False,
                    retry_policy=_PUBLISH_RETRY_POLICY,
                    connection=connection,
                    timeout=confirm_timeout,
                    confirm_timeout=confirm_timeout,
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
