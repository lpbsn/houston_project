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


class OperationalDomain(BaseModel):
    class Source(models.TextChoices):
        AI_PROPOSED = "ai_proposed", "AI Proposed"
        MANUAL = "manual", "Manual"
        TEMPLATE = "template", "Template"

    establishment = models.ForeignKey(
        Establishment,
        on_delete=models.CASCADE,
        related_name="operational_domains",
        db_index=False,
    )
    key = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["establishment", "key"],
                name="op_domain_est_key_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["establishment"], name="domain_est_idx"),
            models.Index(fields=["establishment", "active"], name="domain_est_active_idx"),
            models.Index(fields=["key"], name="domain_key_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.establishment} :: {self.label} [{self.key}]"


class MembershipDomain(BaseModel):
    membership = models.ForeignKey(
        EstablishmentMembership,
        on_delete=models.CASCADE,
        related_name="domain_links",
        db_index=False,
    )
    operational_domain = models.ForeignKey(
        OperationalDomain,
        on_delete=models.CASCADE,
        related_name="membership_links",
        db_index=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "operational_domain"],
                name="membership_domain_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["membership"], name="mship_domain_mship_idx"),
            models.Index(fields=["operational_domain"], name="mship_domain_domain_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.membership} -> {self.operational_domain.key}"
