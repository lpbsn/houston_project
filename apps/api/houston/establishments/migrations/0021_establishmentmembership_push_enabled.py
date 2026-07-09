from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0020_establishmentmembership_notifications_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="establishmentmembership",
            name="push_enabled",
            field=models.BooleanField(default=False),
        ),
    ]
