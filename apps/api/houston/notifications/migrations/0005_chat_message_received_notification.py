from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0004_remove_legacy_notification_enums"),
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
                    ("chat.message.received", "Chat message received"),
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
                    ("chat_conversation", "Chat conversation"),
                    ("comment", "Comment"),
                    ("signal", "Signal"),
                ],
                max_length=32,
            ),
        ),
    ]
