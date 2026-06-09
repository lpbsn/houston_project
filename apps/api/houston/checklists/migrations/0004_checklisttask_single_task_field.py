from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("checklists", "0003_alter_checklistassignment_checklist_template"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="checklisttasktemplate",
            name="title",
        ),
        migrations.RemoveField(
            model_name="checklisttasktemplate",
            name="instructions",
        ),
        migrations.AddField(
            model_name="checklisttasktemplate",
            name="task",
            field=models.CharField(max_length=500),
        ),
        migrations.RemoveField(
            model_name="checklisttaskexecution",
            name="title",
        ),
        migrations.RemoveField(
            model_name="checklisttaskexecution",
            name="instructions",
        ),
        migrations.AddField(
            model_name="checklisttaskexecution",
            name="task",
            field=models.CharField(max_length=500),
        ),
    ]
