# Generated manually for shared checklist scheduling v2

from django.db import migrations, models


def _purge_shared_checklist_runtime_data(apps, schema_editor):
    ChecklistAssignment = apps.get_model("checklists", "ChecklistAssignment")
    ChecklistExecution = apps.get_model("checklists", "ChecklistExecution")
    ChecklistExecution.objects.filter(checklist_assignment__isnull=False).delete()
    ChecklistAssignment.objects.all().delete()


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("checklists", "0004_checklisttask_single_task_field"),
    ]

    operations = [
        migrations.RunPython(_purge_shared_checklist_runtime_data, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="checklistassignment",
            name="checklist_assignment_due_after_start",
        ),
        migrations.RemoveField(
            model_name="checklistassignment",
            name="start_at",
        ),
        migrations.RemoveField(
            model_name="checklistassignment",
            name="due_at",
        ),
        migrations.AddField(
            model_name="checklistassignment",
            name="start_date",
            field=models.DateField(),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="checklistassignment",
            name="end_date",
            field=models.DateField(),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="checklistassignment",
            name="start_at",
            field=models.TimeField(),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="checklistassignment",
            name="end_at",
            field=models.TimeField(),
            preserve_default=False,
        ),
        migrations.RenameField(
            model_name="checklistexecution",
            old_name="due_at",
            new_name="end_at",
        ),
        migrations.RemoveConstraint(
            model_name="checklistexecution",
            name="checklist_execution_personal_no_due_at",
        ),
        migrations.AddConstraint(
            model_name="checklistassignment",
            constraint=models.CheckConstraint(
                condition=models.Q(("end_date__gte", models.F("start_date"))),
                name="checklist_assignment_end_date_on_or_after_start",
            ),
        ),
        migrations.AddConstraint(
            model_name="checklistassignment",
            constraint=models.CheckConstraint(
                condition=models.Q(("end_at__gt", models.F("start_at"))),
                name="checklist_assignment_end_after_start_time",
            ),
        ),
        migrations.AddConstraint(
            model_name="checklistexecution",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("checklist_type", "personal"),
                    ("end_at__isnull", True),
                )
                | models.Q(("checklist_type", "shared")),
                name="checklist_execution_personal_no_end_at",
            ),
        ),
    ]
