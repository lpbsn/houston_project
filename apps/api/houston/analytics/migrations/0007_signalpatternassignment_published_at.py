from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0006_history_coverage_and_sightings"),
    ]

    operations = [
        migrations.AddField(
            model_name="signalpatternassignment",
            name="published_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="signalpatternassignment",
            index=models.Index(
                fields=["classification_status", "published_at"],
                name="sig_pat_assign_published_idx",
            ),
        ),
    ]
