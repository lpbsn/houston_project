# Lot 10A: remove checklist observation origin fields.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_purge_legacy_cross_domain_references"),
        ("observations", "0005_action_plan_task_observation"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="observation",
            name="checklist_execution",
        ),
        migrations.RemoveField(
            model_name="observation",
            name="checklist_task_execution",
        ),
        migrations.AlterField(
            model_name="observation",
            name="origin",
            field=models.CharField(
                choices=[
                    ("direct_report", "Direct report"),
                    ("action_plan_task", "Action plan task"),
                ],
                default="direct_report",
                max_length=40,
            ),
        ),
    ]
