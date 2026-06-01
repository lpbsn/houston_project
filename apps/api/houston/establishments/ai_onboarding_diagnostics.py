from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from houston.establishments.services import OnboardingProposalValidationError

_ERROR_CONTEXT_ALLOWED_KEYS = frozenset(
    {
        "failure_stage",
        "validation_error_count",
        "missing_fields",
        "invalid_field_paths",
        "business_error_codes",
        "pydantic_error_types",
        "provider_request_id",
        "response_format_mode",
        "strict_schema_fallback_reason",
    }
)
_ERROR_CONTEXT_MAX_BYTES = 1024
_ERROR_CONTEXT_MAX_LIST_ITEMS = 20
_ERROR_CONTEXT_MAX_BUSINESS_CODES = 10
_ERROR_CONTEXT_MAX_PYDANTIC_TYPES = 10
_SENSITIVE_SUBSTRINGS = (
    "activity_description",
    "establishment_name",
    "sk-",
    '"reason"',
    '"label"',
    '"term"',
    '"pattern"',
    '"meaning"',
)


def summarize_ai_onboarding_failure(exc: BaseException) -> dict[str, Any]:
    diagnostic_exc = _diagnostic_source_exception(exc)
    failure_stage = _failure_stage(exc)
    summary: dict[str, Any] = {
        "failure_stage": failure_stage,
        "validation_error_count": _validation_error_count(diagnostic_exc),
        "missing_fields": _missing_fields(diagnostic_exc),
        "invalid_field_paths": _invalid_field_paths(diagnostic_exc),
        "business_error_codes": _business_error_codes(diagnostic_exc),
        "pydantic_error_types": _pydantic_error_types(diagnostic_exc),
    }
    return sanitize_error_context(summary)


def _diagnostic_source_exception(exc: BaseException) -> BaseException:
    if isinstance(exc, OnboardingProposalValidationError | PydanticValidationError):
        return exc
    cause = exc.__cause__
    if isinstance(cause, OnboardingProposalValidationError | PydanticValidationError):
        return cause
    return exc


def sanitize_error_context(context: dict[str, Any] | None) -> dict[str, Any]:
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


def _failure_stage(exc: BaseException) -> str:
    error_code = getattr(exc, "error_code", "")
    if error_code == "invalid_structured_output":
        message = str(exc).lower()
        if "invalid json" in message:
            return "json_parse"
        if "empty response" in message:
            return "provider_empty"
        return "pydantic"
    if isinstance(exc, OnboardingProposalValidationError):
        return "business_validation"
    if error_code in {"provider_timeout", "provider_unavailable"}:
        return "provider_error"
    if isinstance(exc, PydanticValidationError):
        return "pydantic"
    return "unknown"


def _validation_error_count(exc: BaseException) -> int:
    if isinstance(exc, OnboardingProposalValidationError):
        return len(exc.errors)
    if isinstance(exc, PydanticValidationError):
        return exc.error_count()
    return 0


def _missing_fields(exc: BaseException) -> list[str]:
    if not isinstance(exc, PydanticValidationError):
        return []

    missing: list[str] = []
    for error in exc.errors():
        if error.get("type") != "missing":
            continue
        location = error.get("loc", ())
        if location and isinstance(location[0], str):
            top_level = location[0]
            if top_level not in missing:
                missing.append(top_level)
    return missing[:_ERROR_CONTEXT_MAX_LIST_ITEMS]


def _invalid_field_paths(exc: BaseException) -> list[str]:
    paths: list[str] = []

    if isinstance(exc, PydanticValidationError):
        for error in exc.errors():
            location = error.get("loc", ())
            if not location:
                continue
            pointer = _json_pointer(location)
            if pointer and pointer not in paths:
                paths.append(pointer)

    if isinstance(exc, OnboardingProposalValidationError):
        for error in exc.errors:
            section = error.get("section")
            field = error.get("field")
            if section and field:
                pointer = f"/{section}/-/{field}"
            elif section:
                pointer = f"/{section}"
            else:
                continue
            if pointer not in paths:
                paths.append(pointer)

    return paths[:_ERROR_CONTEXT_MAX_LIST_ITEMS]


def _business_error_codes(exc: BaseException) -> list[str]:
    if not isinstance(exc, OnboardingProposalValidationError):
        return []

    codes: list[str] = []
    for error in exc.errors:
        code = error.get("code")
        if isinstance(code, str) and code and code not in codes:
            codes.append(code)
    return codes[:_ERROR_CONTEXT_MAX_BUSINESS_CODES]


def _pydantic_error_types(exc: BaseException) -> list[str]:
    if not isinstance(exc, PydanticValidationError):
        return []

    types: list[str] = []
    for error in exc.errors():
        error_type = error.get("type")
        if isinstance(error_type, str) and error_type and error_type not in types:
            types.append(error_type)
    return types[:_ERROR_CONTEXT_MAX_PYDANTIC_TYPES]


def _json_pointer(location: tuple[Any, ...]) -> str:
    parts: list[str] = []
    for item in location:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, int):
            parts.append(str(item))
    if not parts:
        return ""
    return "/" + "/".join(parts)


def _sanitize_value(key: str, value: Any) -> Any:
    if key in {
        "missing_fields",
        "invalid_field_paths",
        "business_error_codes",
        "pydantic_error_types",
    }:
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
        return cleaned[:_ERROR_CONTEXT_MAX_LIST_ITEMS]

    if key == "validation_error_count":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return max(0, value)
        return 0

    if key == "failure_stage":
        return value if isinstance(value, str) and value.strip() else "unknown"

    if key in {"provider_request_id", "response_format_mode", "strict_schema_fallback_reason"}:
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        if not normalized or len(normalized) > 200:
            return normalized[:200] if normalized else None
        return normalized

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

    trimmed = dict(context)
    for list_key in (
        "invalid_field_paths",
        "missing_fields",
        "business_error_codes",
        "pydantic_error_types",
    ):
        items = trimmed.get(list_key)
        if isinstance(items, list) and len(items) > 5:
            trimmed[list_key] = items[:5]

    trimmed.pop("strict_schema_fallback_reason", None)
    serialized = json.dumps(trimmed, ensure_ascii=False, separators=(",", ":"))
    if len(serialized.encode("utf-8")) <= _ERROR_CONTEXT_MAX_BYTES:
        return trimmed

    return {
        "failure_stage": trimmed.get("failure_stage", "unknown"),
        "validation_error_count": trimmed.get("validation_error_count", 0),
    }
