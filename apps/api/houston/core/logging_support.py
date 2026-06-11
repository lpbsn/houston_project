from __future__ import annotations

import json
import logging
from typing import Any

_STRUCTURED_EXTRA_KEYS = frozenset(
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
        "ws_close_code",
        "ws_auth_failure_reason",
        "request_path",
        "request_method",
        "deleted_count",
        "batch_count",
        "session_id",
        "refresh_family_id",
        "refresh_record_id",
        "user_id",
        "declared_content_type",
        "size_bytes",
        "pillow_image_format",
        "pillow_image_mode",
        "pillow_image_size",
        "heif_plugin_loaded",
        "error_raised_at",
        "exception_class",
        "horizon_days",
        "task_name",
        "recovered_count",
        "duration_ms",
        "total_duration_ms",
        "provider_duration_ms",
        "parse_duration_ms",
        "business_unit_count",
        "active_signal_context_count",
        "input_payload_bytes",
        "provider",
        "model",
        "candidate_count",
        "created_count",
        "aggregated_count",
    }
)


class HoustonStructuredFormatter(logging.Formatter):
    """Append safe structured fields from ``logging.Logger`` ``extra`` kwargs."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        extra = _extract_structured_extra(record)
        if not extra:
            return message
        return f"{message} {json.dumps(extra, default=str, sort_keys=True)}"


def _extract_structured_extra(record: logging.LogRecord) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    for key in _STRUCTURED_EXTRA_KEYS:
        if not hasattr(record, key):
            continue
        value = getattr(record, key)
        if value is None or value == "":
            continue
        extra[key] = value
    return extra
