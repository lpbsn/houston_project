# Generated manually for Lot 6 action plan execution comments.

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("action_plans", "0002_action_plan_task_observation"),
        ("comments", "0003_rename_parent_comment_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
            name="action_plan_execution",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="comments",
                to="action_plans.actionplanexecution",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="comment",
            name="comment_exactly_one_parent",
        ),
        migrations.AddConstraint(
            model_name="comment",
            constraint=models.CheckConstraint(
                condition=(
                    Q(
                        ("action__isnull", True),
                        ("action_plan_execution__isnull", True),
                        ("signal__isnull", False),
                    )
                    | Q(
                        ("action__isnull", False),
                        ("action_plan_execution__isnull", True),
                        ("signal__isnull", True),
                    )
                    | Q(
                        ("action__isnull", True),
                        ("action_plan_execution__isnull", False),
                        ("signal__isnull", True),
                    )
                ),
                name="comment_exactly_one_parent",
            ),
        ),
        migrations.AddIndex(
            model_name="comment",
            index=models.Index(
                fields=["establishment", "action_plan_execution", "created_at", "id"],
                name="comments_co_establi_44e023_idx",
            ),
        ),
    ]
