from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from houston.ai.observation_pipeline_provider_schema import (
    AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME,
)

_ERROR_CONTEXT_ALLOWED_KEYS = frozenset(
    {
        "validation_error_count",
        "first_error_path",
        "first_error_type",
        "top_level_keys",
        "has_candidates",
        "candidate_count",
        "provider_request_id",
        "response_format_mode",
        "provider_error_type",
        "provider_error_param",
        "provider_error_code",
        "message_excerpt",
        "response_format_name",
    }
)
_MESSAGE_EXCERPT_MAX_LENGTH = 200
_ERROR_CONTEXT_MAX_BYTES = 1024
_SENSITIVE_SUBSTRINGS = (
    "validated_text",
    "raw_text",
    "sk-",
    '"structured_summary"',
    '"title"',
)


def build_provider_bad_request_error_context(
    *,
    exc: BaseException,
    response_format_mode: str = "",
) -> dict[str, Any]:
    message = str(exc).strip()
    context: dict[str, Any] = {
        "provider_error_type": type(exc).__name__[:80],
        "provider_error_param": _provider_error_field(exc, "param"),
        "provider_error_code": _provider_error_field(exc, "code"),
        "message_excerpt": message[:_MESSAGE_EXCERPT_MAX_LENGTH] if message else "",
        "response_format_name": AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME,
    }
    if response_format_mode.strip():
        context["response_format_mode"] = response_format_mode.strip()[:80]
    return sanitize_observation_pipeline_error_context(context)


def _provider_error_field(exc: BaseException, field: str) -> str:
    value = getattr(exc, field, None)
    if value is None:
        return ""
    return str(value).strip()[:200]


def build_invalid_output_error_context(
    *,
    payload: dict[str, Any] | None,
    exc: BaseException,
    provider_request_id: str = "",
    response_format_mode: str = "",
) -> dict[str, Any]:
    diagnostic_exc = exc.__cause__ if isinstance(exc.__cause__, PydanticValidationError) else exc
    context: dict[str, Any] = {
        **_payload_shape_summary(payload),
        **_validation_summary(diagnostic_exc),
    }
    if provider_request_id.strip():
        context["provider_request_id"] = provider_request_id.strip()[:200]
    if response_format_mode.strip():
        context["response_format_mode"] = response_format_mode.strip()[:80]
    return sanitize_observation_pipeline_error_context(context)


def sanitize_observation_pipeline_error_context(context: dict[str, Any] | None) -> dict[str, Any]:
    if not context:
        return {}

    sanitized: dict[str, Any] = {}
    for key, value in context.items():
        if key not in _ERROR_CONTEXT_ALLOWED_KEYS:
            continue
        sanitized_value = _sanitize_value(key, value)
        if sanitized_value is None:
            continue
        if _contains_sensitive_fragment(sanitized_value):
            continue
        sanitized[key] = sanitized_value

    return _truncate_error_context(sanitized)


def _payload_shape_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "top_level_keys": [],
            "has_candidates": False,
            "candidate_count": 0,
        }

    top_level_keys = sorted(str(key) for key in payload.keys())
    candidates = payload.get("candidates")
    has_candidates = isinstance(candidates, list)
    candidate_count = len(candidates) if has_candidates else 0
    return {
        "top_level_keys": top_level_keys[:20],
        "has_candidates": has_candidates,
        "candidate_count": max(0, candidate_count),
    }


def _validation_summary(exc: BaseException) -> dict[str, Any]:
    if not isinstance(exc, PydanticValidationError):
        return {
            "validation_error_count": 0,
            "first_error_path": "",
            "first_error_type": "",
        }

    errors = exc.errors()
    first = errors[0] if errors else {}
    return {
        "validation_error_count": exc.error_count(),
        "first_error_path": _error_path(first.get("loc", ())),
        "first_error_type": str(first.get("type", ""))[:80],
    }


def _error_path(location: tuple[Any, ...]) -> str:
    parts: list[str] = []
    for item in location:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, int):
            parts.append(str(item))
    return ".".join(parts)[:200]


def _sanitize_value(key: str, value: Any) -> Any:
    if key == "validation_error_count":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return max(0, value)
        return 0

    string_keys = {
        "first_error_path",
        "first_error_type",
        "provider_request_id",
        "response_format_mode",
        "provider_error_type",
        "provider_error_param",
        "provider_error_code",
        "message_excerpt",
        "response_format_name",
    }
    if key in string_keys:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized[:200] if normalized else None

    if key == "top_level_keys":
        if not isinstance(value, list):
            return []
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if not normalized or _contains_sensitive_fragment(normalized):
                continue
            cleaned.append(normalized)
        return cleaned[:20]

    if key == "has_candidates":
        return bool(value)

    if key == "candidate_count":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return max(0, value)
        return 0

    return None


def _contains_sensitive_fragment(value: Any) -> bool:
    serialized = (
        json.dumps(value, ensure_ascii=False).lower()
        if not isinstance(value, str)
        else value.lower()
    )
    return any(fragment in serialized for fragment in _SENSITIVE_SUBSTRINGS)


def _truncate_error_context(context: dict[str, Any]) -> dict[str, Any]:
    serialized = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    if len(serialized.encode("utf-8")) <= _ERROR_CONTEXT_MAX_BYTES:
        return context

    return {
        "validation_error_count": context.get("validation_error_count", 0),
        "first_error_path": context.get("first_error_path", ""),
        "first_error_type": context.get("first_error_type", ""),
        "has_candidates": context.get("has_candidates", False),
        "candidate_count": context.get("candidate_count", 0),
    }
