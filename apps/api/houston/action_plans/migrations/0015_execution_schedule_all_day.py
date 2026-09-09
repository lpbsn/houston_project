from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("action_plans", "0014_execution_history_baseline_and_deadline"),
    ]

    operations = [
        migrations.AddField(
            model_name="actionplanexecution",
            name="all_day",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="actionplanschedule",
            name="all_day",
            field=models.BooleanField(default=False),
        ),
    ]
