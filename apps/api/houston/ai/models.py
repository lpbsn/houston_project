from __future__ import annotations

from django.db import models

from houston.core.models import BaseModel


class AIUsageLog(BaseModel):
    class Domain(models.TextChoices):
        ONBOARDING = "onboarding", "Onboarding"

    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        FALLBACK_SUCCEEDED = "fallback_succeeded", "Fallback succeeded"
        FALLBACK_FAILED = "fallback_failed", "Fallback failed"

    ai_domain = models.CharField(
        max_length=40,
        choices=Domain.choices,
        default=Domain.ONBOARDING,
    )
    provider = models.CharField(max_length=80)
    model = models.CharField(max_length=120, blank=True, default="")
    prompt_version = models.CharField(max_length=80)
    schema_version = models.CharField(max_length=80)
    status = models.CharField(max_length=40, choices=Status.choices)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    total_tokens = models.PositiveIntegerField(null=True, blank=True)
    error_code = models.CharField(max_length=80, blank=True, default="")
    correlation_id = models.UUIDField(db_index=True)
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.SET_NULL,
        related_name="ai_usage_logs",
        null=True,
        blank=True,
        db_index=False,
    )
    onboarding_session = models.ForeignKey(
        "establishments.OnboardingSession",
        on_delete=models.SET_NULL,
        related_name="ai_usage_logs",
        null=True,
        blank=True,
        db_index=False,
    )
    onboarding_proposal = models.ForeignKey(
        "establishments.OnboardingProposal",
        on_delete=models.SET_NULL,
        related_name="ai_usage_logs",
        null=True,
        blank=True,
        db_index=False,
    )

    class Meta:
        indexes = [
            models.Index(fields=["ai_domain", "status"], name="ai_usage_domain_status_idx"),
            models.Index(fields=["provider", "model"], name="ai_usage_provider_model_idx"),
            models.Index(fields=["establishment"], name="ai_usage_est_idx"),
            models.Index(fields=["onboarding_session"], name="ai_usage_session_idx"),
            models.Index(fields=["onboarding_proposal"], name="ai_usage_prop_idx"),
            models.Index(fields=["created_at"], name="ai_usage_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.ai_domain} {self.provider}/{self.model} [{self.status}]"
