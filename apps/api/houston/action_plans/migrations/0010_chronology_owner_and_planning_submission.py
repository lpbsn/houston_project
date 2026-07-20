# Generated manually for chronology owner + planning submission

import django.db.models.deletion
import uuid
from django.db import migrations, models


def normalize_chronology_owner_mode(apps, schema_editor):
    ActionPlanExecution = apps.get_model("action_plans", "ActionPlanExecution")
    # Rows without an owner are shared-by-fact under the new CheckConstraint.
    ActionPlanExecution.objects.filter(chronology_owner_membership__isnull=True).update(
        use_shared_chronology=True
    )


class Migration(migrations.Migration):

    dependencies = [
        ("action_plans", "0009_execution_scheduled_status"),
        ("establishments", "0021_establishmentmembership_push_enabled"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="actionplanscheduleassignee",
            name="action_plan_schedule_assignee_end_after_start",
        ),
        migrations.RemoveField(
            model_name="actionplanscheduleassignee",
            name="end_at",
        ),
        migrations.RemoveField(
            model_name="actionplanscheduleassignee",
            name="start_at",
        ),
        migrations.RemoveConstraint(
            model_name="actionplanexecution",
            name="uniq_ap_exec_schedule_occurrence_individual",
        ),
        migrations.RenameField(
            model_name="actionplanexecution",
            old_name="schedule_source_membership",
            new_name="chronology_owner_membership",
        ),
        migrations.AlterField(
            model_name="actionplanexecution",
            name="chronology_owner_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="action_plan_chronology_owned_executions",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.RunPython(normalize_chronology_owner_mode, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="actionplanexecution",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(
                        ("use_shared_chronology", True),
                        ("chronology_owner_membership__isnull", True),
                    ),
                    models.Q(
                        ("use_shared_chronology", False),
                        ("chronology_owner_membership__isnull", False),
                    ),
                    _connector="OR",
                ),
                name="ap_exec_chronology_owner_matches_mode",
            ),
        ),
        migrations.AddConstraint(
            model_name="actionplanexecution",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("action_plan_schedule__isnull", False),
                    ("use_shared_chronology", False),
                    ("chronology_owner_membership__isnull", False),
                ),
                fields=(
                    "action_plan_schedule",
                    "occurrence_date",
                    "chronology_owner_membership",
                ),
                name="uniq_ap_exec_schedule_occurrence_individual",
            ),
        ),
        migrations.DeleteModel(name="ActionPlanMixedOutboxEntry"),
        migrations.DeleteModel(name="ActionPlanMixedSubmission"),
        migrations.CreateModel(
            name="ActionPlanPlanningSubmission",
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
                ("submission_id", models.UUIDField()),
                ("request_hash", models.CharField(max_length=64)),
                ("result_snapshot", models.JSONField(blank=True, default=dict)),
                (
                    "action_plan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="planning_submissions",
                        to="action_plans.actionplan",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="action_plan_planning_submissions_created",
                        to="establishments.establishmentmembership",
                    ),
                ),
                (
                    "establishment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="action_plan_planning_submissions",
                        to="establishments.establishment",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ActionPlanPlanningOutboxEntry",
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
                ("effect_key", models.CharField(max_length=255)),
                (
                    "effect_type",
                    models.CharField(
                        choices=[
                            ("notification", "Notification"),
                            ("realtime_invalidation", "Realtime invalidation"),
                        ],
                        max_length=32,
                    ),
                ),
                ("payload", models.JSONField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("processing", "Processing"),
                            ("processed", "Processed"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("available_at", models.DateTimeField()),
                ("lease_expires_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True, default="")),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "planning_submission",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="outbox_entries",
                        to="action_plans.actionplanplanningsubmission",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="actionplanplanningsubmission",
            constraint=models.UniqueConstraint(
                fields=("establishment", "created_by", "submission_id"),
                name="uniq_action_plan_planning_submission",
            ),
        ),
        migrations.AddIndex(
            model_name="actionplanplanningoutboxentry",
            index=models.Index(
                fields=["status", "available_at"],
                name="ap_plan_outbox_claim_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="actionplanplanningoutboxentry",
            index=models.Index(
                fields=["status", "lease_expires_at"],
                name="ap_plan_outbox_lease_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="actionplanplanningoutboxentry",
            constraint=models.UniqueConstraint(
                fields=("planning_submission", "effect_key"),
                name="uniq_action_plan_planning_outbox_effect",
            ),
        ),
    ]
