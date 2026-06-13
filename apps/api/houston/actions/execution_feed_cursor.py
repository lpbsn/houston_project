"""Opaque cursor pagination for the polymorphic Execution Feed.

Action cursors encode `as_of` so `is_overdue_rank` is stable across paginated
requests. If an action becomes overdue/non-overdue between page fetches, order
may diverge slightly until the feed is invalidated (mutations reset TanStack Query).
"""

from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from django.db.models import Q, QuerySet
from django.utils.dateparse import parse_datetime

from houston.actions.models import Action
from houston.actions.selectors import apply_execution_feed_sorting
from houston.checklists.models import ChecklistExecution
from houston.establishments.models import EstablishmentMembership

CHECKLIST_CURSOR_PART_COUNT = 4
ACTION_START_CURSOR_PART_COUNT = 2
ACTION_POSITIONAL_CURSOR_PART_COUNT = 9

NULL_DUE_AT_SENTINEL = ""


class ExecutionFeedCursorError(Exception):
    def __init__(self, detail: str = "Invalid cursor.") -> None:
        self.detail = detail
        super().__init__(detail)


ExecutionFeedCursorPhase = Literal["checklist", "action"]


@dataclass(frozen=True)
class ExecutionFeedCursor:
    phase: ExecutionFeedCursorPhase
    as_of: datetime | None = None
    action_start: bool = False
    last_activity_at: datetime | None = None
    created_at: datetime | None = None
    item_id: uuid.UUID | None = None
    is_overdue_rank: int | None = None
    requires_me_rank: int | None = None
    status_rank: int | None = None
    due_at: datetime | None = None


def _encode_cursor_payload(raw: str) -> str:
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor_payload(raw: str) -> str:
    padding = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(f"{raw}{padding}").decode()
    except (ValueError, UnicodeDecodeError) as exc:
        raise ExecutionFeedCursorError() from exc


def encode_checklist_cursor(execution: ChecklistExecution) -> str:
    raw = "|".join(
        [
            "0",
            execution.last_activity_at.isoformat(),
            execution.created_at.isoformat(),
            str(execution.id),
        ]
    )
    return _encode_cursor_payload(raw)


def encode_action_phase_start(*, as_of: datetime) -> str:
    raw = "|".join(["1", as_of.isoformat()])
    return _encode_cursor_payload(raw)


def encode_action_cursor(
    action: Action,
    *,
    membership: EstablishmentMembership,
    as_of: datetime,
) -> str:
    is_overdue_rank = int(getattr(action, "is_overdue_rank", 0))
    requires_me_rank = int(getattr(action, "requires_me_rank", 2))
    status_rank = int(getattr(action, "status_rank", 4))
    due_at_value = action.due_at.isoformat() if action.due_at is not None else NULL_DUE_AT_SENTINEL
    raw = "|".join(
        [
            "1",
            as_of.isoformat(),
            str(is_overdue_rank),
            str(requires_me_rank),
            str(status_rank),
            due_at_value,
            action.last_activity_at.isoformat(),
            action.created_at.isoformat(),
            str(action.id),
        ]
    )
    return _encode_cursor_payload(raw)


def parse_execution_feed_cursor(raw: str | None) -> ExecutionFeedCursor | None:
    if not raw:
        return None
    parts = _decode_cursor_payload(raw.strip()).split("|")
    if not parts:
        raise ExecutionFeedCursorError()
    phase_prefix = parts[0]
    if phase_prefix == "0":
        if len(parts) != CHECKLIST_CURSOR_PART_COUNT:
            raise ExecutionFeedCursorError()
        try:
            last_activity_at = parse_datetime(parts[1])
            created_at = parse_datetime(parts[2])
            item_id = uuid.UUID(parts[3])
        except (TypeError, ValueError) as exc:
            raise ExecutionFeedCursorError() from exc
        if last_activity_at is None or created_at is None:
            raise ExecutionFeedCursorError()
        return ExecutionFeedCursor(
            phase="checklist",
            last_activity_at=last_activity_at,
            created_at=created_at,
            item_id=item_id,
        )
    if phase_prefix == "1":
        if len(parts) == ACTION_START_CURSOR_PART_COUNT:
            try:
                as_of = parse_datetime(parts[1])
            except (TypeError, ValueError) as exc:
                raise ExecutionFeedCursorError() from exc
            if as_of is None:
                raise ExecutionFeedCursorError()
            return ExecutionFeedCursor(phase="action", as_of=as_of, action_start=True)
        if len(parts) == ACTION_POSITIONAL_CURSOR_PART_COUNT:
            try:
                as_of = parse_datetime(parts[1])
                is_overdue_rank = int(parts[2])
                requires_me_rank = int(parts[3])
                status_rank = int(parts[4])
                due_at = parse_datetime(parts[5]) if parts[5] != NULL_DUE_AT_SENTINEL else None
                last_activity_at = parse_datetime(parts[6])
                created_at = parse_datetime(parts[7])
                item_id = uuid.UUID(parts[8])
            except (TypeError, ValueError) as exc:
                raise ExecutionFeedCursorError() from exc
            if as_of is None or last_activity_at is None or created_at is None:
                raise ExecutionFeedCursorError()
            return ExecutionFeedCursor(
                phase="action",
                as_of=as_of,
                action_start=False,
                is_overdue_rank=is_overdue_rank,
                requires_me_rank=requires_me_rank,
                status_rank=status_rank,
                due_at=due_at,
                last_activity_at=last_activity_at,
                created_at=created_at,
                item_id=item_id,
            )
        raise ExecutionFeedCursorError()
    raise ExecutionFeedCursorError()


def _after_checklist_cursor_filter(cursor: ExecutionFeedCursor) -> Q:
    fields: list[tuple[str, str, object]] = [
        ("last_activity_at", "desc", cursor.last_activity_at),
        ("created_at", "desc", cursor.created_at),
        ("id", "desc", cursor.item_id),
    ]
    q = Q()
    prefix = Q()
    for name, direction, value in fields:
        if direction == "asc":
            q |= prefix & Q(**{f"{name}__gt": value})
        else:
            q |= prefix & Q(**{f"{name}__lt": value})
        prefix &= Q(**{name: value})
    return q


def apply_checklist_feed_cursor(
    queryset: QuerySet[ChecklistExecution],
    cursor: ExecutionFeedCursor,
) -> QuerySet[ChecklistExecution]:
    return queryset.filter(_after_checklist_cursor_filter(cursor))


def _after_action_cursor_filter(cursor: ExecutionFeedCursor) -> Q:
    fields: list[tuple[str, str, object]] = [
        ("is_overdue_rank", "desc", cursor.is_overdue_rank),
        ("requires_me_rank", "asc", cursor.requires_me_rank),
        ("status_rank", "asc", cursor.status_rank),
        ("due_at", "asc", cursor.due_at),
        ("last_activity_at", "desc", cursor.last_activity_at),
        ("created_at", "desc", cursor.created_at),
        ("id", "desc", cursor.item_id),
    ]
    q = Q()
    prefix = Q()
    for name, direction, value in fields:
        if direction == "asc":
            q |= prefix & Q(**{f"{name}__gt": value})
        else:
            q |= prefix & Q(**{f"{name}__lt": value})
        prefix &= Q(**{name: value})
    return q


def apply_action_feed_cursor(
    queryset: QuerySet[Action],
    cursor: ExecutionFeedCursor,
    *,
    membership: EstablishmentMembership,
) -> QuerySet[Action]:
    if cursor.as_of is None:
        raise ExecutionFeedCursorError()
    sorted_qs = apply_execution_feed_sorting(
        queryset,
        membership=membership,
        as_of=cursor.as_of,
    )
    if cursor.action_start:
        return sorted_qs
    if (
        cursor.is_overdue_rank is None
        or cursor.requires_me_rank is None
        or cursor.status_rank is None
        or cursor.last_activity_at is None
        or cursor.created_at is None
        or cursor.item_id is None
    ):
        raise ExecutionFeedCursorError()
    return sorted_qs.filter(_after_action_cursor_filter(cursor))
