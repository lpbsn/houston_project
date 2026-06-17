# Generated manually for checklist closure

from django.db import migrations, models


def purge_all_checklist_data(apps, schema_editor):
    ChecklistTaskExecution = apps.get_model("checklists", "ChecklistTaskExecution")
    ChecklistExecution = apps.get_model("checklists", "ChecklistExecution")
    ChecklistAssignment = apps.get_model("checklists", "ChecklistAssignment")
    ChecklistTaskTemplate = apps.get_model("checklists", "ChecklistTaskTemplate")
    ChecklistTemplate = apps.get_model("checklists", "ChecklistTemplate")
    Observation = apps.get_model("observations", "Observation")

    task_execution_ids = list(ChecklistTaskExecution.objects.values_list("id", flat=True))
    execution_ids = list(ChecklistExecution.objects.values_list("id", flat=True))

    if task_execution_ids:
        Observation.objects.filter(
            checklist_task_execution_id__in=task_execution_ids,
        ).update(checklist_task_execution_id=None)
    if execution_ids:
        Observation.objects.filter(
            checklist_execution_id__in=execution_ids,
        ).update(checklist_execution_id=None)

    ChecklistTaskExecution.objects.all().delete()
    ChecklistExecution.objects.all().delete()
    ChecklistAssignment.objects.all().delete()
    ChecklistTaskTemplate.objects.all().delete()
    ChecklistTemplate.objects.all().delete()


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("checklists", "0009_allow_detached_terminal_template_executions"),
        ("observations", "0004_observation_checklist_origin"),
    ]

    operations = [
        migrations.RunPython(purge_all_checklist_data, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="checklistexecution",
            name="checklist_execution_source_shape",
        ),
        migrations.AlterField(
            model_name="checklistexecution",
            name="execution_source",
            field=models.CharField(
                choices=[
                    ("template", "Template"),
                    ("assignment", "Assignment"),
                ],
                default="template",
                max_length=16,
            ),
        ),
        migrations.AddConstraint(
            model_name="checklistexecution",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("business_unit__isnull", False),
                        ("checklist_assignment__isnull", False),
                        ("execution_source", "assignment"),
                    )
                    | models.Q(
                        ("business_unit__isnull", False),
                        ("checklist_template__isnull", False),
                        ("checklist_assignment__isnull", True),
                        ("execution_source", "template"),
                    )
                    | models.Q(
                        ("business_unit__isnull", False),
                        ("checklist_template__isnull", True),
                        ("checklist_assignment__isnull", True),
                        ("execution_source", "template"),
                        ("status__in", ["done", "canceled"]),
                    ),
                    _connector="OR",
                ),
                name="checklist_execution_source_shape",
            ),
        ),
    ]
