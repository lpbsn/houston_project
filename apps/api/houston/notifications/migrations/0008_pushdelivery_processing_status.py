from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0007_webpushsubscription_pushdelivery"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pushdelivery",
            name="status",
            field=models.CharField(
                choices=[
                    ("queued", "Queued"),
                    ("processing", "Processing"),
                    ("sent", "Sent"),
                    ("failed", "Failed"),
                    ("skipped", "Skipped"),
                ],
                default="queued",
                max_length=16,
            ),
        ),
    ]
