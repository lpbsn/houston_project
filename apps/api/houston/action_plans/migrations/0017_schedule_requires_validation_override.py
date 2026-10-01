from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("action_plans", "0016_backfill_execution_start_at_when_end_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="actionplanschedule",
            name="requires_validation_override",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
