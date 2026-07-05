# Lot 10A: remove legacy Action comment parent FK.

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_purge_legacy_cross_domain_references"),
        ("comments", "0004_comment_action_plan_execution"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="comment",
            name="comment_exactly_one_parent",
        ),
        migrations.RemoveIndex(
            model_name="comment",
            name="comments_co_establi_8fd39c_idx",
        ),
        migrations.RemoveField(
            model_name="comment",
            name="action",
        ),
        migrations.AddConstraint(
            model_name="comment",
            constraint=models.CheckConstraint(
                condition=(
                    Q(
                        signal__isnull=False,
                        action_plan_execution__isnull=True,
                    )
                    | Q(
                        signal__isnull=True,
                        action_plan_execution__isnull=False,
                    )
                ),
                name="comment_exactly_one_parent",
            ),
        ),
    ]
