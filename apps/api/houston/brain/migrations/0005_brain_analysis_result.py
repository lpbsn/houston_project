from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("brain", "0004_brain_runtime"),
    ]

    operations = [
        migrations.AddField(
            model_name="brainanalysis",
            name="result",
            field=models.JSONField(blank=True, null=True),
        ),
    ]
