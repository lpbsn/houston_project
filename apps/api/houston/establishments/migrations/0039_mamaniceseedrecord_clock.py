from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0038_mamaniceseedrecord_object_kind_uniq"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mamaniceseedrecord",
            name="object_type",
            field=models.CharField(
                choices=[
                    ("membership", "Membership"),
                    ("observation", "Observation"),
                    ("signal", "Signal"),
                    ("pattern", "Pattern"),
                    ("plan", "Plan"),
                    ("schedule", "Schedule"),
                    ("execution", "Execution"),
                    ("comment", "Comment"),
                    ("review", "Review"),
                    ("season", "Season"),
                    ("operational_unit", "Operational unit"),
                    ("clock", "Clock"),
                ],
                max_length=32,
            ),
        ),
    ]
