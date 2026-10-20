"""Configuration copied at admission. A later attempt reads this copy and nothing newer."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from pathlib import Path

from django.conf import settings

from houston.brain.errors import BrainWorkError
from houston.brain.models import BrainAnalysis, BrainExtraction, BrainKnowledgeVersion

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
    configuration = {
        "extractor_id": extraction.extractor_id,
        "extractor_version": extraction.extractor_version,
        "source_sha256": extraction.source_sha256,
        "schema_version": settings.HOUSTON_BRAIN_SCHEMA_VERSION,
        "prompt_version": settings.HOUSTON_BRAIN_PROMPT_VERSION,
        "knowledge": selected_knowledge(),
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
    from houston.brain.integration import (
        freeze_investigation_configuration,
        investigation_admission_enabled,
    )

    if investigation_admission_enabled():
        return freeze_investigation_configuration(configuration)
    return configuration


def empty_knowledge() -> dict:
    """No Knowledge is selected. This is not a default corpus."""
    return {
        "version_id": None,
        "selection": "none",
        "formulation": "",
        "conditions": "",
        "limits": "",
        "uncertainty": "",
    }


def selected_knowledge() -> dict:
    """Copy the active version's content at admission. Later edits are not read again."""
    version = (
        BrainKnowledgeVersion.objects.filter(is_active=True)
        .only("id", "global_formulation", "conditions", "limits", "uncertainty")
        .first()
    )
    if version is None:
        return empty_knowledge()
    return _knowledge_snapshot(version)


def frozen_knowledge(configuration: object) -> dict:
    """Content already copied onto the analysis. The live version row is not loaded."""
    if not isinstance(configuration, dict):
        return empty_knowledge()
    raw = configuration.get("knowledge")
    if not isinstance(raw, dict):
        return empty_knowledge()
    version_id = raw.get("version_id")
    selection = raw.get("selection")
    if selection not in {"none", "active"}:
        selection = "active" if version_id else "none"
    return {
        "version_id": None if not version_id else str(version_id),
        "selection": selection,
        "formulation": str(raw.get("formulation") or ""),
        "conditions": str(raw.get("conditions") or ""),
        "limits": str(raw.get("limits") or ""),
        "uncertainty": str(raw.get("uncertainty") or ""),
    }


def _knowledge_snapshot(version: BrainKnowledgeVersion) -> dict:
    return {
        "version_id": str(version.id),
        "selection": "active",
        "formulation": version.global_formulation,
        "conditions": version.conditions,
        "limits": version.limits,
        "uncertainty": version.uncertainty,
    }


def canonical_json(value: object) -> str:
    """JSON shared by the hash, the local count, and the provider user message."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


# Published o200k chat framing is a handful of tokens. The strict schema is already
# counted as text. This margin covers the provider's unpublished schema injection.
CALL_FRAMING_TOKENS = 1024
_O200K_HASH = "446a9538cb6c348e3516120d7c08b09f57c36495e2acfffe59a5bf8b0cfb1a2d"
_O200K_PATH = Path(__file__).resolve().parent / "tokenizers" / "o200k_base.tiktoken"
_O200K_FALLBACK = re.compile(
    r"^(?:gpt-5-mini(?:-\d{4}-\d{2}-\d{2})?|gpt-4o(?:-.+)?|gpt-4\.1(?:-.+)?)$"
)
_encoding_lock = threading.Lock()
_o200k_encoding = None
_prompt_tokens: dict[str, int] = {}
_schema_tokens: dict[str, int] = {}


def _encode_len(encoding, text: str) -> int:
    return len(encoding.encode(text, disallowed_special=()))


def _redirect_o200k_bpe(blobpath: str, expected_hash: str | None = None):
    """Read the vendored o200k ranks. A remote encoding URL is not fetched."""
    from tiktoken.load import load_tiktoken_bpe

    if blobpath.endswith("/o200k_base.tiktoken") or blobpath.endswith("o200k_base.tiktoken"):
        return load_tiktoken_bpe(str(_O200K_PATH), expected_hash=expected_hash or _O200K_HASH)
    raise configuration_unusable()


def _o200k():
    """One o200k encoding per process, built from the vendored rank file."""
    global _o200k_encoding
    if _o200k_encoding is not None:
        return _o200k_encoding
    with _encoding_lock:
        if _o200k_encoding is not None:
            return _o200k_encoding
        import tiktoken
        from tiktoken_ext import openai_public

        original = openai_public.load_tiktoken_bpe
        openai_public.load_tiktoken_bpe = _redirect_o200k_bpe
        try:
            blob = openai_public.o200k_base()
            encoding = tiktoken.Encoding(**blob)
        except (OSError, ValueError) as exc:
            raise configuration_unusable() from exc
        finally:
            openai_public.load_tiktoken_bpe = original
        _o200k_encoding = encoding
        return _o200k_encoding


def encoding_for_frozen(*, provider: str, model: str):
    """Tokenizer for one frozen provider and model.

    Only the vendored o200k ranks are loaded. Other encodings are not fetched.
    """
    provider_name = (provider or "").strip().lower()
    model_name = (model or "").strip()
    if provider_name in {"", "fake"} or model_name == "fake":
        return _o200k()
    if provider_name != "openai":
        raise configuration_unusable()
    try:
        import tiktoken

        name = tiktoken.encoding_name_for_model(model_name)
    except KeyError:
        name = ""
    if name == "o200k_base" or (not name and _O200K_FALLBACK.fullmatch(model_name)):
        return _o200k()
    raise configuration_unusable()


def _fixed_call_tokens(encoding) -> tuple[int, int]:
    """Prompt and strict schema, encoded once per encoding name."""
    key = encoding.name
    prompt = _prompt_tokens.get(key)
    schema = _schema_tokens.get(key)
    if prompt is not None and schema is not None:
        return prompt, schema
    from houston.brain.contract import openai_strict_response_format
    from houston.brain.openai_provider import system_prompt

    with _encoding_lock:
        prompt = _prompt_tokens.get(key)
        schema = _schema_tokens.get(key)
        if prompt is None or schema is None:
            prompt = _encode_len(encoding, system_prompt())
            schema = _encode_len(encoding, canonical_json(openai_strict_response_format()))
            _prompt_tokens[key] = prompt
            _schema_tokens[key] = schema
        return prompt, schema


def frozen_counter(configuration: object) -> tuple[str, str]:
    """Provider and model copied on the analysis. Missing values count as the fake encoding."""
    if not isinstance(configuration, dict):
        return "fake", "fake"
    return (
        str(configuration.get("provider") or "fake"),
        str(configuration.get("model") or "fake"),
    )


def json_token_count(value: object, *, provider: str = "fake", model: str = "fake") -> int:
    """o200k (or the frozen model's encoding) of one canonical JSON value."""
    encoding = encoding_for_frozen(provider=provider, model=model)
    return _encode_len(encoding, canonical_json(value))


def call_input_tokens(payload: object, *, provider: str = "fake", model: str = "fake") -> int:
    """Exact local cost of one closed Chat Completions request.

    Prompt, user JSON, and strict schema are encoded. The framing margin is constant.
    """
    encoding = encoding_for_frozen(provider=provider, model=model)
    prompt_tokens, schema_tokens = _fixed_call_tokens(encoding)
    user_tokens = _encode_len(encoding, canonical_json(payload))
    return prompt_tokens + user_tokens + schema_tokens + CALL_FRAMING_TOKENS


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
