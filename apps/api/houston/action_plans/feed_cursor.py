from __future__ import annotations

import base64
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils.dateparse import parse_datetime

from houston.action_plans.models import ActionPlanExecution

CURSOR_PART_COUNT = 3


class ActionPlanExecutionFeedCursorError(Exception):
    def __init__(self, detail: str = "Invalid cursor.") -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class ActionPlanExecutionFeedCursor:
    last_activity_at: datetime
    created_at: datetime
    execution_id: uuid.UUID


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
) -> str:
    raw = "|".join(
        [
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
        last_activity_at = parse_datetime(parts[0])
        created_at = parse_datetime(parts[1])
        execution_id = uuid.UUID(parts[2])
    except (TypeError, ValueError) as exc:
        raise ActionPlanExecutionFeedCursorError() from exc
    if last_activity_at is None or created_at is None:
        raise ActionPlanExecutionFeedCursorError()
    return ActionPlanExecutionFeedCursor(
        last_activity_at=last_activity_at,
        created_at=created_at,
        execution_id=execution_id,
    )


def apply_action_plan_execution_feed_cursor(
    queryset: QuerySet[ActionPlanExecution],
    cursor: ActionPlanExecutionFeedCursor,
) -> QuerySet[ActionPlanExecution]:
    return queryset.filter(
        Q(last_activity_at__lt=cursor.last_activity_at)
        | Q(
            last_activity_at=cursor.last_activity_at,
            created_at__lt=cursor.created_at,
        )
        | Q(
            last_activity_at=cursor.last_activity_at,
            created_at=cursor.created_at,
            id__lt=cursor.execution_id,
        )
    )
