from __future__ import annotations

from django.db import models

from houston.core.models import BaseModel
from houston.signals.constants import (
    SIGNAL_LOCATION_TEXT_MAX_LENGTH,
    SIGNAL_STRUCTURED_SUMMARY_MAX_LENGTH,
    SIGNAL_TITLE_MAX_LENGTH,
)


class Signal(BaseModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        CANCELED = "canceled", "Canceled"
        ARCHIVED = "archived", "Archived"

    class Urgency(models.TextChoices):
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="signals",
    )
    operational_module = models.ForeignKey(
        "establishments.OperationalModule",
        on_delete=models.PROTECT,
        related_name="signals",
    )
    operational_domain = models.ForeignKey(
        "establishments.OperationalDomain",
        on_delete=models.PROTECT,
        related_name="signals",
    )
    operational_subject = models.ForeignKey(
        "establishments.OperationalSubject",
        on_delete=models.PROTECT,
        related_name="signals",
    )
    affected_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="affected_signals",
        null=True,
        blank=True,
    )
    responsible_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="responsible_signals",
        null=True,
        blank=True,
    )
    activity_subject = models.ForeignKey(
        "establishments.ActivitySubject",
        on_delete=models.PROTECT,
        related_name="signals",
        null=True,
        blank=True,
    )
    operational_unit = models.ForeignKey(
        "establishments.OperationalUnit",
        on_delete=models.PROTECT,
        related_name="signals",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    urgency = models.CharField(
        max_length=20,
        choices=Urgency.choices,
        default=Urgency.NORMAL,
    )
    is_pinned = models.BooleanField(default=False)
    pinned_at = models.DateTimeField(null=True, blank=True)
    pinned_by_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.SET_NULL,
        related_name="pinned_signals",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=SIGNAL_TITLE_MAX_LENGTH)
    structured_summary = models.TextField(max_length=SIGNAL_STRUCTURED_SUMMARY_MAX_LENGTH)
    location_text = models.CharField(
        max_length=SIGNAL_LOCATION_TEXT_MAX_LENGTH,
        blank=True,
        default="",
    )
    last_activity_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "establishment",
                    "status",
                    "is_pinned",
                    "urgency",
                    "last_activity_at",
                ],
                name="signal_feed_sort_idx",
            ),
            models.Index(
                fields=["establishment", "operational_subject"],
                name="signal_est_subject_idx",
            ),
            models.Index(
                fields=["establishment", "affected_business_unit"],
                name="signal_est_affected_bu_idx",
            ),
            models.Index(
                fields=["establishment", "responsible_business_unit"],
                name="signal_est_responsible_bu_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Signal {self.id} [{self.status}]"


class CandidateSignal(BaseModel):
    class Outcome(models.TextChoices):
        PENDING = "pending", "Pending"
        CREATED_SIGNAL = "created_signal", "Created signal"
        AGGREGATED_SIGNAL = "aggregated_signal", "Aggregated signal"
        REJECTED = "rejected", "Rejected"
        NO_SIGNAL_CREATED = "no_signal_created", "No signal created"

    observation = models.ForeignKey(
        "observations.Observation",
        on_delete=models.CASCADE,
        related_name="candidate_signals",
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="candidate_signals",
    )
    operational_module = models.ForeignKey(
        "establishments.OperationalModule",
        on_delete=models.PROTECT,
        related_name="candidate_signals",
        null=True,
        blank=True,
    )
    operational_domain = models.ForeignKey(
        "establishments.OperationalDomain",
        on_delete=models.PROTECT,
        related_name="candidate_signals",
        null=True,
        blank=True,
    )
    operational_subject = models.ForeignKey(
        "establishments.OperationalSubject",
        on_delete=models.PROTECT,
        related_name="candidate_signals",
        null=True,
        blank=True,
    )
    affected_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="affected_candidate_signals",
        null=True,
        blank=True,
    )
    responsible_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="responsible_candidate_signals",
        null=True,
        blank=True,
    )
    activity_subject = models.ForeignKey(
        "establishments.ActivitySubject",
        on_delete=models.PROTECT,
        related_name="candidate_signals",
        null=True,
        blank=True,
    )
    location_text = models.CharField(
        max_length=SIGNAL_LOCATION_TEXT_MAX_LENGTH,
        blank=True,
        default="",
    )
    operational_unit = models.ForeignKey(
        "establishments.OperationalUnit",
        on_delete=models.PROTECT,
        related_name="candidate_signals",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=SIGNAL_TITLE_MAX_LENGTH, blank=True, default="")
    structured_summary = models.TextField(
        max_length=SIGNAL_STRUCTURED_SUMMARY_MAX_LENGTH,
        blank=True,
        default="",
    )
    schema_version = models.CharField(max_length=80, blank=True, default="")
    ai_aggregate_hint_signal_id = models.UUIDField(null=True, blank=True)
    outcome = models.CharField(
        max_length=32,
        choices=Outcome.choices,
        default=Outcome.PENDING,
    )
    result_signal = models.ForeignKey(
        Signal,
        on_delete=models.SET_NULL,
        related_name="source_candidates",
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["observation", "outcome"],
                name="cand_signal_obs_outcome_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"CandidateSignal {self.id} [{self.outcome}]"


class SignalSourceObservation(BaseModel):
    class LinkType(models.TextChoices):
        CREATED_FROM = "created_from", "Created from"
        AGGREGATED_FROM = "aggregated_from", "Aggregated from"

    signal = models.ForeignKey(
        Signal,
        on_delete=models.CASCADE,
        related_name="source_observation_links",
    )
    observation = models.ForeignKey(
        "observations.Observation",
        on_delete=models.CASCADE,
        related_name="linked_signals",
    )
    link_type = models.CharField(max_length=32, choices=LinkType.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["signal", "observation", "link_type"],
                name="signal_source_obs_unique_link",
            ),
        ]
        indexes = [
            models.Index(fields=["signal"], name="signal_src_obs_signal_idx"),
            models.Index(fields=["observation"], name="signal_src_obs_obs_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.signal_id} <- {self.observation_id} ({self.link_type})"
