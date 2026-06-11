from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from django.utils import timezone

if TYPE_CHECKING:
    from houston.observations.models import ObservationProcessing

_OBSERVATION_PROCESSING_LOG_KEYS = frozenset(
    {
        "observation_id",
        "establishment_id",
        "processing_status",
        "ux_status",
        "attempt_count",
        "processing_duration_seconds",
        "last_error_code",
        "outcome",
        "event",
        "exception_class",
    }
)
_WS_AUTH_LOG_KEYS = frozenset(
    {
        "establishment_id",
        "ws_close_code",
        "ws_auth_failure_reason",
        "event",
    }
)
_API_REQUEST_LOG_KEYS = frozenset(
    {
        "request_path",
        "request_method",
        "event",
        "exception_class",
    }
)
_REFRESH_TOKEN_REUSE_LOG_KEYS = frozenset(
    {
        "session_id",
        "refresh_family_id",
        "refresh_record_id",
        "user_id",
    }
)
_TEMPORARY_UPLOAD_LOG_KEYS = frozenset(
    {
        "declared_content_type",
        "size_bytes",
        "pillow_image_format",
        "pillow_image_mode",
        "pillow_image_size",
        "heif_plugin_loaded",
        "error_raised_at",
    }
)
_CELERY_TASK_FAILURE_LOG_KEYS = frozenset(
    {
        "establishment_id",
        "horizon_days",
        "exception_class",
        "task_name",
        "deleted_count",
    }
)
_OBSERVATION_ENQUEUE_LOG_KEYS = frozenset(
    {
        "observation_id",
        "event",
        "exception_class",
    }
)
_SENSITIVE_FIELD_NAMES = frozenset(
    {
        "raw_text",
        "validated_text",
        "storage_key",
        "body",
        "ticket",
        "token",
        "password",
        "authorization",
    }
)
_CONTROLLED_VALUE_KEYS = frozenset(
    {
        "event",
        "processing_status",
        "ux_status",
        "last_error_code",
        "ws_auth_failure_reason",
        "outcome",
        "request_method",
        "exception_class",
        "error_raised_at",
    }
)
_SENSITIVE_SUBSTRINGS = (
    "raw_text",
    "validated_text",
    "storage_key",
    "private_media",
    "sk-",
    '"title"',
    '"structured_summary"',
)


def observation_processing_duration_seconds(
    *,
    processing: ObservationProcessing,
    at: datetime | None = None,
) -> float | None:
    if processing.processing_started_at is None:
        return None
    reference = at or timezone.now()
    return max(0.0, (reference - processing.processing_started_at).total_seconds())


def build_observation_processing_log_context(
    *,
    processing: ObservationProcessing,
    establishment_id: uuid.UUID | None = None,
    event: str = "",
    at: datetime | None = None,
) -> dict[str, Any]:
    from houston.observations.selectors import resolve_ux_status

    resolved_establishment_id = establishment_id
    if resolved_establishment_id is None:
        resolved_establishment_id = getattr(processing, "observation_establishment_id", None)
    if resolved_establishment_id is None and hasattr(processing, "observation"):
        resolved_establishment_id = processing.observation.establishment_id

    outcome = processing.outcome or ""
    context: dict[str, Any] = {
        "observation_id": str(processing.observation_id),
        "processing_status": processing.status,
        "ux_status": resolve_ux_status(status=processing.status, outcome=outcome),
        "attempt_count": processing.attempt_count,
        "last_error_code": (processing.last_error_code or "")[:80],
        "outcome": outcome[:32],
    }
    if resolved_establishment_id is not None:
        context["establishment_id"] = str(resolved_establishment_id)
    duration = observation_processing_duration_seconds(processing=processing, at=at)
    if duration is not None:
        context["processing_duration_seconds"] = round(duration, 3)
    if event.strip():
        context["event"] = event.strip()[:80]
    return sanitize_log_context(context, allowed_keys=_OBSERVATION_PROCESSING_LOG_KEYS)


def build_ws_auth_failure_log_context(
    *,
    establishment_id: uuid.UUID,
    reason: str,
    close_code: int,
    event: str = "chat_ws_auth_failed",
) -> dict[str, Any]:
    context = {
        "establishment_id": str(establishment_id),
        "ws_auth_failure_reason": reason.strip()[:80],
        "ws_close_code": close_code,
        "event": event.strip()[:80],
    }
    return sanitize_log_context(context, allowed_keys=_WS_AUTH_LOG_KEYS)


def build_refresh_token_reuse_log_context(
    *,
    session_id: uuid.UUID,
    refresh_family_id: uuid.UUID,
    refresh_record_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    context = {
        "session_id": str(session_id),
        "refresh_family_id": str(refresh_family_id),
        "refresh_record_id": str(refresh_record_id),
        "user_id": str(user_id),
    }
    return sanitize_log_context(context, allowed_keys=_REFRESH_TOKEN_REUSE_LOG_KEYS)


def build_temporary_upload_image_type_log_context(
    *,
    declared_content_type: str,
    size_bytes: int,
    pillow_image_format: str | None,
    pillow_image_mode: str | None,
    pillow_image_size: tuple[int, int] | None,
    heif_plugin_loaded: bool,
    error_raised_at: str,
) -> dict[str, Any]:
    pillow_size = (
        f"{pillow_image_size[0]}x{pillow_image_size[1]}"
        if pillow_image_size is not None
        else None
    )
    context: dict[str, Any] = {
        "declared_content_type": declared_content_type,
        "size_bytes": size_bytes,
        "pillow_image_format": pillow_image_format or "",
        "pillow_image_mode": pillow_image_mode or "",
        "pillow_image_size": pillow_size or "",
        "heif_plugin_loaded": heif_plugin_loaded,
        "error_raised_at": error_raised_at,
    }
    return sanitize_log_context(context, allowed_keys=_TEMPORARY_UPLOAD_LOG_KEYS)


def build_celery_task_failure_log_context(
    *,
    exception_class: str,
    establishment_id: str | None = None,
    horizon_days: int | None = None,
    task_name: str = "",
    deleted_count: int | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {"exception_class": exception_class}
    if establishment_id is not None:
        context["establishment_id"] = establishment_id
    if horizon_days is not None:
        context["horizon_days"] = horizon_days
    if task_name.strip():
        context["task_name"] = task_name.strip()[:80]
    if deleted_count is not None:
        context["deleted_count"] = deleted_count
    return sanitize_log_context(context, allowed_keys=_CELERY_TASK_FAILURE_LOG_KEYS)


def build_observation_processing_failure_log_context(
    *,
    processing: ObservationProcessing | None,
    observation_id: str,
    event: str,
    exception_class: str,
) -> dict[str, Any]:
    if processing is not None:
        base = build_observation_processing_log_context(processing=processing, event=event)
        return sanitize_log_context(
            {**base, "exception_class": exception_class},
            allowed_keys=_OBSERVATION_PROCESSING_LOG_KEYS,
        )
    return build_observation_enqueue_failure_log_context(
        observation_id=uuid.UUID(observation_id),
        event=event,
        exception_class=exception_class,
    )


def build_observation_enqueue_failure_log_context(
    *,
    observation_id: uuid.UUID,
    event: str,
    exception_class: str,
) -> dict[str, Any]:
    context = {
        "observation_id": str(observation_id),
        "event": event.strip()[:80],
        "exception_class": exception_class,
    }
    return sanitize_log_context(context, allowed_keys=_OBSERVATION_ENQUEUE_LOG_KEYS)


def build_api_request_log_context(
    *,
    request_path: str,
    request_method: str,
    event: str = "api_unhandled_exception",
    exception_class: str = "",
) -> dict[str, Any]:
    context = {
        "request_path": request_path[:200],
        "request_method": request_method.upper()[:16],
        "event": event.strip()[:80],
    }
    if exception_class.strip():
        context["exception_class"] = exception_class.strip()[:80]
    return sanitize_log_context(context, allowed_keys=_API_REQUEST_LOG_KEYS)


def sanitize_log_context(
    context: dict[str, Any] | None,
    *,
    allowed_keys: frozenset[str],
) -> dict[str, Any]:
    if not context:
        return {}

    sanitized: dict[str, Any] = {}
    for key, value in context.items():
        if key not in allowed_keys or key in _SENSITIVE_FIELD_NAMES:
            continue
        normalized = _normalize_log_value(value)
        if normalized is None:
            continue
        if key not in _CONTROLLED_VALUE_KEYS and _contains_sensitive_fragment(normalized):
            continue
        sanitized[key] = normalized
    return sanitized


def _normalize_log_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, str):
        normalized = value.strip()
        return normalized if normalized else None
    return str(value)


def _contains_sensitive_fragment(value: Any) -> bool:
    serialized = str(value).lower()
    return any(fragment in serialized for fragment in _SENSITIVE_SUBSTRINGS)
