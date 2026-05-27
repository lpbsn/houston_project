from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from houston.core.models import BaseModel


class User(AbstractUser):
    class IdentityType(models.TextChoices):
        EMAIL = "email", "Email"
        USERNAME = "username", "Username"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        ANONYMIZED = "anonymized", "Anonymized"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(blank=True, null=True)
    identity_type = models.CharField(
        max_length=20,
        choices=IdentityType.choices,
        default=IdentityType.EMAIL,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                condition=Q(email__isnull=False),
                name="accounts_user_email_ci_uniq",
            )
        ]

    @staticmethod
    def normalize_email_value(email: str | None) -> str | None:
        if email is None:
            return None

        normalized_email = email.strip().lower()
        return normalized_email or None

    def save(self, *args, **kwargs):
        self.email = self.normalize_email_value(self.email)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.get_username()


class UserSession(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="sessions",
        db_index=False,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    refresh_token_family_id = models.UUIDField(db_index=True)
    user_agent = models.TextField(blank=True)
    ip_metadata = models.GenericIPAddressField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    refresh_expires_at = models.DateTimeField()
    absolute_expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"], name="user_session_user_status_idx"),
        ]


class AccessToken(BaseModel):
    session = models.ForeignKey(
        UserSession,
        on_delete=models.CASCADE,
        related_name="access_tokens",
        db_index=False,
    )
    token_digest = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["session"], name="access_token_session_idx"),
        ]


class SessionRefreshToken(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        USED = "used", "Used"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    session = models.ForeignKey(
        UserSession,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
        db_index=False,
    )
    family_id = models.UUIDField(db_index=True)
    token_digest = models.CharField(max_length=64, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["session"], name="refresh_token_session_idx"),
        ]
