from __future__ import annotations

from typing import Any


def flatten_signal_feed_items(body: dict[str, Any]) -> list[dict[str, Any]]:
    pins = list(body.get("pins") or [])
    items = list(body.get("items") or [])
    return [*pins, *items]
