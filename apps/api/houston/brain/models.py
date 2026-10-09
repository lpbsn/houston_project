from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from houston.core.models import BaseModel


class BrainReporting(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        REJECTED = "rejected", "Rejected"

    class SourceFormat(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="brain_reportings",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authored_brain_reportings",
    )
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    source_format = models.CharField(max_length=16, choices=SourceFormat.choices)
    content_sha256 = models.CharField(max_length=64)
    storage_key = models.CharField(max_length=512)
    byte_size = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    rejection_code = models.CharField(max_length=80, blank=True, default="")
    rejection_message = models.TextField(blank=True, default="")
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    period_confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    period_confirmed_at__isnull=True,
                    period_start__isnull=True,
                    period_end__isnull=True,
                )
                | (
                    Q(
                        period_confirmed_at__isnull=False,
                        period_start__isnull=False,
                        period_end__isnull=False,
                    )
                    & Q(period_end__gte=F("period_start"))
                ),
                name="brain_rep_period_chk",
            ),
        ]
        indexes = [
            models.Index(
                fields=["establishment", "status", "created_at"],
                name="brain_rep_est_stat_cr_idx",
            ),
            models.Index(fields=["author"], name="brain_rep_author_idx"),
        ]

    def __str__(self) -> str:
        return f"BrainReporting {self.id} [{self.status}]"


class BrainExtraction(BaseModel):
    reporting = models.ForeignKey(
        BrainReporting,
        on_delete=models.CASCADE,
        related_name="extractions",
    )
    extractor_id = models.CharField(max_length=80)
    extractor_version = models.CharField(max_length=40)
    source_sha256 = models.CharField(max_length=64)
    payload = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting", "extractor_id", "extractor_version", "source_sha256"],
                name="brain_ext_version_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"BrainExtraction {self.extractor_id}@{self.extractor_version}"
