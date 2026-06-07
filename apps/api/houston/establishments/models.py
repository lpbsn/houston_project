from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from houston.core.models import BaseModel
from houston.organizations.models import Organization

ACTIVITY_DESCRIPTION_MIN_LENGTH = 50
ONBOARDING_TERMINAL_STATUSES = (
    "activated",
    "failed",
    "canceled",
)
ONBOARDING_NON_TERMINAL_STATUSES = (
    "started",
    "description_submitted",
    "configuring_runtime",
    "proposal_ready",
    "validating_sections",
    "ready_for_activation",
)
ONBOARDING_PROPOSAL_NON_TERMINAL_STATUSES = (
    "draft",
    "ready",
    "partially_validated",
    "validated",
)


def _validate_nonblank(value: str, field_name: str, errors: dict[str, str]) -> None:
    if not isinstance(value, str) or not value.strip():
        errors[field_name] = "This field cannot be blank."


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


class OnboardingCatalogUnit(BaseModel):
    key = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["active"], name="onbrd_cat_unit_active_idx"),
            models.Index(
                fields=["active", "sort_order", "key"],
                name="onbrd_cat_unit_order_idx",
            ),
        ]
        ordering = ["sort_order", "key"]

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        _validate_nonblank(self.key, "key", errors)
        _validate_nonblank(self.label, "label", errors)
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.label} [{self.key}]"


class OnboardingSession(BaseModel):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        DESCRIPTION_SUBMITTED = "description_submitted", "Description submitted"
        CONFIGURING_RUNTIME = "configuring_runtime", "Configuring runtime"
        PROPOSAL_READY = "proposal_ready", "Proposal ready"
        VALIDATING_SECTIONS = "validating_sections", "Validating sections"
        READY_FOR_ACTIVATION = "ready_for_activation", "Ready for activation"
        ACTIVATED = "activated", "Activated"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    class SourceMode(models.TextChoices):
        MANUAL = "manual", "Manual"
        TEMPLATE = "template", "Template"
        AI = "ai", "AI"

    TERMINAL_STATUSES = ONBOARDING_TERMINAL_STATUSES
    NON_TERMINAL_STATUSES = ONBOARDING_NON_TERMINAL_STATUSES

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="onboarding_sessions",
        db_index=False,
    )
    establishment = models.ForeignKey(
        Establishment,
        on_delete=models.CASCADE,
        related_name="onboarding_sessions",
        db_index=False,
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="started_onboarding_sessions",
        null=True,
        blank=True,
        db_index=False,
    )
    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.STARTED,
    )
    source_mode = models.CharField(
        max_length=20,
        choices=SourceMode.choices,
        default=SourceMode.MANUAL,
    )
    current_step = models.CharField(max_length=80, blank=True, default="")
    ai_attempts = models.PositiveSmallIntegerField(default=0)
    last_error_code = models.CharField(max_length=80, blank=True, default="")
    started_at = models.DateTimeField(default=timezone.now)
    ready_for_activation_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["establishment"],
                condition=Q(status__in=ONBOARDING_NON_TERMINAL_STATUSES),
                name="onboarding_session_est_nonterminal_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["establishment"], name="onbrd_session_est_idx"),
            models.Index(fields=["organization"], name="onbrd_session_org_idx"),
            models.Index(fields=["started_by"], name="onbrd_session_started_idx"),
            models.Index(fields=["status"], name="onbrd_session_status_idx"),
            models.Index(
                fields=["establishment", "status"],
                name="onbrd_session_est_status_idx",
            ),
        ]

    @classmethod
    def is_terminal_status(cls, status: str) -> bool:
        return status in cls.TERMINAL_STATUSES

    @classmethod
    def is_non_terminal_status(cls, status: str) -> bool:
        return status in cls.NON_TERMINAL_STATUSES

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}

        if (
            self.organization_id is not None
            and self.establishment_id is not None
            and self.establishment.organization_id != self.organization_id
        ):
            errors["organization"] = "Organization must match the establishment organization."

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.establishment} onboarding [{self.status}]"


class OnboardingProposal(BaseModel):
    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        TEMPLATE = "template", "Template"
        AI_PROPOSED = "ai_proposed", "AI Proposed"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        PARTIALLY_VALIDATED = "partially_validated", "Partially validated"
        VALIDATED = "validated", "Validated"
        APPLIED = "applied", "Applied"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    NON_TERMINAL_STATUSES = ONBOARDING_PROPOSAL_NON_TERMINAL_STATUSES

    onboarding_session = models.ForeignKey(
        OnboardingSession,
        on_delete=models.CASCADE,
        related_name="proposals",
        db_index=False,
    )
    establishment = models.ForeignKey(
        Establishment,
        on_delete=models.CASCADE,
        related_name="onboarding_proposals",
        db_index=False,
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    payload = models.JSONField(default=dict, blank=True)
    section_validation = models.JSONField(default=dict, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_onboarding_proposals",
        null=True,
        blank=True,
        db_index=False,
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="validated_onboarding_proposals",
        null=True,
        blank=True,
        db_index=False,
    )
    applied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="applied_onboarding_proposals",
        null=True,
        blank=True,
        db_index=False,
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["onboarding_session"],
                condition=Q(status__in=ONBOARDING_PROPOSAL_NON_TERMINAL_STATUSES),
                name="onbrd_prop_session_open_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["onboarding_session"], name="onbrd_prop_session_idx"),
            models.Index(fields=["establishment"], name="onbrd_prop_est_idx"),
            models.Index(fields=["status"], name="onbrd_prop_status_idx"),
            models.Index(fields=["source"], name="onbrd_prop_source_idx"),
            models.Index(fields=["created_by"], name="onbrd_prop_created_idx"),
            models.Index(fields=["validated_by"], name="onbrd_prop_validated_idx"),
            models.Index(fields=["applied_at"], name="onbrd_prop_applied_idx"),
            models.Index(
                fields=["onboarding_session", "status"],
                name="onbrd_prop_sess_status_idx",
            ),
            models.Index(
                fields=["establishment", "status"],
                name="onbrd_prop_est_status_idx",
            ),
        ]

    @classmethod
    def is_non_terminal_status(cls, status: str) -> bool:
        return status in cls.NON_TERMINAL_STATUSES

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}

        if (
            self.onboarding_session_id is not None
            and self.establishment_id is not None
            and self.onboarding_session.establishment_id != self.establishment_id
        ):
            errors["establishment"] = (
                "Establishment must match the onboarding session establishment."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.establishment} proposal [{self.status}]"


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
            ),
            models.UniqueConstraint(
                fields=["establishment"],
                condition=Q(
                    role="director",
                    status__in=["invited", "active"],
                ),
                name="unique_active_or_invited_director_per_establishment",
            ),
        ]
        indexes = [
            models.Index(fields=["establishment"], name="membership_est_idx"),
            models.Index(fields=["user"], name="membership_user_idx"),
            models.Index(fields=["role"], name="membership_role_idx"),
            models.Index(fields=["status"], name="membership_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user} @ {self.establishment}"


class EstablishmentInvitation(BaseModel):
    membership = models.ForeignKey(
        EstablishmentMembership,
        on_delete=models.CASCADE,
        related_name="invitations",
        db_index=False,
    )
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["membership"], name="est_invitation_membership_idx"),
            models.Index(fields=["expires_at"], name="est_invitation_expires_idx"),
        ]

    def __str__(self) -> str:
        return f"Invitation for {self.membership_id}"


class MembershipScope(BaseModel):
    """Operational RBAC scope for manager/staff memberships (BusinessUnit only)."""

    membership = models.ForeignKey(
        EstablishmentMembership,
        on_delete=models.CASCADE,
        related_name="scope_links",
        db_index=False,
    )
    business_unit = models.ForeignKey(
        "BusinessUnit",
        on_delete=models.CASCADE,
        related_name="membership_scopes",
        db_index=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["membership", "business_unit"],
                name="membership_scope_business_unit_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["membership"], name="mship_scope_mship_idx"),
            models.Index(fields=["business_unit"], name="mship_scope_bu_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        if self.business_unit_id is None:
            raise ValidationError({"business_unit": "Business unit scope is required."})

    @property
    def scope_type(self) -> str:
        return "business_unit"

    @property
    def scope_id(self):
        return self.business_unit_id

    def __str__(self) -> str:
        return f"{self.membership} -> {self.scope_type}:{self.scope_id}"


class EstablishmentActivityDescription(BaseModel):
    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"

    establishment = models.OneToOneField(
        Establishment,
        on_delete=models.CASCADE,
        related_name="activity_description",
    )
    description = models.TextField()
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="submitted_activity_descriptions",
        null=True,
        blank=True,
        db_index=False,
    )
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["submitted_by"], name="activity_desc_submitter_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        if len((self.description or "").strip()) < ACTIVITY_DESCRIPTION_MIN_LENGTH:
            raise ValidationError(
                {
                    "description": (
                        "Activity description must be at least "
                        f"{ACTIVITY_DESCRIPTION_MIN_LENGTH} characters."
                    )
                }
            )

    def __str__(self) -> str:
        return f"{self.establishment} activity description"


class OperationalUnit(BaseModel):
    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        TEMPLATE = "template", "Template"
        AI_PROPOSED = "ai_proposed", "AI Proposed"

    establishment = models.ForeignKey(
        Establishment,
        on_delete=models.CASCADE,
        related_name="operational_units",
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
    managed_by_onboarding_proposal = models.ForeignKey(
        OnboardingProposal,
        on_delete=models.SET_NULL,
        related_name="managed_operational_units",
        null=True,
        blank=True,
        db_index=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["establishment", "key"],
                name="op_unit_est_key_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["establishment"], name="unit_est_idx"),
            models.Index(fields=["establishment", "active"], name="unit_est_active_idx"),
            models.Index(fields=["key"], name="unit_key_idx"),
            models.Index(
                fields=["managed_by_onboarding_proposal"],
                name="unit_managed_prop_idx",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}
        _validate_nonblank(self.key, "key", errors)
        _validate_nonblank(self.label, "label", errors)
        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"{self.establishment} :: {self.label} [{self.key}]"


class CatalogBusinessUnit(BaseModel):
    class DefaultUnitType(models.TextChoices):
        DEDICATED = "dedicated", "Dedicated"
        TRANSVERSAL = "transversal", "Transversal"

    key = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    default_unit_type = models.CharField(
        max_length=20,
        choices=DefaultUnitType.choices,
        default=DefaultUnitType.DEDICATED,
    )
    active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "key"]
        indexes = [
            models.Index(fields=["active"], name="cat_bu_active_idx"),
            models.Index(
                fields=["active", "sort_order", "key"],
                name="cat_bu_order_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.label} [{self.key}]"


class CatalogActivitySubject(BaseModel):
    catalog_business_unit = models.ForeignKey(
        CatalogBusinessUnit,
        on_delete=models.SET_NULL,
        related_name="catalog_activity_subjects",
        null=True,
        blank=True,
    )
    key = models.CharField(max_length=150, unique=True)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "key"]
        indexes = [
            models.Index(fields=["active"], name="cat_as_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.label} [{self.key}]"


class BusinessUnit(BaseModel):
    class UnitType(models.TextChoices):
        DEDICATED = "dedicated", "Dedicated"
        TRANSVERSAL = "transversal", "Transversal"

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        CATALOG_SUGGESTION = "catalog_suggestion", "Catalog suggestion"
        MIGRATED = "migrated", "Migrated"
        TEMPLATE = "template", "Template"

    establishment = models.ForeignKey(
        Establishment,
        on_delete=models.CASCADE,
        related_name="business_units",
        db_index=False,
    )
    key = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    unit_type = models.CharField(
        max_length=20,
        choices=UnitType.choices,
        default=UnitType.DEDICATED,
    )
    catalog_business_unit = models.ForeignKey(
        CatalogBusinessUnit,
        on_delete=models.SET_NULL,
        related_name="establishment_business_units",
        null=True,
        blank=True,
        db_index=False,
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    active = models.BooleanField(default=True)
    managed_by_onboarding_proposal = models.ForeignKey(
        OnboardingProposal,
        on_delete=models.SET_NULL,
        related_name="managed_business_units",
        null=True,
        blank=True,
        db_index=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["establishment", "key"],
                name="bu_est_key_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["establishment"], name="bu_est_idx"),
            models.Index(fields=["establishment", "active"], name="bu_est_active_idx"),
            models.Index(fields=["establishment", "unit_type"], name="bu_est_type_idx"),
            models.Index(fields=["key"], name="bu_key_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.establishment} :: {self.label} [{self.key}]"


class ActivitySubject(BaseModel):
    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        CATALOG_SUGGESTION = "catalog_suggestion", "Catalog suggestion"
        MIGRATED = "migrated", "Migrated"
        TEMPLATE = "template", "Template"

    establishment = models.ForeignKey(
        Establishment,
        on_delete=models.CASCADE,
        related_name="activity_subjects",
        db_index=False,
    )
    business_unit = models.ForeignKey(
        BusinessUnit,
        on_delete=models.CASCADE,
        related_name="activity_subjects",
        db_index=False,
    )
    normalized_name = models.CharField(max_length=150)
    label = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    catalog_activity_subject = models.ForeignKey(
        CatalogActivitySubject,
        on_delete=models.SET_NULL,
        related_name="establishment_activity_subjects",
        null=True,
        blank=True,
        db_index=False,
    )
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.MANUAL,
    )
    active = models.BooleanField(default=True)
    managed_by_onboarding_proposal = models.ForeignKey(
        OnboardingProposal,
        on_delete=models.SET_NULL,
        related_name="managed_activity_subjects",
        null=True,
        blank=True,
        db_index=False,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["business_unit", "normalized_name"],
                name="as_bu_normalized_name_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["business_unit", "active"], name="as_bu_active_idx"),
            models.Index(fields=["establishment", "active"], name="as_est_active_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        if (
            self.business_unit_id is not None
            and self.establishment_id is not None
            and self.business_unit.establishment_id != self.establishment_id
        ):
            raise ValidationError(
                {"business_unit": "Business unit must belong to the same establishment."}
            )

    def __str__(self) -> str:
        return f"{self.business_unit.key} :: {self.label} [{self.normalized_name}]"



