# Generated manually for checklist closure

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("checklists", "0010_purge_checklist_data_and_remove_flash_todo"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="checklisttemplate",
            name="checklists__establi_3fd9c0_idx",
        ),
        migrations.RemoveField(
            model_name="checklisttemplate",
            name="badge",
        ),
    ]
