from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0013_notification_idempotency_key_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="event_key",
            field=models.CharField(
                choices=[
                    ("action_plan.execution.created", "Action plan execution created"),
                    (
                        "action_plan.execution.created_from_signal",
                        "Action plan execution created from signal",
                    ),
                    (
                        "action_plan.execution.pending_validation",
                        "Action plan execution pending validation",
                    ),
                    ("action_plan.execution.canceled", "Action plan execution canceled"),
                    ("action_plan.execution.reopened", "Action plan execution reopened"),
                    ("action_plan.execution.started", "Action plan execution started"),
                    ("comment.mention.created", "Comment mention created"),
                    ("comment.signal.created", "Comment signal created"),
                    (
                        "comment.action_plan_execution.created",
                        "Comment action plan execution created",
                    ),
                    ("comment.reply.created", "Comment reply created"),
                    ("signal.created", "Signal created"),
                    (
                        "signal.created.unassigned_global",
                        "Signal created unassigned global",
                    ),
                    ("signal.pinned", "Signal pinned"),
                    ("signal.resolved", "Signal resolved"),
                    ("signal.canceled", "Signal canceled"),
                    ("chat.message.received", "Chat message received"),
                ],
                max_length=64,
            ),
        ),
    ]
