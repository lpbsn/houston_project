import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0017_action_plan_execution_done_validated_event_keys"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.DeleteModel(name="PushDelivery"),
        migrations.DeleteModel(name="WebPushSubscription"),
        migrations.CreateModel(
            name="PushDevice",
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
                ("token", models.CharField(max_length=512)),
                (
                    "platform",
                    models.CharField(
                        choices=[("ios", "iOS"), ("android", "Android")],
                        max_length=16,
                    ),
                ),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="push_devices",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PushDelivery",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("processing", "Processing"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                            ("skipped", "Skipped"),
                        ],
                        default="queued",
                        max_length=16,
                    ),
                ),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("error_code", models.CharField(blank=True, default="", max_length=64)),
                (
                    "notification",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="push_deliveries",
                        to="notifications.notification",
                    ),
                ),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="push_deliveries",
                        to="notifications.pushdevice",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="pushdevice",
            constraint=models.UniqueConstraint(
                condition=models.Q(("revoked_at__isnull", True)),
                fields=("token",),
                name="notifications_pushdevice_active_token_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="pushdevice",
            index=models.Index(
                fields=["user", "revoked_at"],
                name="notificatio_user_id_2945d5_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="pushdelivery",
            constraint=models.UniqueConstraint(
                fields=("notification", "device"),
                name="notifications_pushdelivery_notification_device_uniq",
            ),
        ),
    ]
