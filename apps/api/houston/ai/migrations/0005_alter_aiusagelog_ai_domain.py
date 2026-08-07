from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0004_aiusagelog_error_context"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aiusagelog",
            name="ai_domain",
            field=models.CharField(
                choices=[
                    ("onboarding", "Onboarding"),
                    ("transcription", "Transcription"),
                    ("observation_pipeline", "Observation pipeline"),
                    ("analytics_pattern", "Analytics pattern"),
                ],
                default="onboarding",
                max_length=40,
            ),
        ),
    ]
