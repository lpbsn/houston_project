import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("action_plans", "0016_backfill_execution_start_at_when_end_at"),
        ("comments", "0005_commentmention_membership_comment_idx"),
        ("establishments", "0019_drop_orphan_legacy_taxonomy_tables"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActionPlanCommentUpload",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("original_filename", models.CharField(max_length=255)),
                ("declared_content_type", models.CharField(max_length=120)),
                ("declared_size_bytes", models.PositiveIntegerField()),
                ("content_type", models.CharField(blank=True, default="", max_length=120)),
                ("size_bytes", models.PositiveIntegerField(blank=True, null=True)),
                ("kind", models.CharField(blank=True, default="", max_length=16)),
                ("storage_key", models.CharField(max_length=512)),
                ("thumbnail_storage_key", models.CharField(blank=True, default="", max_length=512)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("reserved", "Reserved"),
                            ("validated", "Validated"),
                            ("linked", "Linked"),
                            ("expired", "Expired"),
                        ],
                        default="reserved",
                        max_length=20,
                    ),
                ),
                ("expires_at", models.DateTimeField()),
                ("linked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "action_plan_execution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comment_uploads",
                        to="action_plans.actionplanexecution",
                    ),
                ),
                (
                    "establishment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="action_plan_comment_uploads",
                        to="establishments.establishment",
                    ),
                ),
                (
                    "uploaded_by_membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="action_plan_comment_uploads",
                        to="establishments.establishmentmembership",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ActionPlanCommentAttachment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("position", models.PositiveSmallIntegerField()),
                ("kind", models.CharField(max_length=16)),
                ("content_type", models.CharField(max_length=120)),
                ("size_bytes", models.PositiveIntegerField()),
                ("original_filename", models.CharField(max_length=255)),
                (
                    "action_plan_execution",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comment_attachments",
                        to="action_plans.actionplanexecution",
                    ),
                ),
                (
                    "comment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="plan_comment_attachments",
                        to="comments.comment",
                    ),
                ),
                (
                    "upload",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachment",
                        to="comments.actionplancommentupload",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="actionplancommentupload",
            index=models.Index(
                fields=["action_plan_execution", "status", "expires_at"],
                name="apcmt_up_exec_status_exp_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="actionplancommentupload",
            index=models.Index(
                fields=["uploaded_by_membership", "status"],
                name="apcmt_up_member_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="actionplancommentattachment",
            index=models.Index(
                fields=["action_plan_execution", "created_at", "id"],
                name="apcmt_att_exec_created_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="actionplancommentattachment",
            constraint=models.UniqueConstraint(
                fields=("comment", "position"),
                name="uniq_action_plan_comment_attachment_position",
            ),
        ),
    ]
