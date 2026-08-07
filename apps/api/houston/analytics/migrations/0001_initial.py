import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("establishments", "0030_seed_onboarding_drafts"),
        ("organizations", "0001_initial"),
        ("signals", "0016_signal_lifecycle_event_moved_open"),
    ]

    operations = [
        migrations.CreateModel(
            name="OperationalPattern",
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
                ("label", models.CharField(max_length=255)),
                (
                    "normalized_label",
                    models.CharField(blank=True, editable=False, max_length=255),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("merged", "Merged"),
                            ("retired", "Retired"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "created_by_membership",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_operational_patterns",
                        to="establishments.establishmentmembership",
                    ),
                ),
                (
                    "merged_into",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="merged_patterns",
                        to="analytics.operationalpattern",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="operational_patterns",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["organization", "status"],
                        name="pattern_org_status_idx",
                    ),
                    models.Index(
                        fields=["organization", "normalized_label"],
                        name="pattern_org_label_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("status", "active")),
                        fields=("organization", "normalized_label"),
                        name="analytics_pattern_active_label_uniq",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("normalized_label", ""),
                            _negated=True,
                        ),
                        name="analytics_pattern_norm_label_nonempty",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            ("merged_into__isnull", False),
                            ("status", "merged"),
                        )
                        | models.Q(
                            ("merged_into__isnull", True),
                            ("status__in", ["active", "retired"]),
                        ),
                        name="analytics_pattern_merge_target_state",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="PatternLifecycleEvent",
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
                            ("created", "Created"),
                            ("merged", "Merged"),
                            ("retired", "Retired"),
                        ],
                        max_length=64,
                    ),
                ),
                ("occurred_at", models.DateTimeField()),
                ("metadata_safe", models.JSONField(blank=True, default=dict)),
                (
                    "actor_membership",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pattern_lifecycle_events",
                        to="establishments.establishmentmembership",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pattern_lifecycle_events",
                        to="organizations.organization",
                    ),
                ),
                (
                    "pattern",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lifecycle_events",
                        to="analytics.operationalpattern",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["pattern", "occurred_at"],
                        name="pattern_event_at_idx",
                    ),
                    models.Index(
                        fields=["organization", "occurred_at"],
                        name="pattern_org_at_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="PatternIssueReport",
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
                ("report_type", models.CharField(max_length=64)),
                ("comment", models.TextField(blank=True, default="", max_length=500)),
                (
                    "status",
                    models.CharField(
                        choices=[("open", "Open"), ("reviewed", "Reviewed")],
                        default="open",
                        max_length=20,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pattern_issue_reports",
                        to="organizations.organization",
                    ),
                ),
                (
                    "pattern",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="issue_reports",
                        to="analytics.operationalpattern",
                    ),
                ),
                (
                    "reported_by_membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="pattern_issue_reports_submitted",
                        to="establishments.establishmentmembership",
                    ),
                ),
                (
                    "signal",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pattern_issue_reports",
                        to="signals.signal",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["pattern", "status"],
                        name="pattern_report_status_idx",
                    ),
                    models.Index(
                        fields=["organization", "status"],
                        name="pattern_org_report_status_idx",
                    ),
                    models.Index(fields=["signal"], name="pattern_report_signal_idx"),
                ],
            },
        ),
    ]
