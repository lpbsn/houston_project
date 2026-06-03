from __future__ import annotations

from django.db import models

from houston.core.models import BaseModel
from houston.observations.constants import OBSERVATION_RAW_TEXT_MAX_LENGTH


class Observation(BaseModel):
    class Origin(models.TextChoices):
        DIRECT_REPORT = "direct_report", "Direct report"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="observations",
    )
    submitted_by_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="submitted_observations",
    )
    raw_text = models.TextField(max_length=OBSERVATION_RAW_TEXT_MAX_LENGTH)
    origin = models.CharField(
        max_length=40,
        choices=Origin.choices,
        default=Origin.DIRECT_REPORT,
    )
    submitted_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(
                fields=["establishment", "submitted_at"],
                name="observation_est_submitted_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Observation {self.id}"


class ObservationMedia(BaseModel):
    observation = models.ForeignKey(
        Observation,
        on_delete=models.CASCADE,
        related_name="media_items",
    )
    temporary_upload = models.OneToOneField(
        "uploads.TemporaryUpload",
        on_delete=models.PROTECT,
        related_name="observation_media",
    )
    position = models.PositiveSmallIntegerField()
    content_type = models.CharField(max_length=120)
    size_bytes = models.PositiveIntegerField()
    storage_key = models.CharField(max_length=512)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["observation", "position"],
                name="observation_media_unique_position",
            ),
        ]
        indexes = [
            models.Index(fields=["observation"], name="observation_media_obs_idx"),
        ]

    def __str__(self) -> str:
        return f"ObservationMedia {self.id} pos={self.position}"


class ObservationProcessing(BaseModel):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        RETRYING = "retrying", "Retrying"
        FAILED = "failed", "Failed"

    observation = models.OneToOneField(
        Observation,
        on_delete=models.CASCADE,
        related_name="processing",
    )

    class Outcome(models.TextChoices):
        SIGNALS_CREATED = "signals_created", "Signals created"
        SIGNAL_AGGREGATED = "signal_aggregated", "Signal aggregated"
        NO_SIGNAL_CREATED = "no_signal_created", "No signal created"
        NOT_ACTIONABLE = "not_actionable", "Not actionable"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    queued_at = models.DateTimeField()
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    outcome = models.CharField(
        max_length=32,
        choices=Outcome.choices,
        blank=True,
        default="",
    )
    last_error_code = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["status", "queued_at"], name="obs_processing_status_idx"),
        ]

    def __str__(self) -> str:
        return f"ObservationProcessing {self.observation_id} [{self.status}]"
