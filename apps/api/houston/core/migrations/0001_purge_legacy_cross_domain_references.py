"""Lot 10A: purge cross-domain legacy references before RemoveField migrations."""

from __future__ import annotations

from django.db import migrations
from django.db.models import Count, Q


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


def _delete_action_comments(apps, schema_editor) -> None:
    Comment = apps.get_model("comments", "Comment")
    CommentMention = apps.get_model("comments", "CommentMention")
    action_comment_ids = Comment.objects.filter(action_id__isnull=False).values_list(
        "id", flat=True
    )
    if not action_comment_ids.exists():
        return

    while True:
        leaf_ids = list(
            Comment.objects.filter(action_id__isnull=False)
            .annotate(reply_count=Count("replies"))
            .filter(reply_count=0)
            .values_list("id", flat=True)[:1000]
        )
        if not leaf_ids:
            remaining = Comment.objects.filter(action_id__isnull=False).count()
            if remaining:
                CommentMention.objects.filter(
                    comment_id__in=Comment.objects.filter(action_id__isnull=False)
                ).delete()
                Comment.objects.filter(action_id__isnull=False).delete()
            break
        CommentMention.objects.filter(comment_id__in=leaf_ids).delete()
        Comment.objects.filter(id__in=leaf_ids).delete()


def _purge_legacy_notifications(apps, schema_editor) -> None:
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.filter(
        Q(event_key__in=LEGACY_NOTIFICATION_EVENT_KEYS)
        | Q(subject_type__in=LEGACY_NOTIFICATION_SUBJECT_TYPES)
    ).delete()


def _purge_checklist_origin_observations(apps, schema_editor) -> None:
    Observation = apps.get_model("observations", "Observation")
    ObservationMedia = apps.get_model("observations", "ObservationMedia")
    ObservationProcessing = apps.get_model("observations", "ObservationProcessing")

    checklist_observation_ids = list(
        Observation.objects.filter(origin="checklist_task").values_list("id", flat=True)
    )
    if checklist_observation_ids:
        ObservationMedia.objects.filter(observation_id__in=checklist_observation_ids).delete()
        ObservationProcessing.objects.filter(observation_id__in=checklist_observation_ids).delete()
        Observation.objects.filter(id__in=checklist_observation_ids).delete()

    Observation.objects.filter(
        Q(checklist_execution_id__isnull=False) | Q(checklist_task_execution_id__isnull=False)
    ).update(
        checklist_execution_id=None,
        checklist_task_execution_id=None,
    )


def purge_legacy_cross_domain_references(apps, schema_editor) -> None:
    _purge_legacy_notifications(apps, schema_editor)
    _delete_action_comments(apps, schema_editor)
    _purge_checklist_origin_observations(apps, schema_editor)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("comments", "0004_comment_action_plan_execution"),
        ("observations", "0005_action_plan_task_observation"),
        ("notifications", "0003_action_plan_execution_notifications"),
        ("actions", "0005_multi_assignee_phase1"),
        ("checklists", "0012_align_execution_source_constraint"),
        ("action_plans", "0005_actionplanexecution_cancel_origin"),
    ]

    operations = [
        migrations.RunPython(
            purge_legacy_cross_domain_references,
            migrations.RunPython.noop,
        ),
    ]
