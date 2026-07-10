"""Celery autodiscovery entrypoint for notification tasks."""

from houston.notifications.push import tasks as _push_tasks  # noqa: F401
