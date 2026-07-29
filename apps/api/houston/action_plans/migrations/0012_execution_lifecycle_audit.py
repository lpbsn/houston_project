# Generated manually for EVO-AUD-02 ActionPlanExecution lifecycle audit fields + journal.

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("action_plans", "0011_remove_actionplanexecution_ap_exec_chronology_owner_matches_mode_and_more"),
        ("establishments", "0030_seed_onboarding_drafts"),
    ]

    operations = [
        migrations.AddField(
            model_name="actionplanexecution",
            name="canceled_by_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="action_plan_executions_canceled",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddField(
            model_name="actionplanexecution",
            name="marked_done_by_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="action_plan_executions_marked_done",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddField(
            model_name="actionplanexecution",
            name="reactivated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="actionplanexecution",
            name="reactivated_by_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="action_plan_executions_reactivated",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddField(
            model_name="actionplanexecution",
            name="reopened_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="actionplanexecution",
            name="reopened_by_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="action_plan_executions_reopened",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddField(
            model_name="actionplanexecution",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="actionplanexecution",
            name="started_by_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="action_plan_executions_started",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddField(
            model_name="actionplanexecution",
            name="validated_by_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="action_plan_executions_validated",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.CreateModel(
            name="ActionPlanExecutionLifecycleEvent",
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
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("action_plan_execution.created", "Created"),
                            ("action_plan_execution.started", "Started"),
                            ("action_plan_execution.marked_done", "Marked done"),
                            ("action_plan_execution.validated", "Validated"),
                            ("action_plan_execution.canceled", "Canceled"),
                            ("action_plan_execution.reopened", "Reopened"),
                            ("action_plan_execution.reactivated", "Reactivated"),
                        ],
                        max_length=64,
                    ),
                ),
                ("occurred_at", models.DateTimeField()),
                ("metadata_safe", models.JSONField(blank=True, default=dict)),
                (
                    "action_plan_execution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lifecycle_events",
                        to="action_plans.actionplanexecution",
                    ),
                ),
                (
                    "actor_membership",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="action_plan_execution_lifecycle_events",
                        to="establishments.establishmentmembership",
                    ),
                ),
                (
                    "establishment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="action_plan_execution_lifecycle_events",
                        to="establishments.establishment",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["action_plan_execution", "occurred_at"],
                        name="ap_exec_lifecycle_exec_at_idx",
                    ),
                    models.Index(
                        fields=["establishment", "occurred_at"],
                        name="ap_exec_lifecycle_est_at_idx",
                    ),
                ],
            },
        ),
    ]
