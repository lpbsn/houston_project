"""Lot 10A: purge legacy notification rows before enum cleanup."""

from __future__ import annotations

from django.db import migrations
from django.db.models import Q


LEGACY_NOTIFICATION_EVENT_KEYS = (
    "action.created",
    "action.reassigned",
    "action.pending_validation",
    "action.reopened",
    "action.canceled",
    "checklist.execution.created",
    "checklist.execution.canceled",
)

LEGACY_NOTIFICATION_SUBJECT_TYPES = (
    "action",
    "checklist_execution",
)


def _purge_legacy_notifications(apps, schema_editor) -> None:
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.filter(
        Q(event_key__in=LEGACY_NOTIFICATION_EVENT_KEYS)
        | Q(subject_type__in=LEGACY_NOTIFICATION_SUBJECT_TYPES)
    ).delete()


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("comments", "0004_comment_action_plan_execution"),
        ("observations", "0005_action_plan_task_observation"),
        ("notifications", "0003_action_plan_execution_notifications"),
        ("action_plans", "0005_actionplanexecution_cancel_origin"),
    ]

    operations = [
        migrations.RunPython(
            _purge_legacy_notifications,
            migrations.RunPython.noop,
        ),
    ]
