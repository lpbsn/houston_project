from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0005_alter_aiusagelog_ai_domain"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="aiusagelog",
            name="ai_usage_prop_idx",
        ),
        migrations.RemoveField(
            model_name="aiusagelog",
            name="onboarding_proposal",
        ),
        migrations.AlterField(
            model_name="aiusagelog",
            name="ai_domain",
            field=models.CharField(
                choices=[
                    ("transcription", "Transcription"),
                    ("observation_pipeline", "Observation pipeline"),
                    ("analytics_pattern", "Analytics pattern"),
                ],
                default="transcription",
                max_length=40,
            ),
        ),
    ]
