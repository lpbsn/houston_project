from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time
from typing import Any
from uuid import UUID


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _sort_assignees(assignees: list[dict]) -> list[dict]:
    copied = [
        {key: _normalize_scalar(value) for key, value in dict(item).items()}
        for item in assignees
    ]
    return sorted(
        copied,
        key=lambda item: (
            str(item.get("membership_id") or ""),
            str(item.get("business_unit_id") or ""),
        ),
    )


def _canonicalize_body(body: dict) -> dict:
    canonical: dict[str, Any] = {}
    for key in sorted(body.keys()):
        value = body[key]
        if key == "assignees" and isinstance(value, list):
            canonical[key] = _sort_assignees(value)
        elif key == "recurrence_days" and isinstance(value, list):
            canonical[key] = sorted(str(day) for day in value)
        elif isinstance(value, dict):
            canonical[key] = _canonicalize_body(value)
        elif isinstance(value, list):
            canonical[key] = [
                _canonicalize_body(item) if isinstance(item, dict) else _normalize_scalar(item)
                for item in value
            ]
        else:
            canonical[key] = _normalize_scalar(value)
    return canonical


def compute_mixed_request_hash(*, schedule_body: dict, use_body: dict) -> str:
    canonical = {
        "schedule": _canonicalize_body(schedule_body),
        "use": _canonicalize_body(use_body),
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
