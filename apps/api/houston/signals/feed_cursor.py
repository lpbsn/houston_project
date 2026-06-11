from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django.utils.dateparse import parse_datetime

from houston.signals.models import Signal

CURSOR_PART_COUNT = 7


class SignalFeedCursorError(Exception):
    def __init__(self, detail: str = "Invalid cursor.") -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class SignalFeedCursor:
    status_group_rank: int
    is_pinned: bool
    urgency_order: int
    status_rank: int
    last_activity_at: datetime
    created_at: datetime
    signal_id: uuid.UUID


def feed_sort_case_expressions() -> tuple[Case, Case, Case]:
    status_group_rank = Case(
        When(status__in=[Signal.Status.OPEN, Signal.Status.IN_PROGRESS], then=Value(0)),
        When(status=Signal.Status.RESOLVED, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    urgency_order = Case(
        When(urgency=Signal.Urgency.HIGH, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )
    status_rank = Case(
        When(status=Signal.Status.OPEN, then=Value(0)),
        When(status=Signal.Status.IN_PROGRESS, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    return status_group_rank, urgency_order, status_rank


def status_group_rank_for_signal(signal: Signal) -> int:
    if signal.status in {Signal.Status.OPEN, Signal.Status.IN_PROGRESS}:
        return 0
    if signal.status == Signal.Status.RESOLVED:
        return 1
    return 2


def urgency_order_for_signal(signal: Signal) -> int:
    return 0 if signal.urgency == Signal.Urgency.HIGH else 1


def status_rank_for_signal(signal: Signal) -> int:
    if signal.status == Signal.Status.OPEN:
        return 0
    if signal.status == Signal.Status.IN_PROGRESS:
        return 1
    return 2


def encode_signal_feed_cursor(signal: Signal) -> str:
    raw = "|".join(
        [
            str(status_group_rank_for_signal(signal)),
            "1" if signal.is_pinned else "0",
            str(urgency_order_for_signal(signal)),
            str(status_rank_for_signal(signal)),
            signal.last_activity_at.isoformat(),
            signal.created_at.isoformat(),
            str(signal.id),
        ]
    )
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor_payload(raw: str) -> str:
    padding = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(f"{raw}{padding}").decode()
    except (ValueError, UnicodeDecodeError) as exc:
        raise SignalFeedCursorError() from exc


def parse_signal_feed_cursor(raw: str | None) -> SignalFeedCursor | None:
    if not raw:
        return None
    parts = _decode_cursor_payload(raw.strip()).split("|")
    if len(parts) != CURSOR_PART_COUNT:
        raise SignalFeedCursorError()
    try:
        status_group_rank = int(parts[0])
        is_pinned = parts[1] == "1"
        urgency_order = int(parts[2])
        status_rank = int(parts[3])
        last_activity_at = parse_datetime(parts[4])
        created_at = parse_datetime(parts[5])
        signal_id = uuid.UUID(parts[6])
    except (TypeError, ValueError) as exc:
        raise SignalFeedCursorError() from exc
    if last_activity_at is None or created_at is None:
        raise SignalFeedCursorError()
    return SignalFeedCursor(
        status_group_rank=status_group_rank,
        is_pinned=is_pinned,
        urgency_order=urgency_order,
        status_rank=status_rank,
        last_activity_at=last_activity_at,
        created_at=created_at,
        signal_id=signal_id,
    )


def _after_cursor_filter(cursor: SignalFeedCursor) -> Q:
    fields: list[tuple[str, str, object]] = [
        ("status_group_rank", "asc", cursor.status_group_rank),
        ("is_pinned", "desc", cursor.is_pinned),
        ("urgency_order", "asc", cursor.urgency_order),
        ("status_rank", "asc", cursor.status_rank),
        ("last_activity_at", "desc", cursor.last_activity_at),
        ("created_at", "desc", cursor.created_at),
        ("id", "desc", cursor.signal_id),
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


def apply_signal_feed_cursor(
    queryset: QuerySet[Signal],
    cursor: SignalFeedCursor,
) -> QuerySet[Signal]:
    status_group_rank, urgency_order, status_rank = feed_sort_case_expressions()
    return queryset.annotate(
        status_group_rank=status_group_rank,
        urgency_order=urgency_order,
        status_rank=status_rank,
    ).filter(_after_cursor_filter(cursor))
