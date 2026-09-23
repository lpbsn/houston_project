import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0036_drop_onboarding_proposal"),
    ]

    operations = [
        migrations.CreateModel(
            name="MamaNiceSeedRecord",
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
                    "object_type",
                    models.CharField(
                        choices=[
                            ("membership", "Membership"),
                            ("observation", "Observation"),
                            ("signal", "Signal"),
                            ("pattern", "Pattern"),
                            ("plan", "Plan"),
                            ("schedule", "Schedule"),
                            ("execution", "Execution"),
                            ("comment", "Comment"),
                            ("review", "Review"),
                            ("season", "Season"),
                            ("operational_unit", "Operational unit"),
                        ],
                        max_length=32,
                    ),
                ),
                ("seed_key", models.CharField(max_length=180)),
                ("object_id", models.UUIDField()),
                ("fingerprint", models.CharField(max_length=64)),
                ("event_kind", models.CharField(max_length=64)),
                ("event_at", models.DateTimeField()),
                (
                    "establishment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mama_nice_seed_records",
                        to="establishments.establishment",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="mamaniceseedrecord",
            constraint=models.UniqueConstraint(
                fields=("establishment", "object_type", "seed_key"),
                name="mama_nice_seed_est_type_key_uniq",
            ),
        ),
        migrations.AddConstraint(
            model_name="mamaniceseedrecord",
            constraint=models.UniqueConstraint(
                fields=("establishment", "object_type", "object_id"),
                name="mama_nice_seed_est_type_object_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="mamaniceseedrecord",
            index=models.Index(
                fields=["establishment", "object_type"],
                name="mama_nice_seed_est_type_idx",
            ),
        ),
    ]
