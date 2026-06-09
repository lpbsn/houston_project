from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0016_drop_legacy_taxonomy"),
    ]

    operations = [
        migrations.AddField(
            model_name="establishment",
            name="timezone",
            field=models.CharField(default="Europe/Paris", max_length=63),
        ),
    ]
