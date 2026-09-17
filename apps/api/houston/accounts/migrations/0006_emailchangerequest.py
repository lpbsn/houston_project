from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_user_ai_declined_version"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailChangeRequest",
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
                ("new_email", models.EmailField(max_length=254)),
                (
                    "token_digest",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        db_index=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_change_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user"], name="email_change_user_idx"),
                    models.Index(fields=["expires_at"], name="email_change_expires_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="emailchangerequest",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("consumed_at__isnull", True),
                    ("revoked_at__isnull", True),
                ),
                fields=("user",),
                name="accounts_email_change_one_live",
            ),
        ),
    ]
