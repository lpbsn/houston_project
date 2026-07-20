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


def _canonicalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _canonicalize_value(value[key]) for key in sorted(value.keys())}
    if isinstance(value, list):
        if value and isinstance(value[0], dict) and "membership_id" in value[0]:
            items = [_canonicalize_value(item) for item in value]
            return sorted(
                items,
                key=lambda item: (
                    str(item.get("membership_id") or ""),
                    str(item.get("business_unit_id") or ""),
                ),
            )
        return [
            _canonicalize_value(item) if isinstance(item, dict) else _normalize_scalar(item)
            for item in value
        ]
    return _normalize_scalar(value)


def compute_planning_request_hash(
    *,
    use_shared_chronology: bool,
    items: list[dict],
) -> str:
    canonical_items = [_canonicalize_value(dict(item)) for item in items]
    canonical_items.sort(key=lambda item: str(item.get("item_id") or ""))
    for item in canonical_items:
        if isinstance(item.get("recurrence_days"), list):
            item["recurrence_days"] = sorted(str(day) for day in item["recurrence_days"])
    canonical = {
        "use_shared_chronology": use_shared_chronology,
        "items": canonical_items,
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
