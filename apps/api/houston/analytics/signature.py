from __future__ import annotations

import hashlib
import json
from typing import Any

from houston.signals.models import Signal


def _label_payload(value) -> dict[str, str] | None:
    if value is None:
        return None
    label = getattr(value, "label", "") or getattr(value, "specific_name", "")
    payload = {
        "id": str(value.id),
        "label": label,
    }
    routing_key = getattr(value, "routing_key", "")
    if routing_key:
        payload["routing_key"] = routing_key
    return payload


def build_signal_pattern_payload(signal: Signal) -> dict[str, Any]:
    signal = (
        Signal.objects.select_related(
            "affected_business_unit",
            "responsible_business_unit",
            "activity_subject",
            "operational_unit",
        )
        .only(
            "id",
            "title",
            "structured_summary",
            "issue_focus",
            "affected_business_unit__id",
            "affected_business_unit__specific_name",
            "affected_business_unit__routing_key",
            "responsible_business_unit__id",
            "responsible_business_unit__specific_name",
            "responsible_business_unit__routing_key",
            "activity_subject__id",
            "activity_subject__label",
            "activity_subject__routing_key",
            "operational_unit__id",
            "operational_unit__label",
        )
        .get(pk=signal.pk)
    )
    return {
        "signal": {
            "title": signal.title,
            "structured_summary": signal.structured_summary,
            "issue_focus": signal.issue_focus,
            "activity_subject": _label_payload(signal.activity_subject),
            "operational_unit": _label_payload(signal.operational_unit),
        },
        "context": {
            "affected_business_unit": _label_payload(signal.affected_business_unit),
            "responsible_business_unit": _label_payload(signal.responsible_business_unit),
        },
    }


def build_signal_pattern_signature(signal: Signal) -> str:
    payload = build_signal_pattern_payload(signal)
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
