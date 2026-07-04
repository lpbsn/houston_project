# Lot 10A: remove legacy action/checklist notification enums.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_purge_legacy_cross_domain_references"),
        ("notifications", "0003_action_plan_execution_notifications"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="event_key",
            field=models.CharField(
                choices=[
                    ("action_plan.execution.created", "Action plan execution created"),
                    (
                        "action_plan.execution.pending_validation",
                        "Action plan execution pending validation",
                    ),
                    ("action_plan.execution.canceled", "Action plan execution canceled"),
                    ("action_plan.execution.reopened", "Action plan execution reopened"),
                    ("comment.mention.created", "Comment mention created"),
                    ("signal.created", "Signal created"),
                    ("signal.urgency_changed", "Signal urgency changed"),
                    ("signal.pinned", "Signal pinned"),
                    ("signal.resolved", "Signal resolved"),
                    ("signal.canceled", "Signal canceled"),
                ],
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="subject_type",
            field=models.CharField(
                choices=[
                    ("action_plan_execution", "Action plan execution"),
                    ("comment", "Comment"),
                    ("signal", "Signal"),
                ],
                max_length=32,
            ),
        ),
    ]
