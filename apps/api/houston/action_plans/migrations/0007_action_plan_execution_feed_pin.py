import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("action_plans", "0006_action_plan_task_enrichment"),
        ("establishments", "0020_establishmentmembership_notifications_enabled"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActionPlanExecutionFeedPin",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("pinned_at", models.DateTimeField(auto_now_add=True)),
                (
                    "action_plan_execution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feed_pins",
                        to="action_plans.actionplanexecution",
                    ),
                ),
                (
                    "membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="action_plan_execution_feed_pins",
                        to="establishments.establishmentmembership",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["membership", "pinned_at"],
                        name="ap_exec_feed_pin_idx",
                    )
                ],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("membership", "action_plan_execution"),
                        name="uniq_action_plan_execution_feed_pin",
                    )
                ],
            },
        ),
    ]
