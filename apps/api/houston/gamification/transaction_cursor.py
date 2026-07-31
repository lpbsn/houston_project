from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.utils.dateparse import parse_datetime

CURSOR_PART_COUNT = 3
DEFAULT_SEASON_FILTER_TOKEN = "default"
INVALID_CURSOR_ERROR_DETAIL = "Invalid cursor."


class TransactionCursorError(Exception):
    def __init__(self, detail: str = INVALID_CURSOR_ERROR_DETAIL) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class TransactionCursor:
    season_id: uuid.UUID | None
    occurred_at: datetime
    transaction_id: uuid.UUID


def _season_filter_token(season_id: uuid.UUID | None) -> str:
    if season_id is None:
        return DEFAULT_SEASON_FILTER_TOKEN
    return str(season_id)


def _encode_cursor_payload(raw: str) -> str:
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor_payload(raw: str) -> str:
    padding = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(f"{raw}{padding}").decode()
    except (ValueError, UnicodeDecodeError) as exc:
        raise TransactionCursorError() from exc


def encode_transaction_cursor(
    *,
    occurred_at: datetime,
    transaction_id: uuid.UUID,
    season_id: uuid.UUID | None,
) -> str:
    raw = "|".join(
        [
            _season_filter_token(season_id),
            occurred_at.isoformat(),
            str(transaction_id),
        ]
    )
    return _encode_cursor_payload(raw)


def decode_transaction_cursor(
    raw: str | None,
    *,
    expected_season_id: uuid.UUID | None,
) -> TransactionCursor | None:
    if not raw:
        return None

    parts = _decode_cursor_payload(raw.strip()).split("|")
    if len(parts) != CURSOR_PART_COUNT:
        raise TransactionCursorError()

    season_token = parts[0]
    expected_token = _season_filter_token(expected_season_id)
    if season_token != expected_token:
        raise TransactionCursorError()

    occurred_at = parse_datetime(parts[1])
    if occurred_at is None:
        raise TransactionCursorError()

    try:
        transaction_id = uuid.UUID(parts[2])
        season_id = None if season_token == DEFAULT_SEASON_FILTER_TOKEN else uuid.UUID(season_token)
    except ValueError as exc:
        raise TransactionCursorError() from exc

    return TransactionCursor(
        season_id=season_id,
        occurred_at=occurred_at,
        transaction_id=transaction_id,
    )
