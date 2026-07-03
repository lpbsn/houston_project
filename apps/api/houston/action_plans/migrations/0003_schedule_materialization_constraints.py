# Generated manually for Lot 4 schedule materialization

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("action_plans", "0002_action_plan_task_observation"),
    ]

    operations = [
        migrations.AddField(
            model_name="actionplanexecution",
            name="schedule_source_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="action_plan_schedule_sourced_executions",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddConstraint(
            model_name="actionplanexecution",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("action_plan_schedule__isnull", False),
                    ("use_shared_chronology", True),
                ),
                fields=("action_plan_schedule", "occurrence_date"),
                name="uniq_ap_exec_schedule_occurrence_shared",
            ),
        ),
        migrations.AddConstraint(
            model_name="actionplanexecution",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("action_plan_schedule__isnull", False),
                    ("use_shared_chronology", False),
                    ("schedule_source_membership__isnull", False),
                ),
                fields=(
                    "action_plan_schedule",
                    "occurrence_date",
                    "schedule_source_membership",
                ),
                name="uniq_ap_exec_schedule_occurrence_individual",
            ),
        ),
    ]
