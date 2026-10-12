from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ai", "0007_aiusagelog_brain_domain"),
    ]

    operations = [
        migrations.AlterField(
            model_name="aiusagelog",
            name="ai_domain",
            field=models.CharField(
                choices=[
                    ("transcription", "Transcription"),
                    ("observation_pipeline", "Observation pipeline"),
                    ("analytics_pattern", "Analytics pattern"),
                    ("brain_analysis", "Brain analysis"),
                    ("brain_follow_up", "Brain follow-up"),
                ],
                default="transcription",
                max_length=40,
            ),
        ),
    ]
