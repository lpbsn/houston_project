import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0030_seed_onboarding_drafts"),
    ]

    operations = [
        migrations.CreateModel(
            name="MembershipBlock",
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
                    "blocked_membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="blocks_received",
                        to="establishments.establishmentmembership",
                    ),
                ),
                (
                    "blocker_membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="blocks_created",
                        to="establishments.establishmentmembership",
                    ),
                ),
                (
                    "establishment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="membership_blocks",
                        to="establishments.establishment",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ContentReport",
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
                ("content_kind", models.CharField(max_length=32)),
                ("content_id", models.UUIDField(blank=True, null=True)),
                ("reason", models.CharField(max_length=500)),
                ("status", models.CharField(default="open", max_length=20)),
                (
                    "establishment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_reports",
                        to="establishments.establishment",
                    ),
                ),
                (
                    "reporter_membership",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_reports_filed",
                        to="establishments.establishmentmembership",
                    ),
                ),
                (
                    "target_membership",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content_reports_received",
                        to="establishments.establishmentmembership",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="membershipblock",
            constraint=models.UniqueConstraint(
                fields=("blocker_membership", "blocked_membership"),
                name="unique_membership_block_pair",
            ),
        ),
        migrations.AddConstraint(
            model_name="membershipblock",
            constraint=models.CheckConstraint(
                condition=~Q(blocker_membership=F("blocked_membership")),
                name="membership_block_not_self",
            ),
        ),
        migrations.AddIndex(
            model_name="membershipblock",
            index=models.Index(fields=["establishment"], name="membership_block_est_idx"),
        ),
        migrations.AddIndex(
            model_name="contentreport",
            index=models.Index(
                fields=["establishment", "status"],
                name="content_report_est_status_idx",
            ),
        ),
    ]
