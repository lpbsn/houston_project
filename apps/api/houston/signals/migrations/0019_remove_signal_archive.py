from django.db import migrations, models

from houston.signals.migrations._archive_purge import noop_reverse, purge_archived_signals


class Migration(migrations.Migration):

    dependencies = [
        ("action_plans", "0016_backfill_execution_start_at_when_end_at"),
        ("analytics", "0006_history_coverage_and_sightings"),
        ("comments", "0005_commentmention_membership_comment_idx"),
        ("gamification", "0001_initial"),
        ("notifications", "0018_pushdevice"),
        ("observations", "0005_action_plan_task_observation"),
        ("signals", "0018_signal_first_action_plan_associated_at"),
    ]

    operations = [
        migrations.RunPython(purge_archived_signals, noop_reverse),
        migrations.RemoveField(
            model_name="signal",
            name="archived_at",
        ),
        migrations.RemoveField(
            model_name="signal",
            name="archived_by_membership",
        ),
        migrations.RemoveField(
            model_name="signal",
            name="merged_into",
        ),
        migrations.AlterField(
            model_name="signal",
            name="status",
            field=models.CharField(
                choices=[
                    ("open", "Open"),
                    ("interesting", "Interesting"),
                    ("in_progress", "In progress"),
                    ("resolved", "Resolved"),
                    ("canceled", "Canceled"),
                ],
                default="open",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="signallifecycleevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("signal.created", "Created"),
                    ("signal.history_baseline", "History baseline"),
                    ("signal.marked_interesting", "Marked interesting"),
                    ("signal.resolved", "Resolved"),
                    ("signal.canceled", "Canceled"),
                    ("signal.moved_in_progress", "Moved in progress"),
                    ("signal.moved_open", "Moved open"),
                ],
                max_length=64,
            ),
        ),
    ]
