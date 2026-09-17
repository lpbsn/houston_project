from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_emailchangerequest"),
    ]

    operations = [
        migrations.CreateModel(
            name="PasswordResetRequest",
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
                ("email_at_issue", models.EmailField(max_length=254)),
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
                        related_name="password_reset_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user"], name="password_reset_user_idx"),
                    models.Index(fields=["expires_at"], name="password_reset_expires_idx"),
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="passwordresetrequest",
            constraint=models.UniqueConstraint(
                condition=models.Q(
                    ("revoked_at__isnull", True),
                    ("consumed_at__isnull", True),
                ),
                fields=("user",),
                name="accounts_password_reset_one_live",
            ),
        ),
    ]
