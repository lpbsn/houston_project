from __future__ import annotations

import subprocess
import sys

PUSH_TASK_NAME = "houston.notifications.push.tasks.send_push_for_notification_task"

_CHECK_SCRIPT = """
import importlib
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()
importlib.import_module("houston.notifications.tasks")

from config.celery import app

assert "{task_name}" in app.tasks, sorted(
    task_name for task_name in app.tasks if "houston" in task_name
)
""".format(task_name=PUSH_TASK_NAME)


def test_send_push_for_notification_task_registered_by_celery_autodiscovery():
    result = subprocess.run(
        [sys.executable, "-c", _CHECK_SCRIPT],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
