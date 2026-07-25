from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signals", "0009_signal_routing_status_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="signal",
            name="routing_status",
            field=models.CharField(
                choices=[("resolved", "Resolved"), ("unassigned", "Unassigned")],
                max_length=20,
            ),
        ),
        migrations.RemoveConstraint(
            model_name="signal",
            name="signal_unique_active_aggregation_key",
        ),
        migrations.AddConstraint(
            model_name="signal",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("status__in", frozenset({"in_progress", "open"})),
                    ("routing_status", "resolved"),
                ),
                fields=(
                    "establishment",
                    "affected_business_unit",
                    "responsible_business_unit",
                    "activity_subject",
                    "operational_unit",
                    "issue_focus",
                ),
                name="signal_unique_active_aggregation_key",
                nulls_distinct=False,
            ),
        ),
    ]
