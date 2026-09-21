from __future__ import annotations

from typing import Any


def flatten_signal_feed_items(body: dict[str, Any]) -> list[dict[str, Any]]:
    sections = body.get("sections") or []
    return [item for section in sections for item in section.get("items", [])]


def signal_feed_section(body: dict[str, Any], status: str) -> dict[str, Any] | None:
    for section in body.get("sections") or []:
        if section.get("status") == status:
            return section
    return None
