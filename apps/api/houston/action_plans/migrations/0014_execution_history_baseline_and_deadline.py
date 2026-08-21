from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("action_plans", "0013_actionplanexecutionreview"),
    ]

    operations = [
        migrations.AlterField(
            model_name="actionplanexecutionlifecycleevent",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("action_plan_execution.created", "Created"),
                    ("action_plan_execution.started", "Started"),
                    ("action_plan_execution.history_baseline", "History baseline"),
                    ("action_plan_execution.deadline_changed", "Deadline changed"),
                    ("action_plan_execution.marked_done", "Marked done"),
                    ("action_plan_execution.validated", "Validated"),
                    ("action_plan_execution.canceled", "Canceled"),
                    ("action_plan_execution.reopened", "Reopened"),
                    ("action_plan_execution.reactivated", "Reactivated"),
                ],
                max_length=64,
            ),
        ),
        migrations.AddConstraint(
            model_name="actionplanexecutionlifecycleevent",
            constraint=models.UniqueConstraint(
                condition=models.Q(("event_type", "action_plan_execution.history_baseline")),
                fields=("action_plan_execution",),
                name="ap_exec_lifecycle_one_baseline",
            ),
        ),
    ]
