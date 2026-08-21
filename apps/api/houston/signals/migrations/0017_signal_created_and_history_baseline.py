from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signals", "0016_signal_lifecycle_event_moved_open"),
    ]

    operations = [
        migrations.AlterField(
            model_name="signallifecycleevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("signal.created", "Created"),
                    ("signal.history_baseline", "History baseline"),
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
        migrations.AddConstraint(
            model_name="signallifecycleevent",
            constraint=models.UniqueConstraint(
                condition=models.Q(("event_type", "signal.history_baseline")),
                fields=("signal",),
                name="sig_lifecycle_one_baseline",
            ),
        ),
    ]
