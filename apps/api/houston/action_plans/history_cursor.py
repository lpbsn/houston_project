from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from houston.action_plans.models import ActionPlanExecution
from houston.core.opaque_cursor import OpaqueCursorError, decode_opaque_cursor, encode_opaque_cursor

HISTORY_CURSOR_VERSION = "v1"
HISTORY_CURSOR_KIND = "execution_history"


@dataclass(frozen=True)
class ExecutionHistoryCursor:
    context_hash: str
    terminal_at: datetime | None
    item_id: uuid.UUID

    def validate_context(self, context_hash: str) -> None:
        if self.context_hash != context_hash:
            raise OpaqueCursorError(
                "Cursor does not match the current history context.",
                code="cursor_context_mismatch",
            )


def execution_history_context_hash(
    *,
    scope: str,
    view_mode: str,
    status: str,
    period: str,
    period_from: str | None,
    period_to: str | None,
    auth_context_hash: str,
) -> str:
    raw = json.dumps(
        {
            "auth_context_hash": auth_context_hash,
            "kind": HISTORY_CURSOR_KIND,
            "period": period,
            "period_from": period_from,
            "period_to": period_to,
            "scope": scope,
            "status": status,
            "view_mode": view_mode,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def encode_execution_history_cursor(
    *,
    scope: str,
    view_mode: str,
    status: str,
    period: str,
    period_from: str | None,
    period_to: str | None,
    auth_context_hash: str,
    terminal_at: datetime | None,
    item_id: uuid.UUID,
) -> str:
    return encode_opaque_cursor(
        {
            "v": HISTORY_CURSOR_VERSION,
            "kind": HISTORY_CURSOR_KIND,
            "context_hash": execution_history_context_hash(
                scope=scope,
                view_mode=view_mode,
                status=status,
                period=period,
                period_from=period_from,
                period_to=period_to,
                auth_context_hash=auth_context_hash,
            ),
            "terminal_at": None if terminal_at is None else terminal_at.isoformat(),
            "item_id": str(item_id),
        }
    )


def parse_execution_history_cursor(raw: str | None) -> ExecutionHistoryCursor | None:
    if not raw:
        return None
    payload = decode_opaque_cursor(raw.strip())
    if payload.get("v") != HISTORY_CURSOR_VERSION or payload.get("kind") != HISTORY_CURSOR_KIND:
        raise OpaqueCursorError()
    try:
        context_hash = str(payload["context_hash"])
        item_id = uuid.UUID(str(payload["item_id"]))
        terminal_raw = payload.get("terminal_at")
    except (KeyError, TypeError, ValueError) as exc:
        raise OpaqueCursorError() from exc
    terminal_at = None
    if terminal_raw is not None:
        terminal_at = parse_datetime(str(terminal_raw))
        if terminal_at is None or timezone.is_naive(terminal_at):
            raise OpaqueCursorError()
    return ExecutionHistoryCursor(
        context_hash=context_hash,
        terminal_at=terminal_at,
        item_id=item_id,
    )


def apply_execution_history_cursor(
    queryset: QuerySet[ActionPlanExecution],
    cursor: ExecutionHistoryCursor,
    *,
    include_undated: bool,
) -> QuerySet[ActionPlanExecution]:
    if cursor.terminal_at is None:
        return queryset.filter(terminal_at__isnull=True, id__lt=cursor.item_id)
    later = Q(terminal_at__lt=cursor.terminal_at) | Q(
        terminal_at=cursor.terminal_at,
        id__lt=cursor.item_id,
    )
    if include_undated:
        later |= Q(terminal_at__isnull=True)
    return queryset.filter(later)
