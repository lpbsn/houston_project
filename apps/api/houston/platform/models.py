from __future__ import annotations

from django.conf import settings
from django.db import models

from houston.core.models import BaseModel


class PlatformOperatorAccess(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="platform_operator_access",
    )
    is_active = models.BooleanField(default=True)
    granted_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"platform-operator:{self.user_id}:{'active' if self.is_active else 'revoked'}"


class PlatformLifecycleEvent(BaseModel):
    class Result(models.TextChoices):
        OK = "ok", "Ok"
        DENIED = "denied", "Denied"
        FAILED = "failed", "Failed"

    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="platform_lifecycle_events",
    )
    action = models.CharField(max_length=64)
    resource_type = models.CharField(max_length=64)
    resource_id = models.UUIDField(null=True, blank=True)
    justification = models.TextField(blank=True, default="")
    result = models.CharField(max_length=16, choices=Result.choices)
    error_code = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]
