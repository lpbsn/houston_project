from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Case, F, IntegerField, OrderBy, Q, QuerySet, Value, When
from django.utils.dateparse import parse_datetime

from houston.action_plans.constants import (
    ACTIVE_EXECUTION_STATUSES,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
)
from houston.action_plans.models import ActionPlanExecution

CURSOR_PART_COUNT = 9

DEADLINE_BUCKET_OVERDUE = 0
DEADLINE_BUCKET_UPCOMING = 1
DEADLINE_BUCKET_NO_DEADLINE = 2


class ActionPlanExecutionFeedCursorError(Exception):
    def __init__(self, detail: str = "Invalid cursor.") -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class ActionPlanExecutionFeedCursor:
    as_of: datetime
    is_feed_pinned: bool
    feed_pinned_at: datetime | None
    status_rank: int
    deadline_bucket: int
    end_at: datetime | None
    last_activity_at: datetime
    created_at: datetime
    item_id: uuid.UUID


def execution_deadline_bucket(
    *,
    end_at: datetime | None,
    status: str,
    as_of: datetime,
) -> int:
    if end_at is None:
        return DEADLINE_BUCKET_NO_DEADLINE
    if status in ACTIVE_EXECUTION_STATUSES and end_at < as_of:
        return DEADLINE_BUCKET_OVERDUE
    return DEADLINE_BUCKET_UPCOMING


def status_rank_for_execution(status: str) -> int:
    if status == EXECUTION_STATUS_PENDING_VALIDATION:
        return 0
    if status == EXECUTION_STATUS_IN_PROGRESS:
        return 1
    if status == EXECUTION_STATUS_DONE:
        return 2
    if status == EXECUTION_STATUS_CANCELED:
        return 3
    return 4


def deadline_bucket_for_execution(
    execution: ActionPlanExecution,
    as_of: datetime,
) -> int:
    return execution_deadline_bucket(
        end_at=execution.end_at,
        status=execution.status,
        as_of=as_of,
    )


def action_plan_execution_feed_sort_case_expressions(
    as_of: datetime,
) -> tuple[Case, Case]:
    status_rank = Case(
        When(status=EXECUTION_STATUS_PENDING_VALIDATION, then=Value(0)),
        When(status=EXECUTION_STATUS_IN_PROGRESS, then=Value(1)),
        When(status=EXECUTION_STATUS_DONE, then=Value(2)),
        When(status=EXECUTION_STATUS_CANCELED, then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )
    deadline_bucket = Case(
        When(end_at__isnull=True, then=Value(DEADLINE_BUCKET_NO_DEADLINE)),
        When(
            end_at__lt=as_of,
            status__in=ACTIVE_EXECUTION_STATUSES,
            then=Value(DEADLINE_BUCKET_OVERDUE),
        ),
        default=Value(DEADLINE_BUCKET_UPCOMING),
        output_field=IntegerField(),
    )
    return status_rank, deadline_bucket


def action_plan_execution_feed_order_by() -> tuple[object, ...]:
    return (
        "-is_feed_pinned",
        OrderBy(F("feed_pinned_at"), nulls_last=True),
        "status_rank",
        "deadline_bucket",
        OrderBy(F("end_at"), nulls_last=True),
        "-last_activity_at",
        "-created_at",
        "-id",
    )


def _encode_cursor_payload(raw: str) -> str:
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor_payload(raw: str) -> str:
    padding = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(f"{raw}{padding}").decode()
    except (ValueError, UnicodeDecodeError) as exc:
        raise ActionPlanExecutionFeedCursorError() from exc


def encode_action_plan_execution_feed_cursor(
    execution: ActionPlanExecution,
    *,
    as_of: datetime,
) -> str:
    is_feed_pinned = bool(getattr(execution, "is_feed_pinned", False))
    feed_pinned_at = getattr(execution, "feed_pinned_at", None)
    end_at_part = "" if execution.end_at is None else execution.end_at.isoformat()
    pinned_at_part = "" if feed_pinned_at is None else feed_pinned_at.isoformat()
    raw = "|".join(
        [
            as_of.isoformat(),
            "1" if is_feed_pinned else "0",
            pinned_at_part,
            str(status_rank_for_execution(execution.status)),
            str(deadline_bucket_for_execution(execution, as_of)),
            end_at_part,
            execution.last_activity_at.isoformat(),
            execution.created_at.isoformat(),
            str(execution.id),
        ]
    )
    return _encode_cursor_payload(raw)


def parse_action_plan_execution_feed_cursor(
    raw: str | None,
) -> ActionPlanExecutionFeedCursor | None:
    if not raw:
        return None
    parts = _decode_cursor_payload(raw.strip()).split("|")
    if len(parts) != CURSOR_PART_COUNT:
        raise ActionPlanExecutionFeedCursorError()
    try:
        as_of = parse_datetime(parts[0])
        is_feed_pinned = parts[1] == "1"
        feed_pinned_at = parse_datetime(parts[2]) if parts[2] else None
        status_rank = int(parts[3])
        deadline_bucket = int(parts[4])
        end_at = parse_datetime(parts[5]) if parts[5] else None
        last_activity_at = parse_datetime(parts[6])
        created_at = parse_datetime(parts[7])
        item_id = uuid.UUID(parts[8])
    except (TypeError, ValueError) as exc:
        raise ActionPlanExecutionFeedCursorError() from exc
    if as_of is None or last_activity_at is None or created_at is None:
        raise ActionPlanExecutionFeedCursorError()
    return ActionPlanExecutionFeedCursor(
        as_of=as_of,
        is_feed_pinned=is_feed_pinned,
        feed_pinned_at=feed_pinned_at,
        status_rank=status_rank,
        deadline_bucket=deadline_bucket,
        end_at=end_at,
        created_at=created_at,
        item_id=item_id,
        last_activity_at=last_activity_at,
    )


def _after_cursor_filter(cursor: ActionPlanExecutionFeedCursor) -> Q:
    q = Q()
    prefix = Q()

    q |= prefix & Q(is_feed_pinned__lt=cursor.is_feed_pinned)
    prefix &= Q(is_feed_pinned=cursor.is_feed_pinned)

    if cursor.is_feed_pinned:
        if cursor.feed_pinned_at is not None:
            q |= prefix & Q(feed_pinned_at__gt=cursor.feed_pinned_at)
            prefix &= Q(feed_pinned_at=cursor.feed_pinned_at)
        else:
            prefix &= Q(feed_pinned_at__isnull=True)

    q |= prefix & Q(status_rank__gt=cursor.status_rank)
    prefix &= Q(status_rank=cursor.status_rank)

    q |= prefix & Q(deadline_bucket__gt=cursor.deadline_bucket)
    prefix &= Q(deadline_bucket=cursor.deadline_bucket)

    if cursor.end_at is not None:
        q |= prefix & (Q(end_at__gt=cursor.end_at) | Q(end_at__isnull=True))
        prefix &= Q(end_at=cursor.end_at)
    else:
        prefix &= Q(end_at__isnull=True)

    q |= prefix & Q(last_activity_at__lt=cursor.last_activity_at)
    prefix &= Q(last_activity_at=cursor.last_activity_at)

    q |= prefix & Q(created_at__lt=cursor.created_at)
    prefix &= Q(created_at=cursor.created_at)

    q |= prefix & Q(id__lt=cursor.item_id)
    return q


def apply_action_plan_execution_feed_cursor(
    queryset: QuerySet[ActionPlanExecution],
    cursor: ActionPlanExecutionFeedCursor,
    *,
    membership,
) -> QuerySet[ActionPlanExecution]:
    from houston.action_plans.selectors import annotate_action_plan_execution_feed_pins

    status_rank, deadline_bucket = action_plan_execution_feed_sort_case_expressions(
        cursor.as_of,
    )
    return annotate_action_plan_execution_feed_pins(
        queryset,
        membership=membership,
    ).annotate(
        status_rank=status_rank,
        deadline_bucket=deadline_bucket,
    ).filter(_after_cursor_filter(cursor)).order_by(
        *action_plan_execution_feed_order_by(),
    )
