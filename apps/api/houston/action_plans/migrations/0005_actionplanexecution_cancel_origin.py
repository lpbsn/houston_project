# Generated manually for Lot 4 cancel_origin guard

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("action_plans", "0004_fix_schedule_occurrence_individual_constraint"),
    ]

    operations = [
        migrations.AddField(
            model_name="actionplanexecution",
            name="cancel_origin",
            field=models.CharField(
                blank=True,
                choices=[
                    ("manual", "Manual"),
                    ("schedule_sync", "Schedule sync"),
                ],
                max_length=32,
                null=True,
            ),
        ),
    ]
