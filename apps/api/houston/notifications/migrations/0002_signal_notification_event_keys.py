from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="event_key",
            field=models.CharField(
                choices=[
                    ("action.created", "Action created"),
                    ("action.reassigned", "Action reassigned"),
                    ("action.pending_validation", "Action pending validation"),
                    ("action.reopened", "Action reopened"),
                    ("action.canceled", "Action canceled"),
                    ("checklist.execution.created", "Checklist execution created"),
                    ("checklist.execution.canceled", "Checklist execution canceled"),
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
    ]
