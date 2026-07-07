from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("action_plans", "0005_actionplanexecution_cancel_origin"),
        ("establishments", "0020_establishmentmembership_notifications_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="actionplantask",
            name="assigned_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="action_plan_tasks_assigned",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddField(
            model_name="actionplantask",
            name="deadline_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="actionplantask",
            name="description",
            field=models.TextField(blank=True, default="", max_length=2000),
        ),
        migrations.AddField(
            model_name="actionplanexecutiontask",
            name="assigned_display_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="actionplanexecutiontask",
            name="assigned_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="action_plan_execution_tasks_assigned",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddField(
            model_name="actionplanexecutiontask",
            name="deadline_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="actionplanexecutiontask",
            name="description",
            field=models.TextField(blank=True, default="", max_length=2000),
        ),
    ]
