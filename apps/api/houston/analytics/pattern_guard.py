from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from houston.ai.models import AIUsageLog
from houston.analytics.classifier import (
    ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
    ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
    PatternClassifierError,
    PatternClassifierProvider,
    parse_pattern_duplicate_guard_response,
)
from houston.analytics.pattern_shortlist import PatternDuplicateGuardCandidate
from houston.signals.models import Signal


@dataclass(frozen=True)
class PatternDuplicateGuardDecision:
    action: str
    pattern_id: uuid.UUID | None = None
    reason: str = ""
    reason_code: str | None = None


def _assess_duplicate_guard_best_effort(
    *,
    signal: Signal,
    provider: PatternClassifierProvider,
    canonical_label: str,
    shortlist: list[PatternDuplicateGuardCandidate],
    shortlist_metrics: dict[str, int] | None = None,
) -> PatternDuplicateGuardDecision:
    shortlist_ids = {candidate.id for candidate in shortlist}
    input_payload = {
        "schema_version": ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
        "prompt_version": ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
        "signal": _duplicate_guard_signal_payload(signal),
        "canonical_label": canonical_label,
        "candidate_patterns": [
            {
                "id": str(candidate.id),
                "label": candidate.label,
                "normalized_label": candidate.normalized_label,
                "semantic_label": candidate.semantic_label,
                "normalized_semantic_label": candidate.normalized_semantic_label,
            }
            for candidate in shortlist
        ],
    }

    started_at = time.monotonic()
    try:
        response = provider.assess_duplicate(input_payload=input_payload)
        parsed = parse_pattern_duplicate_guard_response(response.payload)
        if parsed.result_type == "reuse_existing_pattern":
            if parsed.pattern_id not in shortlist_ids:
                _write_duplicate_guard_usage_log(
                    signal=signal,
                    provider=provider.provider,
                    model=response.model or getattr(provider, "model", ""),
                    status=AIUsageLog.Status.FAILED,
                    latency_ms=_elapsed_ms(started_at),
                    correlation_id=uuid.uuid4(),
                    error_code="duplicate_guard_pattern_outside_shortlist",
                    error_context=shortlist_metrics,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    total_tokens=response.total_tokens,
                )
                return PatternDuplicateGuardDecision(
                    action="fallback",
                    reason="outside_shortlist",
                )
            _write_duplicate_guard_usage_log(
                signal=signal,
                provider=provider.provider,
                model=response.model or getattr(provider, "model", ""),
                status=AIUsageLog.Status.SUCCEEDED,
                latency_ms=_elapsed_ms(started_at),
                correlation_id=uuid.uuid4(),
                error_context=shortlist_metrics,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.total_tokens,
            )
            return PatternDuplicateGuardDecision(
                action="reused",
                pattern_id=parsed.pattern_id,
                reason_code=parsed.reason_code,
            )

        _write_duplicate_guard_usage_log(
            signal=signal,
            provider=provider.provider,
            model=response.model or getattr(provider, "model", ""),
            status=AIUsageLog.Status.SUCCEEDED,
            latency_ms=_elapsed_ms(started_at),
            correlation_id=uuid.uuid4(),
            error_context=shortlist_metrics,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=response.total_tokens,
        )
        return PatternDuplicateGuardDecision(
            action="created",
            reason_code=parsed.reason_code,
        )
    except PatternClassifierError as exc:
        _write_duplicate_guard_usage_log(
            signal=signal,
            provider=provider.provider,
            model=getattr(provider, "model", ""),
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(started_at),
            correlation_id=uuid.uuid4(),
            error_code=getattr(exc, "error_code", "duplicate_guard_error"),
            error_context=shortlist_metrics,
        )
        return PatternDuplicateGuardDecision(
            action="fallback",
            reason=getattr(exc, "error_code", "duplicate_guard_error"),
        )


def _duplicate_guard_signal_payload(signal: Signal) -> dict[str, Any]:
    activity_subject = signal.activity_subject.label if signal.activity_subject_id else ""
    operational_unit = signal.operational_unit.label if signal.operational_unit_id else ""
    return {
        "title": signal.title,
        "structured_summary": signal.structured_summary,
        "issue_focus": signal.issue_focus,
        "activity_subject": activity_subject,
        "operational_unit": operational_unit,
    }


def _write_duplicate_guard_usage_log(
    *,
    signal: Signal,
    provider: str,
    model: str,
    status: str,
    latency_ms: int,
    correlation_id: uuid.UUID,
    error_code: str = "",
    error_context: dict[str, int] | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
) -> None:
    AIUsageLog.objects.create(
        ai_domain=AIUsageLog.Domain.ANALYTICS_PATTERN,
        provider=provider,
        model=model or "",
        prompt_version=ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
        schema_version=ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
        status=status,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        error_code=error_code,
        error_context={
            "phase": "analytics_pattern_duplicate_guard",
            **(error_context or {}),
        },
        correlation_id=correlation_id,
        establishment=signal.establishment,
    )


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)
