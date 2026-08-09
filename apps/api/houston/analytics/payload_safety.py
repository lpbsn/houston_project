from __future__ import annotations

from typing import Any

FORBIDDEN_PROVIDER_PAYLOAD_KEYS = frozenset(
    {
        "raw_text",
        "media",
        "comment",
        "action_plan",
        "author",
        "submitted_at",
        "location_text",
        "routing_status",
        "expected_action",
    }
)


def provider_payload_safety_errors(payloads: list[dict[str, Any]]) -> list[str]:
    found_keys: set[str] = set()
    for payload in payloads:
        _collect_forbidden_keys(payload, found_keys)
    return sorted(found_keys)


def assert_provider_payloads_are_safe(payloads: list[dict[str, Any]]) -> None:
    if provider_payload_safety_errors(payloads):
        raise RuntimeError("Analytics provider payload contains forbidden key data.")


def _collect_forbidden_keys(value: Any, found_keys: set[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_PROVIDER_PAYLOAD_KEYS:
                found_keys.add(key)
            _collect_forbidden_keys(child, found_keys)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _collect_forbidden_keys(child, found_keys)
