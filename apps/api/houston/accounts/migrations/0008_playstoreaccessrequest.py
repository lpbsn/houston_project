import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_passwordresetrequest"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlayStoreAccessRequest",
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
                ("google_play_email", models.EmailField(max_length=254)),
                ("idempotency_key", models.UUIDField(unique=True)),
                ("idempotency_key_created_at", models.DateTimeField()),
                ("mail_to", models.CharField(max_length=254)),
                ("mail_from", models.CharField(max_length=255)),
                ("mail_subject", models.CharField(max_length=255)),
                ("mail_html", models.TextField()),
                ("mail_text", models.TextField()),
                ("provider_accepted_at", models.DateTimeField(blank=True, null=True)),
                ("is_address_correction", models.BooleanField(default=False)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="play_store_access_request",
                        to="accounts.user",
                    ),
                ),
            ],
        ),
    ]
