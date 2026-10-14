import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("brain", "0005_brain_analysis_result"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BrainMessage",
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
                ("request_id", models.CharField(max_length=128)),
                ("sequence", models.PositiveIntegerField()),
                (
                    "purpose",
                    models.CharField(
                        choices=[
                            ("explain", "Explain"),
                            ("hypothesis", "Hypothesis"),
                            ("correction", "Correction"),
                            ("new_fact", "New fact"),
                            ("new_document", "New document"),
                        ],
                        max_length=32,
                    ),
                ),
                ("body", models.TextField()),
                ("cited_item_ids", models.JSONField(default=list)),
                ("declaration", models.JSONField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("canceled", "Canceled"),
                        ],
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("attempt_token", models.UUIDField(default=uuid.uuid4)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("transient_retries_used", models.PositiveIntegerField(default=0)),
                ("transport_republish_count", models.PositiveIntegerField(default=0)),
                ("transport_stall_since", models.DateTimeField(blank=True, null=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("claimed_at", models.DateTimeField(blank=True, null=True)),
                ("lease_expires_at", models.DateTimeField(blank=True, null=True)),
                ("cancel_requested_at", models.DateTimeField(blank=True, null=True)),
                ("failure_code", models.CharField(blank=True, default="", max_length=80)),
                ("reserved_input_tokens", models.PositiveIntegerField(default=0)),
                ("consumed_input_tokens", models.PositiveIntegerField(default=0)),
                ("provider_calls_used", models.PositiveIntegerField(default=0)),
                ("result", models.JSONField(blank=True, null=True)),
                (
                    "analysis",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="brain.brainanalysis",
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="authored_brain_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="brainslot",
            name="message",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="slots",
                to="brain.brainmessage",
            ),
        ),
        migrations.AddConstraint(
            model_name="brainmessage",
            constraint=models.UniqueConstraint(
                fields=("analysis", "request_id"),
                name="brain_msg_an_req_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="brainmessage",
            constraint=models.UniqueConstraint(
                fields=("analysis", "sequence"),
                name="brain_msg_an_seq_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="brainmessage",
            constraint=models.CheckConstraint(
                condition=models.Q(("sequence__gte", 1)),
                name="brain_msg_seq_chk",
            ),
        ),
        migrations.AddConstraint(
            model_name="brainmessage",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "purpose__in",
                        [
                            "explain",
                            "hypothesis",
                            "correction",
                            "new_fact",
                            "new_document",
                        ],
                    )
                ),
                name="brain_msg_purpose_chk",
            ),
        ),
        migrations.AddConstraint(
            model_name="brainmessage",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "status__in",
                        ["queued", "running", "completed", "failed", "canceled"],
                    )
                ),
                name="brain_msg_status_chk",
            ),
        ),
        migrations.AddIndex(
            model_name="brainmessage",
            index=models.Index(fields=["status", "created_at"], name="brain_msg_stat_cr_idx"),
        ),
        migrations.AddIndex(
            model_name="brainmessage",
            index=models.Index(fields=["author"], name="brain_msg_author_idx"),
        ),
        migrations.AddIndex(
            model_name="brainslot",
            index=models.Index(fields=["message"], name="brain_slot_message_idx"),
        ),
        migrations.AddConstraint(
            model_name="brainslot",
            constraint=models.CheckConstraint(
                condition=models.Q(kind="analysis", message__isnull=True)
                | models.Q(kind="follow_up", message__isnull=False),
                name="brain_slot_msg_kind_chk",
            ),
        ),
    ]
