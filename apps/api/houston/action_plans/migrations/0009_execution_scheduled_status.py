from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("action_plans", "0008_actionplanmixedsubmission_actionplanmixedoutboxentry_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="actionplanexecution",
            name="availability_notified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="actionplanexecution",
            name="status",
            field=models.CharField(
                choices=[
                    ("scheduled", "Scheduled"),
                    ("in_progress", "In progress"),
                    ("pending_validation", "Pending validation"),
                    ("done", "Done"),
                    ("canceled", "Canceled"),
                ],
                default="in_progress",
                max_length=32,
            ),
        ),
        migrations.AddIndex(
            model_name="actionplanexecution",
            index=models.Index(
                condition=models.Q(("status", "scheduled")),
                fields=["status", "start_at"],
                name="ap_exec_scheduled_promote_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="actionplanexecution",
            index=models.Index(
                condition=models.Q(
                    ("availability_notified_at__isnull", True),
                    ("status", "scheduled"),
                ),
                fields=["status", "visible_from"],
                name="ap_exec_scheduled_avail_idx",
            ),
        ),
    ]
