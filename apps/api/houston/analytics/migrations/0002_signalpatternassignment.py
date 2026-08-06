import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("analytics", "0001_initial"),
        ("signals", "0016_signal_lifecycle_event_moved_open"),
    ]

    operations = [
        migrations.CreateModel(
            name="SignalPatternAssignment",
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
                    "classification_status",
                    models.CharField(
                        choices=[
                            ("not_started", "Not started"),
                            ("processing", "Processing"),
                            ("succeeded", "Succeeded"),
                            ("temporary_failed", "Temporary failed"),
                            ("permanently_failed", "Permanently failed"),
                        ],
                        default="not_started",
                        max_length=32,
                    ),
                ),
                (
                    "assigned_signature",
                    models.CharField(blank=True, default="", max_length=128),
                ),
                (
                    "assigned_classifier_version",
                    models.CharField(blank=True, default="", max_length=80),
                ),
                ("assigned_at", models.DateTimeField(blank=True, null=True)),
                (
                    "pending_signature",
                    models.CharField(blank=True, default="", max_length=128),
                ),
                (
                    "pending_classifier_version",
                    models.CharField(blank=True, default="", max_length=80),
                ),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("last_error_code", models.CharField(blank=True, default="", max_length=80)),
                ("last_attempted_at", models.DateTimeField(blank=True, null=True)),
                ("next_retry_at", models.DateTimeField(blank=True, null=True)),
                (
                    "pattern",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="signal_assignments",
                        to="analytics.operationalpattern",
                    ),
                ),
                (
                    "signal",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pattern_assignment",
                        to="signals.signal",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["classification_status", "next_retry_at"],
                        name="sig_pat_assign_retry_idx",
                    ),
                    models.Index(
                        fields=["pattern", "classification_status"],
                        name="sig_pat_asgn_pattern_st_idx",
                    ),
                ],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            ("classification_status", "succeeded"),
                            _negated=True,
                        )
                        | models.Q(("pattern__isnull", False)),
                        name="sig_pat_assign_succeeded_pattern",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("classification_status", "not_started"),
                            _negated=True,
                        )
                        | models.Q(("pattern__isnull", True)),
                        name="sig_pat_assign_not_started_null",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("pattern__isnull", False))
                        | models.Q(
                            ("assigned_at__isnull", True),
                            ("assigned_classifier_version", ""),
                            ("assigned_signature", ""),
                        ),
                        name="sig_pat_assign_null_empty_success",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(("pattern__isnull", True))
                        | (
                            models.Q(("assigned_signature", ""), _negated=True)
                            & models.Q(
                                ("assigned_classifier_version", ""),
                                _negated=True,
                            )
                            & models.Q(("assigned_at__isnull", False))
                        ),
                        name="sig_pat_assign_pattern_success_meta",
                    ),
                ],
            },
        ),
    ]
