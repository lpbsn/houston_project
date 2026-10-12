"""Configuration copied at admission. A later attempt reads this copy and nothing newer."""

from __future__ import annotations

import hashlib
import json

from django.conf import settings

from houston.brain.errors import BrainWorkError
from houston.brain.models import BrainAnalysis, BrainExtraction

_UNUSABLE = "La configuration figée de l'analyse est inutilisable."

RUNTIME_CEILING_KEYS = (
    "per_call_input_tokens",
    "per_call_output_tokens",
    "total_input_tokens",
    "max_calls",
    "lease_seconds",
    "provider_timeout_seconds",
    "attempt_soft_seconds",
    "attempt_hard_seconds",
)


def admission_configuration(extraction: BrainExtraction) -> dict:
    knowledge = (settings.HOUSTON_BRAIN_KNOWLEDGE_VERSION or "").strip()
    return {
        "extractor_id": extraction.extractor_id,
        "extractor_version": extraction.extractor_version,
        "source_sha256": extraction.source_sha256,
        "schema_version": settings.HOUSTON_BRAIN_SCHEMA_VERSION,
        "prompt_version": settings.HOUSTON_BRAIN_PROMPT_VERSION,
        "knowledge_version": knowledge or None,
        "model": settings.HOUSTON_BRAIN_MODEL,
        "provider": settings.HOUSTON_BRAIN_PROVIDER,
        "ceilings": {
            "capture_timeout_seconds": int(settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS),
            "max_candidates_per_category": int(settings.HOUSTON_BRAIN_MAX_CANDIDATES_PER_CATEGORY),
            "max_queued_and_running": int(settings.HOUSTON_BRAIN_MAX_QUEUED_AND_RUNNING),
            "per_call_input_tokens": int(settings.HOUSTON_BRAIN_PER_CALL_INPUT_TOKENS),
            "per_call_output_tokens": int(settings.HOUSTON_BRAIN_PER_CALL_OUTPUT_TOKENS),
            "total_input_tokens": int(settings.HOUSTON_BRAIN_TOTAL_INPUT_TOKENS),
            "max_calls": int(settings.HOUSTON_BRAIN_MAX_CALLS),
            "follow_up_max_calls": int(settings.HOUSTON_BRAIN_FOLLOW_UP_MAX_CALLS),
            "follow_up_total_input_tokens": int(
                settings.HOUSTON_BRAIN_FOLLOW_UP_TOTAL_INPUT_TOKENS
            ),
            "lease_seconds": int(settings.HOUSTON_BRAIN_LEASE_SECONDS),
            "provider_timeout_seconds": int(settings.HOUSTON_BRAIN_PROVIDER_TIMEOUT_SECONDS),
            "attempt_soft_seconds": int(settings.HOUSTON_BRAIN_ATTEMPT_SOFT_SECONDS),
            "attempt_hard_seconds": int(settings.HOUSTON_BRAIN_ATTEMPT_HARD_SECONDS),
        },
    }


def digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def estimate_tokens(value: object) -> int:
    """Local size estimate used to place sections. It is not a provider tokenizer."""
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return max(1, (len(raw) + 3) // 4)


def configuration_unusable() -> BrainWorkError:
    return BrainWorkError(code="configuration_unusable", message=_UNUSABLE)


FOLLOW_UP_CEILING_KEYS = (
    "per_call_input_tokens",
    "per_call_output_tokens",
    "follow_up_total_input_tokens",
    "follow_up_max_calls",
    "lease_seconds",
    "provider_timeout_seconds",
    "attempt_soft_seconds",
    "attempt_hard_seconds",
)


def follow_up_ceilings(configuration: object) -> dict[str, int]:
    """Follow-up budgets from the analysis copy. Global settings are not read here."""
    if not isinstance(configuration, dict):
        raise configuration_unusable()
    ceilings = configuration.get("ceilings")
    if not isinstance(ceilings, dict):
        raise configuration_unusable()
    values: dict[str, int] = {}
    for key in FOLLOW_UP_CEILING_KEYS:
        try:
            number = int(ceilings[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise configuration_unusable() from exc
        if number <= 0:
            raise configuration_unusable()
        values[key] = number
    return values


def runtime_ceilings(configuration: object) -> dict[str, int]:
    if not isinstance(configuration, dict):
        raise configuration_unusable()
    ceilings = configuration.get("ceilings")
    if not isinstance(ceilings, dict):
        raise configuration_unusable()
    values: dict[str, int] = {}
    for key in RUNTIME_CEILING_KEYS:
        try:
            number = int(ceilings[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise configuration_unusable() from exc
        if number <= 0:
            raise configuration_unusable()
        values[key] = number
    return values


def frozen_extraction(analysis: BrainAnalysis) -> BrainExtraction:
    config = analysis.configuration if isinstance(analysis.configuration, dict) else {}
    try:
        extractor_id = config["extractor_id"]
        extractor_version = config["extractor_version"]
        source_sha256 = config["source_sha256"]
    except (KeyError, TypeError) as exc:
        raise configuration_unusable() from exc
    extraction = BrainExtraction.objects.filter(
        reporting_id=analysis.reporting_id,
        extractor_id=extractor_id,
        extractor_version=extractor_version,
        source_sha256=source_sha256,
    ).first()
    if extraction is None or not isinstance(extraction.payload, dict):
        raise configuration_unusable()
    return extraction
