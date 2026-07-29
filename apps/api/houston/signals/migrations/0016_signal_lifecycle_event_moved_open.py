# Add signal.moved_open to SignalLifecycleEvent.event_type choices.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signals", "0015_signal_lifecycle_audit"),
    ]

    operations = [
        migrations.AlterField(
            model_name="signallifecycleevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("signal.marked_interesting", "Marked interesting"),
                    ("signal.archived", "Archived"),
                    ("signal.resolved", "Resolved"),
                    ("signal.canceled", "Canceled"),
                    ("signal.moved_in_progress", "Moved in progress"),
                    ("signal.moved_open", "Moved open"),
                ],
                max_length=64,
            ),
        ),
    ]
