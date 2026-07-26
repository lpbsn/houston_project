from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("signals", "0010_signal_routing_status_non_null_and_resolved_unique"),
    ]

    operations = [
        migrations.AddField(
            model_name="signal",
            name="merged_into",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="merged_sources",
                to="signals.signal",
            ),
        ),
        migrations.AlterField(
            model_name="signalsourceobservation",
            name="link_type",
            field=models.CharField(
                choices=[
                    ("created_from", "Created from"),
                    ("aggregated_from", "Aggregated from"),
                    ("merged_from", "Merged from"),
                ],
                max_length=32,
            ),
        ),
    ]
