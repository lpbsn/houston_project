from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db.models import (
    Case,
    DateTimeField,
    F,
    IntegerField,
    OrderBy,
    Q,
    QuerySet,
    UUIDField,
    Value,
    When,
)
from django.utils.dateparse import parse_datetime

from houston.action_plans.constants import (
    ACTIVE_EXECUTION_STATUSES,
    EXECUTION_FEED_CATEGORIES,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    ExecutionFeedCategory,
    ExecutionFeedScope,
    ExecutionFeedViewMode,
)
from houston.action_plans.models import ActionPlanExecution
from houston.establishments.membership_scope import membership_business_unit_scope_ids

FEED_CURSOR_VERSION = "v1"
FEED_CURSOR_COLLECTION_LIST = "L"
FEED_CURSOR_COLLECTION_PINS = "P"

DEADLINE_BUCKET_OVERDUE = 0
DEADLINE_BUCKET_UPCOMING = 1
DEADLINE_BUCKET_NO_DEADLINE = 2


class ActionPlanExecutionFeedCursorError(Exception):
    def __init__(self, detail: str = "Invalid cursor.", *, code: str = "validation_error") -> None:
        self.detail = detail
        self.code = code
        super().__init__(detail)


@dataclass(frozen=True)
class ActionPlanExecutionFeedCursor:
    as_of: datetime
    collection: str
    view_mode: ExecutionFeedViewMode
    category: ExecutionFeedCategory
    auth_context_hash: str
    category_rank: int
    deadline_bucket: int
    marked_done_at: datetime | None
    end_at: datetime | None
    last_activity_at: datetime
    created_at: datetime
    item_id: uuid.UUID


@dataclass(frozen=True)
class ActionPlanExecutionFeedPinCursor:
    as_of: datetime
    collection: str
    view_mode: ExecutionFeedViewMode
    category: ExecutionFeedCategory
    auth_context_hash: str
    pinned_at: datetime
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


def category_rank_for_execution(
    execution: ActionPlanExecution,
    as_of: datetime,
) -> int:
    if execution.status == EXECUTION_STATUS_PENDING_VALIDATION:
        return 0
    if execution.status == EXECUTION_STATUS_IN_PROGRESS:
        if execution.end_at is not None and execution.end_at < as_of:
            return 1
        if execution.end_at is not None:
            return 2
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


def sort_end_at_for_execution(execution: ActionPlanExecution) -> datetime | None:
    return execution.end_at


def action_plan_execution_feed_category_rank_case(as_of: datetime) -> Case:
    return Case(
        When(status=EXECUTION_STATUS_PENDING_VALIDATION, then=Value(0)),
        When(
            status=EXECUTION_STATUS_IN_PROGRESS,
            end_at__lt=as_of,
            then=Value(1),
        ),
        When(
            status=EXECUTION_STATUS_IN_PROGRESS,
            end_at__isnull=False,
            then=Value(2),
        ),
        When(status=EXECUTION_STATUS_IN_PROGRESS, end_at__isnull=True, then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )


def action_plan_execution_feed_sort_case_expressions(
    as_of: datetime,
) -> tuple[Case, Case, Case, Case, Case]:
    category_rank = action_plan_execution_feed_category_rank_case(as_of)
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
    feed_sort_marked_done_at = Case(
        When(
            status=EXECUTION_STATUS_PENDING_VALIDATION,
            then=F("marked_done_at"),
        ),
        default=Value(None, output_field=DateTimeField()),
        output_field=DateTimeField(),
    )
    feed_sort_pending_id = Case(
        When(
            status=EXECUTION_STATUS_PENDING_VALIDATION,
            then=F("id"),
        ),
        default=Value(None, output_field=UUIDField()),
        output_field=UUIDField(),
    )
    feed_sort_end_at = Case(
        When(
            status=EXECUTION_STATUS_PENDING_VALIDATION,
            then=Value(None, output_field=DateTimeField()),
        ),
        default=F("end_at"),
        output_field=DateTimeField(),
    )
    return (
        category_rank,
        deadline_bucket,
        feed_sort_marked_done_at,
        feed_sort_pending_id,
        feed_sort_end_at,
    )


def action_plan_execution_feed_order_by() -> tuple[object, ...]:
    return (
        "category_rank",
        OrderBy(F("feed_sort_marked_done_at"), nulls_last=True),
        OrderBy(F("feed_sort_pending_id"), nulls_last=True),
        "deadline_bucket",
        OrderBy(F("feed_sort_end_at"), nulls_last=True),
        "-last_activity_at",
        "-created_at",
        "-id",
    )


def action_plan_execution_feed_pin_order_by() -> tuple[object, ...]:
    return (
        OrderBy(F("feed_pinned_at"), nulls_last=True),
        "id",
    )


def _encode_cursor_payload(raw: str) -> str:
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor_payload(raw: str) -> str:
    padding = "=" * (-len(raw) % 4)
    try:
        return base64.urlsafe_b64decode(f"{raw}{padding}").decode()
    except (ValueError, UnicodeDecodeError) as exc:
        raise ActionPlanExecutionFeedCursorError() from exc


def action_plan_execution_feed_auth_context_hash(
    *,
    memberships,
    view_mode: ExecutionFeedViewMode,
    category: ExecutionFeedCategory,
    scope: ExecutionFeedScope,
) -> str:
    rows = []
    for membership in sorted(memberships, key=lambda item: str(item.id)):
        scope_ids = sorted(
            str(scope_id) for scope_id in membership_business_unit_scope_ids(membership)
        )
        rows.append(
            {
                "membership_id": str(membership.id),
                "establishment_id": str(membership.establishment_id),
                "role": membership.role,
                "status": membership.status,
                "scope_business_unit_ids": scope_ids,
            }
        )
    raw = json.dumps(
        {
            "category": category,
            "memberships": rows,
            "scope": scope,
            "view_mode": view_mode,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def encode_action_plan_execution_feed_cursor(
    execution: ActionPlanExecution,
    *,
    as_of: datetime,
    view_mode: ExecutionFeedViewMode,
    category: ExecutionFeedCategory,
    auth_context_hash: str,
) -> str:
    sort_end_at = sort_end_at_for_execution(execution)
    marked_done_at = (
        execution.marked_done_at
        if execution.status == EXECUTION_STATUS_PENDING_VALIDATION
        else None
    )
    payload = {
        "v": FEED_CURSOR_VERSION,
        "collection": FEED_CURSOR_COLLECTION_LIST,
        "as_of": as_of.isoformat(),
        "view_mode": view_mode,
        "category": category,
        "auth_context_hash": auth_context_hash,
        "category_rank": category_rank_for_execution(execution, as_of),
        "deadline_bucket": deadline_bucket_for_execution(execution, as_of),
        "marked_done_at": marked_done_at.isoformat() if marked_done_at else None,
        "end_at": sort_end_at.isoformat() if sort_end_at else None,
        "last_activity_at": execution.last_activity_at.isoformat(),
        "created_at": execution.created_at.isoformat(),
        "item_id": str(execution.id),
    }
    return _encode_cursor_payload(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
    )


def parse_action_plan_execution_feed_cursor(
    raw: str | None,
) -> ActionPlanExecutionFeedCursor | None:
    if not raw:
        return None
    try:
        payload = json.loads(_decode_cursor_payload(raw.strip()))
    except json.JSONDecodeError as exc:
        raise ActionPlanExecutionFeedCursorError() from exc
    if not isinstance(payload, dict) or payload.get("v") != FEED_CURSOR_VERSION:
        raise ActionPlanExecutionFeedCursorError()
    try:
        as_of = parse_datetime(payload["as_of"])
        collection = str(payload["collection"])
        view_mode = str(payload["view_mode"])
        category = str(payload["category"])
        auth_context_hash = str(payload["auth_context_hash"])
        category_rank = int(payload["category_rank"])
        deadline_bucket = int(payload["deadline_bucket"])
        marked_done_raw = payload.get("marked_done_at")
        marked_done_at = parse_datetime(marked_done_raw) if marked_done_raw else None
        end_raw = payload.get("end_at")
        end_at = parse_datetime(end_raw) if end_raw else None
        last_activity_at = parse_datetime(payload["last_activity_at"])
        created_at = parse_datetime(payload["created_at"])
        item_id = uuid.UUID(payload["item_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ActionPlanExecutionFeedCursorError() from exc
    if (
        as_of is None
        or collection != FEED_CURSOR_COLLECTION_LIST
        or view_mode not in {"personal", "general"}
        or category not in EXECUTION_FEED_CATEGORIES
        or last_activity_at is None
        or created_at is None
    ):
        raise ActionPlanExecutionFeedCursorError()
    return ActionPlanExecutionFeedCursor(
        as_of=as_of,
        collection=collection,
        view_mode=view_mode,  # type: ignore[arg-type]
        category=category,  # type: ignore[arg-type]
        auth_context_hash=auth_context_hash,
        category_rank=category_rank,
        deadline_bucket=deadline_bucket,
        marked_done_at=marked_done_at,
        end_at=end_at,
        created_at=created_at,
        item_id=item_id,
        last_activity_at=last_activity_at,
    )


def encode_action_plan_execution_feed_pin_cursor(
    execution: ActionPlanExecution,
    *,
    as_of: datetime,
    view_mode: ExecutionFeedViewMode,
    category: ExecutionFeedCategory,
    auth_context_hash: str,
) -> str:
    pinned_at = getattr(execution, "feed_pinned_at", None)
    if pinned_at is None:
        raise ValueError("Pinned execution cursor requires feed_pinned_at.")
    payload = {
        "v": FEED_CURSOR_VERSION,
        "collection": FEED_CURSOR_COLLECTION_PINS,
        "as_of": as_of.isoformat(),
        "view_mode": view_mode,
        "category": category,
        "auth_context_hash": auth_context_hash,
        "pinned_at": pinned_at.isoformat(),
        "item_id": str(execution.id),
    }
    return _encode_cursor_payload(
        json.dumps(payload, sort_keys=True, separators=(",", ":")),
    )


def parse_action_plan_execution_feed_pin_cursor(
    raw: str | None,
) -> ActionPlanExecutionFeedPinCursor | None:
    if not raw:
        return None
    try:
        payload = json.loads(_decode_cursor_payload(raw.strip()))
    except json.JSONDecodeError as exc:
        raise ActionPlanExecutionFeedCursorError() from exc
    if not isinstance(payload, dict) or payload.get("v") != FEED_CURSOR_VERSION:
        raise ActionPlanExecutionFeedCursorError()
    try:
        as_of = parse_datetime(payload["as_of"])
        collection = str(payload["collection"])
        view_mode = str(payload["view_mode"])
        category = str(payload["category"])
        auth_context_hash = str(payload["auth_context_hash"])
        pinned_at = parse_datetime(payload["pinned_at"])
        item_id = uuid.UUID(payload["item_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ActionPlanExecutionFeedCursorError() from exc
    if (
        as_of is None
        or collection != FEED_CURSOR_COLLECTION_PINS
        or view_mode not in {"personal", "general"}
        or category not in EXECUTION_FEED_CATEGORIES
        or pinned_at is None
    ):
        raise ActionPlanExecutionFeedCursorError()
    return ActionPlanExecutionFeedPinCursor(
        as_of=as_of,
        collection=collection,
        view_mode=view_mode,  # type: ignore[arg-type]
        category=category,  # type: ignore[arg-type]
        auth_context_hash=auth_context_hash,
        pinned_at=pinned_at,
        item_id=item_id,
    )


def validate_action_plan_execution_feed_cursor_context(
    cursor: ActionPlanExecutionFeedCursor | ActionPlanExecutionFeedPinCursor,
    *,
    view_mode: ExecutionFeedViewMode,
    category: ExecutionFeedCategory,
    auth_context_hash: str,
) -> None:
    if (
        cursor.view_mode != view_mode
        or cursor.category != category
        or cursor.auth_context_hash != auth_context_hash
    ):
        raise ActionPlanExecutionFeedCursorError(
            "cursor_context_mismatch",
            code="cursor_context_mismatch",
        )


def _after_cursor_filter(cursor: ActionPlanExecutionFeedCursor) -> Q:
    q = Q()
    prefix = Q()

    q |= prefix & Q(category_rank__gt=cursor.category_rank)
    prefix &= Q(category_rank=cursor.category_rank)

    if cursor.marked_done_at is not None:
        q |= prefix & (
            Q(feed_sort_marked_done_at__gt=cursor.marked_done_at)
            | Q(feed_sort_marked_done_at__isnull=True)
        )
        prefix &= Q(feed_sort_marked_done_at=cursor.marked_done_at)
    else:
        prefix &= Q(feed_sort_marked_done_at__isnull=True)

    if cursor.category_rank == 0:
        q |= prefix & Q(feed_sort_pending_id__gt=cursor.item_id)
        return q
    prefix &= Q(feed_sort_pending_id__isnull=True)

    q |= prefix & Q(deadline_bucket__gt=cursor.deadline_bucket)
    prefix &= Q(deadline_bucket=cursor.deadline_bucket)

    if cursor.end_at is not None:
        q |= prefix & (
            Q(feed_sort_end_at__gt=cursor.end_at) | Q(feed_sort_end_at__isnull=True)
        )
        prefix &= Q(feed_sort_end_at=cursor.end_at)
    else:
        prefix &= Q(feed_sort_end_at__isnull=True)

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
    membership=None,
    memberships=None,
) -> QuerySet[ActionPlanExecution]:
    from houston.action_plans.selectors import (
        annotate_action_plan_execution_feed_sort_keys,
    )

    return annotate_action_plan_execution_feed_sort_keys(
        queryset,
        membership=membership,
        memberships=memberships,
        as_of=cursor.as_of,
    ).filter(_after_cursor_filter(cursor)).order_by(
        *action_plan_execution_feed_order_by(),
    )


def apply_action_plan_execution_feed_pin_cursor(
    queryset: QuerySet[ActionPlanExecution],
    cursor: ActionPlanExecutionFeedPinCursor,
) -> QuerySet[ActionPlanExecution]:
    return queryset.filter(
        Q(feed_pinned_at__gt=cursor.pinned_at)
        | Q(feed_pinned_at=cursor.pinned_at, id__gt=cursor.item_id),
    ).order_by(*action_plan_execution_feed_pin_order_by())
