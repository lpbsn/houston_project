from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0003_owner_corrections"),
    ]

    operations = [
        migrations.AlterField(
            model_name="patternlifecycleevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("created", "Created"),
                    ("merged", "Merged"),
                    ("renamed", "Renamed"),
                    ("retired", "Retired"),
                    ("split", "Split"),
                    ("signals_moved", "Signals moved"),
                ],
                max_length=64,
            ),
        ),
    ]
