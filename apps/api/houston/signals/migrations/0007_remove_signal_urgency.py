from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signals", "0006_signal_unique_active_aggregation_key"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="signal",
            name="signal_feed_sort_idx",
        ),
        migrations.RemoveField(
            model_name="signal",
            name="urgency",
        ),
        migrations.AddIndex(
            model_name="signal",
            index=models.Index(
                fields=[
                    "establishment",
                    "status",
                    "is_pinned",
                    "last_activity_at",
                ],
                name="signal_feed_sort_idx",
            ),
        ),
    ]
