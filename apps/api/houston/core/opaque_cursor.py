from __future__ import annotations

import base64
import json


class OpaqueCursorError(Exception):
    def __init__(self, detail: str = "Invalid cursor.", *, code: str = "validation_error") -> None:
        self.detail = detail
        self.code = code
        super().__init__(detail)


def encode_opaque_cursor(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def decode_opaque_cursor(raw: str) -> dict:
    padding = "=" * (-len(raw) % 4)
    try:
        decoded = base64.urlsafe_b64decode(f"{raw}{padding}").decode()
        payload = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OpaqueCursorError() from exc
    if not isinstance(payload, dict):
        raise OpaqueCursorError()
    return payload
