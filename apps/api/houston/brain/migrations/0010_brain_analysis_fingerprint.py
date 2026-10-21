from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("brain", "0009_brain_engine_trace"),
    ]

    operations = [
        migrations.AddField(
            model_name="brainanalysis",
            name="context_fingerprint",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddConstraint(
            model_name="brainanalysis",
            constraint=models.UniqueConstraint(
                condition=models.Q(status__in=["queued", "running", "completed"])
                & ~models.Q(context_fingerprint=""),
                fields=("establishment", "context_fingerprint"),
                name="brain_an_ctx_live_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="brainanalysis",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="running"),
                fields=("establishment",),
                name="brain_an_one_running",
            ),
        ),
        migrations.AddIndex(
            model_name="brainanalysis",
            index=models.Index(
                fields=["establishment", "status", "created_at"],
                name="brain_an_est_stat_cr_idx",
            ),
        ),
    ]
