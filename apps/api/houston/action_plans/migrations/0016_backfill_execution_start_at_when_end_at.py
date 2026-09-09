from django.db import migrations
from django.db.models import F


def backfill_execution_start_at_when_end_at(apps, schema_editor):
    ActionPlanExecution = apps.get_model("action_plans", "ActionPlanExecution")
    ActionPlanExecution.objects.filter(
        start_at__isnull=True,
        end_at__isnull=False,
        created_at__lt=F("end_at"),
    ).update(start_at=F("created_at"))


class Migration(migrations.Migration):
    dependencies = [
        ("action_plans", "0015_execution_schedule_all_day"),
    ]

    operations = [
        migrations.RunPython(
            backfill_execution_start_at_when_end_at,
            migrations.RunPython.noop,
        ),
    ]
