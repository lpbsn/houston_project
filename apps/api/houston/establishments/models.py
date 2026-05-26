from __future__ import annotations

from django.conf import settings
from django.db import models

from houston.core.models import BaseModel
from houston.organizations.models import Organization


class Establishment(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        DEACTIVATED = "deactivated", "Deactivated"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="establishments",
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    def __str__(self) -> str:
        return self.name


class EstablishmentMembership(BaseModel):
    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        DIRECTOR = "director", "Director"
        MANAGER = "manager", "Manager"
        STAFF = "staff", "Staff"

    class Status(models.TextChoices):
        INVITED = "invited", "Invited"
        ACTIVE = "active", "Active"
        DEACTIVATED = "deactivated", "Deactivated"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="establishment_memberships",
        db_index=False,
    )
    establishment = models.ForeignKey(
        Establishment,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=False,
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INVITED,
    )
    operational_domains = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "establishment"],
                name="unique_user_establishment_membership",
            )
        ]
        indexes = [
            models.Index(fields=["establishment"], name="membership_est_idx"),
            models.Index(fields=["user"], name="membership_user_idx"),
            models.Index(fields=["role"], name="membership_role_idx"),
            models.Index(fields=["status"], name="membership_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.establishment}"
