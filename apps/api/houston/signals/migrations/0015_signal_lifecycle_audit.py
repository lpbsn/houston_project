# Generated manually for EVO-AUD-01 Signal lifecycle audit fields + journal.

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("establishments", "0030_seed_onboarding_drafts"),
        ("signals", "0014_signal_resolution_request"),
    ]

    operations = [
        migrations.AddField(
            model_name="signal",
            name="archived_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="signal",
            name="archived_by_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="archived_signals",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddField(
            model_name="signal",
            name="canceled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="signal",
            name="canceled_by_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="canceled_signals",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddField(
            model_name="signal",
            name="marked_interesting_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="signal",
            name="marked_interesting_by_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="marked_interesting_signals",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.AddField(
            model_name="signal",
            name="resolution_origin",
            field=models.CharField(
                blank=True,
                choices=[
                    ("manual", "Manual"),
                    ("resolution_request", "Resolution request"),
                    ("action_plan", "Action plan"),
                ],
                max_length=32,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="signal",
            name="resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="signal",
            name="resolved_by_membership",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="resolved_signals",
                to="establishments.establishmentmembership",
            ),
        ),
        migrations.CreateModel(
            name="SignalLifecycleEvent",
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
                            ("signal.marked_interesting", "Marked interesting"),
                            ("signal.archived", "Archived"),
                            ("signal.resolved", "Resolved"),
                            ("signal.canceled", "Canceled"),
                            ("signal.moved_in_progress", "Moved in progress"),
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
                        related_name="signal_lifecycle_events",
                        to="establishments.establishmentmembership",
                    ),
                ),
                (
                    "establishment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="signal_lifecycle_events",
                        to="establishments.establishment",
                    ),
                ),
                (
                    "signal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lifecycle_events",
                        to="signals.signal",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["signal", "occurred_at"],
                        name="sig_lifecycle_signal_at_idx",
                    ),
                    models.Index(
                        fields=["establishment", "occurred_at"],
                        name="sig_lifecycle_est_at_idx",
                    ),
                ],
            },
        ),
    ]
