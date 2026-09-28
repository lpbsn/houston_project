from __future__ import annotations

from typing import Any


def flatten_signal_feed_items(body: dict[str, Any]) -> list[dict[str, Any]]:
    if "sections" in body:
        sections = body.get("sections") or []
        return [item for section in sections for item in section.get("items", [])]
    pins = list(body.get("pins") or [])
    items = list(body.get("items") or [])
    return [*pins, *items]


def signal_feed_section(body: dict[str, Any], status: str) -> dict[str, Any] | None:
    if "sections" in body:
        for section in body.get("sections") or []:
            if section.get("status") == status:
                return section
        return None
    items = [
        item
        for item in body.get("items") or []
        if item.get("status") == status
    ]
    if not items and not body.get("items"):
        return None
    return {
        "status": status,
        "items": items,
        "next_cursor": body.get("next_cursor"),
        "has_more": body.get("has_more"),
    }
