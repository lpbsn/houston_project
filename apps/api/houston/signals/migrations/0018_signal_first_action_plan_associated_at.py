from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("signals", "0017_signal_created_and_history_baseline"),
    ]

    operations = [
        migrations.AddField(
            model_name="signal",
            name="first_action_plan_associated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
