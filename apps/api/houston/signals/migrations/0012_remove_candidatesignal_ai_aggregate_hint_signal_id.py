from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("signals", "0011_signal_merged_into_and_merged_from_link"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="candidatesignal",
            name="ai_aggregate_hint_signal_id",
        ),
    ]
