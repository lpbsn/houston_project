from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("action_plans", "0018_execution_establishment_occurrence_idx"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="actionplanassignee",
            index=models.Index(
                fields=["membership", "visible_from"],
                name="ap_assignee_member_visible_idx",
            ),
        ),
        migrations.AlterField(
            model_name="actionplanassignee",
            name="membership",
            field=models.ForeignKey(
                db_index=False,
                on_delete=models.deletion.PROTECT,
                related_name="action_plan_execution_assignments",
                to="establishments.establishmentmembership",
            ),
        ),
    ]
