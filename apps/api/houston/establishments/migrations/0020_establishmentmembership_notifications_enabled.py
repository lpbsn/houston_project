from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0019_drop_orphan_legacy_taxonomy_tables"),
    ]

    operations = [
        migrations.AddField(
            model_name="establishmentmembership",
            name="notifications_enabled",
            field=models.BooleanField(default=True),
        ),
    ]
