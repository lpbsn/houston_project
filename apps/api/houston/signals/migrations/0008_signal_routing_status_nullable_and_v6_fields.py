from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("signals", "0007_remove_signal_urgency"),
    ]

    operations = [
        migrations.AddField(
            model_name="signal",
            name="routing_status",
            field=models.CharField(
                choices=[("resolved", "Resolved"), ("unassigned", "Unassigned")],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="signal",
            name="expected_action",
            field=models.CharField(
                blank=True,
                choices=[
                    ("clean_secure", "Clean / secure"),
                    ("repair", "Repair"),
                    ("replenish", "Replenish"),
                    ("inspect", "Inspect"),
                    ("coordinate", "Coordinate"),
                    ("assist", "Assist"),
                    ("inform", "Inform"),
                    ("monitor", "Monitor"),
                    ("safety_response", "Safety response"),
                ],
                max_length=32,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="signal_kind",
            field=models.CharField(
                blank=True,
                choices=[
                    ("actionable", "Actionable"),
                    ("informational", "Informational"),
                ],
                max_length=32,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="information_type",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="canonical_object",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="expected_action",
            field=models.CharField(
                blank=True,
                choices=[
                    ("clean_secure", "Clean / secure"),
                    ("repair", "Repair"),
                    ("replenish", "Replenish"),
                    ("inspect", "Inspect"),
                    ("coordinate", "Coordinate"),
                    ("assist", "Assist"),
                    ("inform", "Inform"),
                    ("monitor", "Monitor"),
                    ("safety_response", "Safety response"),
                ],
                max_length=32,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="proposed_affected_business_unit_routing_key",
            field=models.CharField(blank=True, default="", max_length=180),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="proposed_responsible_business_unit_routing_key",
            field=models.CharField(blank=True, default="", max_length=180),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="proposed_activity_subject_routing_key",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="routing_status",
            field=models.CharField(
                blank=True,
                choices=[("resolved", "Resolved"), ("unassigned", "Unassigned")],
                max_length=20,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="resolution_audit",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="candidatesignal",
            name="rejection_code",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
    ]
