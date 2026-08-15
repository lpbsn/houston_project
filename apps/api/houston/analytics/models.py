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
ASSIGNMENT_SIGNATURE_MAX_LENGTH = 128
CLASSIFIER_VERSION_MAX_LENGTH = 80
ASSIGNMENT_ERROR_CODE_MAX_LENGTH = 80
ASSIGNMENT_STATUS_NOT_STARTED = "not_started"
ASSIGNMENT_STATUS_PROCESSING = "processing"
ASSIGNMENT_STATUS_SUCCEEDED = "succeeded"
ASSIGNMENT_STATUS_TEMPORARY_FAILED = "temporary_failed"
ASSIGNMENT_STATUS_PERMANENTLY_FAILED = "permanently_failed"
ASSIGNMENT_SOURCE_CLASSIFIER = "classifier"
ASSIGNMENT_SOURCE_OWNER_CORRECTION = "owner_correction"


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
    semantic_label = models.CharField(
        max_length=PATTERN_LABEL_MAX_LENGTH,
        blank=True,
    )
    normalized_semantic_label = models.CharField(
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
            models.Index(
                fields=["organization", "normalized_semantic_label"],
                name="pattern_org_sem_label_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "normalized_label"],
                condition=Q(status=PATTERN_STATUS_ACTIVE),
                name="analytics_pattern_active_label_uniq",
            ),
            models.UniqueConstraint(
                fields=["organization", "normalized_semantic_label"],
                condition=Q(status=PATTERN_STATUS_ACTIVE),
                name="analytics_pattern_active_sem_label_uniq",
            ),
            models.CheckConstraint(
                condition=~Q(normalized_label=""),
                name="analytics_pattern_norm_label_nonempty",
            ),
            models.CheckConstraint(
                condition=~Q(normalized_semantic_label=""),
                name="analytics_pattern_norm_sem_label_nonempty",
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
        if not self.semantic_label:
            self.semantic_label = self.label
        self.normalized_label = normalize_pattern_label(self.label)
        self.normalized_semantic_label = normalize_pattern_label(self.semantic_label)
        errors: dict[str, str] = {}

        if not self.normalized_label:
            errors["label"] = "Pattern label cannot be blank."
        if not self.normalized_semantic_label:
            errors["semantic_label"] = "Pattern semantic label cannot be blank."

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
        if not self.semantic_label:
            self.semantic_label = self.label
        self.normalized_label = normalize_pattern_label(self.label)
        self.normalized_semantic_label = normalize_pattern_label(self.semantic_label)
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and "label" in update_fields:
            kwargs["update_fields"] = {*update_fields, "normalized_label"}
        if update_fields is not None and "semantic_label" in update_fields:
            kwargs["update_fields"] = {*kwargs["update_fields"], "normalized_semantic_label"}
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.label} [{self.status}]"


class PatternLifecycleEvent(BaseModel):
    class EventType(models.TextChoices):
        CREATED = "created", "Created"
        MERGED = "merged", "Merged"
        RENAMED = "renamed", "Renamed"
        RETIRED = "retired", "Retired"
        SPLIT = "split", "Split"
        SIGNALS_MOVED = "signals_moved", "Signals moved"

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


class SignalPatternAssignment(BaseModel):
    class ClassificationStatus(models.TextChoices):
        NOT_STARTED = ASSIGNMENT_STATUS_NOT_STARTED, "Not started"
        PROCESSING = ASSIGNMENT_STATUS_PROCESSING, "Processing"
        SUCCEEDED = ASSIGNMENT_STATUS_SUCCEEDED, "Succeeded"
        TEMPORARY_FAILED = ASSIGNMENT_STATUS_TEMPORARY_FAILED, "Temporary failed"
        PERMANENTLY_FAILED = ASSIGNMENT_STATUS_PERMANENTLY_FAILED, "Permanently failed"

    class AssignmentSource(models.TextChoices):
        CLASSIFIER = ASSIGNMENT_SOURCE_CLASSIFIER, "Classifier"
        OWNER_CORRECTION = ASSIGNMENT_SOURCE_OWNER_CORRECTION, "Owner correction"

    signal = models.OneToOneField(
        "signals.Signal",
        on_delete=models.CASCADE,
        related_name="pattern_assignment",
    )
    pattern = models.ForeignKey(
        OperationalPattern,
        on_delete=models.PROTECT,
        related_name="signal_assignments",
        null=True,
        blank=True,
    )
    classification_status = models.CharField(
        max_length=32,
        choices=ClassificationStatus.choices,
        default=ClassificationStatus.NOT_STARTED,
    )
    assigned_signature = models.CharField(
        max_length=ASSIGNMENT_SIGNATURE_MAX_LENGTH,
        blank=True,
        default="",
    )
    assigned_classifier_version = models.CharField(
        max_length=CLASSIFIER_VERSION_MAX_LENGTH,
        blank=True,
        default="",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    pending_signature = models.CharField(
        max_length=ASSIGNMENT_SIGNATURE_MAX_LENGTH,
        blank=True,
        default="",
    )
    pending_classifier_version = models.CharField(
        max_length=CLASSIFIER_VERSION_MAX_LENGTH,
        blank=True,
        default="",
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    last_error_code = models.CharField(
        max_length=ASSIGNMENT_ERROR_CODE_MAX_LENGTH,
        blank=True,
        default="",
    )
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    assignment_source = models.CharField(
        max_length=32,
        choices=AssignmentSource.choices,
        default=AssignmentSource.CLASSIFIER,
    )
    owner_correction_signature = models.CharField(
        max_length=ASSIGNMENT_SIGNATURE_MAX_LENGTH,
        blank=True,
        default="",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["classification_status", "next_retry_at"],
                name="sig_pat_assign_retry_idx",
            ),
            models.Index(
                fields=["pattern", "classification_status"],
                name="sig_pat_asgn_pattern_st_idx",
            ),
            models.Index(
                fields=["assignment_source"],
                name="sig_pat_assign_source_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    ~Q(classification_status=ASSIGNMENT_STATUS_SUCCEEDED)
                    | Q(pattern__isnull=False)
                ),
                name="sig_pat_assign_succeeded_pattern",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(classification_status=ASSIGNMENT_STATUS_NOT_STARTED)
                    | Q(pattern__isnull=True)
                ),
                name="sig_pat_assign_not_started_null",
            ),
            models.CheckConstraint(
                condition=(
                    Q(pattern__isnull=False)
                    | Q(
                        assigned_signature="",
                        assigned_classifier_version="",
                        assigned_at__isnull=True,
                    )
                ),
                name="sig_pat_assign_null_empty_success",
            ),
            models.CheckConstraint(
                condition=(
                    Q(pattern__isnull=True)
                    | (
                        ~Q(assigned_signature="")
                        & ~Q(assigned_classifier_version="")
                        & Q(assigned_at__isnull=False)
                    )
                ),
                name="sig_pat_assign_pattern_success_meta",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(assignment_source=ASSIGNMENT_SOURCE_CLASSIFIER)
                    | Q(owner_correction_signature="")
                ),
                name="sig_pat_assign_classifier_no_owner",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(assignment_source=ASSIGNMENT_SOURCE_OWNER_CORRECTION)
                    | ~Q(owner_correction_signature="")
                ),
                name="sig_pat_assign_owner_sig_required",
            ),
            models.CheckConstraint(
                condition=(
                    ~Q(assignment_source=ASSIGNMENT_SOURCE_OWNER_CORRECTION)
                    | Q(pattern__isnull=False)
                ),
                name="sig_pat_assign_owner_pattern",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        errors: dict[str, str] = {}

        if (
            self.classification_status == self.ClassificationStatus.SUCCEEDED
            and self.pattern_id is None
        ):
            errors["pattern"] = "Succeeded assignments require a pattern."

        if (
            self.classification_status == self.ClassificationStatus.NOT_STARTED
            and self.pattern_id is not None
        ):
            errors["pattern"] = "Not started assignments cannot have a pattern."

        if self.pattern_id is None:
            if self.assigned_signature:
                errors["assigned_signature"] = (
                    "Assignments without a pattern cannot have an assigned signature."
                )
            if self.assigned_classifier_version:
                errors["assigned_classifier_version"] = (
                    "Assignments without a pattern cannot have an assigned classifier version."
                )
            if self.assigned_at is not None:
                errors["assigned_at"] = (
                    "Assignments without a pattern cannot have an assigned timestamp."
                )
        else:
            if not self.assigned_signature:
                errors["assigned_signature"] = (
                    "Assignments with a pattern require an assigned signature."
                )
            if not self.assigned_classifier_version:
                errors["assigned_classifier_version"] = (
                    "Assignments with a pattern require an assigned classifier version."
                )
            if self.assigned_at is None:
                errors["assigned_at"] = (
                    "Assignments with a pattern require an assigned timestamp."
                )

        if self.pattern_id is not None:
            pattern = self.pattern
            if pattern.status != OperationalPattern.Status.ACTIVE:
                errors["pattern"] = "Assigned pattern must be active."
            elif (
                self.signal_id is not None
                and pattern.organization_id
                != self.signal.establishment.organization_id
            ):
                errors["pattern"] = (
                    "Assigned pattern must belong to the signal organization."
                )

        if self.assignment_source == self.AssignmentSource.CLASSIFIER:
            if self.owner_correction_signature:
                errors["owner_correction_signature"] = (
                    "Classifier assignments cannot have an owner correction signature."
                )
        elif self.assignment_source == self.AssignmentSource.OWNER_CORRECTION:
            if not self.owner_correction_signature:
                errors["owner_correction_signature"] = (
                    "Owner-corrected assignments require an owner correction signature."
                )
            if self.pattern_id is None:
                errors["pattern"] = "Owner-corrected assignments require a pattern."
        else:
            errors["assignment_source"] = "Invalid assignment source."

        if errors:
            raise ValidationError(errors)

    def __str__(self) -> str:
        return f"SignalPatternAssignment {self.signal_id} [{self.classification_status}]"
