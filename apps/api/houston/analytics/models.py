from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from houston.analytics.labels import normalize_pattern_label
from houston.core.models import BaseModel

PATTERN_LABEL_MAX_LENGTH = 255
PATTERN_EVENT_TYPE_MAX_LENGTH = 64
PATTERN_REPORT_TYPE_MAX_LENGTH = 64
PATTERN_ISSUE_COMMENT_MAX_LENGTH = 500
PATTERN_STATUS_ACTIVE = "active"
PATTERN_STATUS_MERGED = "merged"
PATTERN_STATUS_RETIRED = "retired"


class OperationalPattern(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = PATTERN_STATUS_ACTIVE, "Active"
        MERGED = PATTERN_STATUS_MERGED, "Merged"
        RETIRED = PATTERN_STATUS_RETIRED, "Retired"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="operational_patterns",
    )
    label = models.CharField(max_length=PATTERN_LABEL_MAX_LENGTH)
    normalized_label = models.CharField(
        max_length=PATTERN_LABEL_MAX_LENGTH,
        editable=False,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    merged_into = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="merged_patterns",
        null=True,
        blank=True,
    )
    created_by_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.SET_NULL,
        related_name="created_operational_patterns",
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["organization", "status"], name="pattern_org_status_idx"),
            models.Index(
                fields=["organization", "normalized_label"],
                name="pattern_org_label_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "normalized_label"],
                condition=Q(status=PATTERN_STATUS_ACTIVE),
                name="analytics_pattern_active_label_uniq",
            ),
            models.CheckConstraint(
                condition=~Q(normalized_label=""),
                name="analytics_pattern_norm_label_nonempty",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status=PATTERN_STATUS_MERGED, merged_into__isnull=False)
                    | Q(
                        status__in=[PATTERN_STATUS_ACTIVE, PATTERN_STATUS_RETIRED],
                        merged_into__isnull=True,
                    )
                ),
                name="analytics_pattern_merge_target_state",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        self.normalized_label = normalize_pattern_label(self.label)
        errors: dict[str, str] = {}

        if not self.normalized_label:
            errors["label"] = "Pattern label cannot be blank."

        if self.status == self.Status.MERGED:
            if self.merged_into_id is None:
                errors["merged_into"] = "Merged patterns require a target pattern."
            elif self.pk is not None and self.merged_into_id == self.pk:
                errors["merged_into"] = "A pattern cannot be merged into itself."
            else:
                target = self.merged_into
                if target.organization_id != self.organization_id:
                    errors["merged_into"] = (
                        "Merged target must belong to the same organization."
                    )
                elif target.status != self.Status.ACTIVE:
                    errors["merged_into"] = "Merged target must be active."
        elif self.merged_into_id is not None:
            errors["merged_into"] = "Only merged patterns can have a target pattern."

        if (
            self.created_by_membership_id is not None
            and self.created_by_membership.establishment.organization_id
            != self.organization_id
        ):
            errors["created_by_membership"] = (
                "Creator membership must belong to the same organization."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.normalized_label = normalize_pattern_label(self.label)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "label" in update_fields:
            kwargs["update_fields"] = {*update_fields, "normalized_label"}
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.label} [{self.status}]"


class PatternLifecycleEvent(BaseModel):
    class EventType(models.TextChoices):
        CREATED = "created", "Created"
        MERGED = "merged", "Merged"
        RETIRED = "retired", "Retired"

    pattern = models.ForeignKey(
        OperationalPattern,
        on_delete=models.CASCADE,
        related_name="lifecycle_events",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="pattern_lifecycle_events",
    )
    event_type = models.CharField(
        max_length=PATTERN_EVENT_TYPE_MAX_LENGTH,
        choices=EventType.choices,
    )
    actor_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.SET_NULL,
        related_name="pattern_lifecycle_events",
        null=True,
        blank=True,
    )
    occurred_at = models.DateTimeField()
    metadata_safe = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["pattern", "occurred_at"], name="pattern_event_at_idx"),
            models.Index(fields=["organization", "occurred_at"], name="pattern_org_at_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}

        if (
            self.pattern_id is not None
            and self.organization_id is not None
            and self.pattern.organization_id != self.organization_id
        ):
            errors["organization"] = "Organization must match the pattern organization."

        if (
            self.actor_membership_id is not None
            and self.organization_id is not None
            and self.actor_membership.establishment.organization_id
            != self.organization_id
        ):
            errors["actor_membership"] = (
                "Actor membership must belong to the same organization."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"PatternLifecycleEvent {self.event_type} ({self.pattern_id})"


class PatternIssueReport(BaseModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REVIEWED = "reviewed", "Reviewed"

    pattern = models.ForeignKey(
        OperationalPattern,
        on_delete=models.CASCADE,
        related_name="issue_reports",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="pattern_issue_reports",
    )
    signal = models.ForeignKey(
        "signals.Signal",
        on_delete=models.SET_NULL,
        related_name="pattern_issue_reports",
        null=True,
        blank=True,
    )
    reported_by_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="pattern_issue_reports_submitted",
    )
    report_type = models.CharField(max_length=PATTERN_REPORT_TYPE_MAX_LENGTH)
    comment = models.TextField(
        max_length=PATTERN_ISSUE_COMMENT_MAX_LENGTH,
        blank=True,
        default="",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    class Meta:
        indexes = [
            models.Index(fields=["pattern", "status"], name="pattern_report_status_idx"),
            models.Index(
                fields=["organization", "status"],
                name="pattern_org_report_status_idx",
            ),
            models.Index(fields=["signal"], name="pattern_report_signal_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}

        if (
            self.pattern_id is not None
            and self.organization_id is not None
            and self.pattern.organization_id != self.organization_id
        ):
            errors["organization"] = "Organization must match the pattern organization."

        if (
            self.reported_by_membership_id is not None
            and self.organization_id is not None
            and self.reported_by_membership.establishment.organization_id
            != self.organization_id
        ):
            errors["reported_by_membership"] = (
                "Reporter membership must belong to the same organization."
            )

        if (
            self.signal_id is not None
            and self.organization_id is not None
            and self.signal.establishment.organization_id != self.organization_id
        ):
            errors["signal"] = "Signal must belong to the same organization."

        if not (self.report_type or "").strip():
            errors["report_type"] = "Report type is required."

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"PatternIssueReport {self.id} [{self.status}]"
