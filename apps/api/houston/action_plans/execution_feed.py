from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from django.utils import timezone

from houston.action_plans.constants import (
    ExecutionFeedCategory,
    ExecutionFeedViewMode,
)
from houston.action_plans.feed_cursor import (
    ActionPlanExecutionFeedCursor,
    ActionPlanExecutionFeedPinCursor,
    action_plan_execution_feed_auth_context_hash,
    apply_action_plan_execution_feed_cursor,
    apply_action_plan_execution_feed_pin_cursor,
    encode_action_plan_execution_feed_cursor,
    encode_action_plan_execution_feed_pin_cursor,
    validate_action_plan_execution_feed_cursor_context,
)
from houston.action_plans.feed_pin_services import ACTION_PLAN_EXECUTION_FEED_PIN_LIMIT
from houston.action_plans.lifecycle_promotion import ensure_execution_lifecycle_for_read
from houston.action_plans.materialization import (
    ensure_visible_action_plan_executions_materialized,
)
from houston.action_plans.membership_read import prepare_execution_read_membership
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.selectors import (
    action_plan_execution_feed_list_queryset,
    action_plan_execution_feed_pins_queryset,
    action_plan_execution_feed_queryset,
    action_plan_execution_feed_section_counts,
    filter_action_plan_execution_feed_category,
    scheduled_executions_next_queryset,
    scheduled_executions_upcoming_queryset,
)
from houston.establishments.models import EstablishmentMembership

logger = logging.getLogger(__name__)

EMPTY_SECTION_COUNTS = {
    "pinned": 0,
    "pending_validation": 0,
    "overdue": 0,
    "in_progress": 0,
}


@dataclass(frozen=True)
class ScheduledExecutionSummary:
    id: UUID
    start_at: datetime
    title: str


@dataclass(frozen=True)
class ActionPlanExecutionFeedPage:
    items: list[ActionPlanExecution]
    has_more: bool
    next_cursor: str | None
    as_of: datetime
    pins: list[ActionPlanExecution] | None = None
    scheduled_count: int | None = None
    scheduled_next: ScheduledExecutionSummary | None = None
    section_counts: dict[str, int] | None = None


@dataclass(frozen=True)
class ActionPlanExecutionFeedPinsPage:
    items: list[ActionPlanExecution]
    has_more: bool
    next_cursor: str | None
    as_of: datetime


def _log_read_path_materialization(
    *,
    count: int,
    view_mode: ExecutionFeedViewMode,
    membership: EstablishmentMembership,
) -> None:
    if count <= 0:
        return
    logger.info(
        "action_plan_execution_feed.read_materialized",
        extra={
            "count": count,
            "establishment_id": str(membership.establishment_id),
            "membership_id": str(membership.id),
            "view_mode": view_mode,
        },
    )


def _scheduled_summary_from_execution(
    execution: ActionPlanExecution | None,
) -> ScheduledExecutionSummary | None:
    if execution is None or execution.start_at is None:
        return None
    return ScheduledExecutionSummary(
        id=execution.id,
        start_at=execution.start_at,
        title=execution.title,
    )


def build_action_plan_execution_feed_page(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
    category: ExecutionFeedCategory,
    page_size: int,
    cursor: ActionPlanExecutionFeedCursor | None = None,
) -> ActionPlanExecutionFeedPage:
    membership = prepare_execution_read_membership(membership)
    materialized_count = ensure_visible_action_plan_executions_materialized(
        membership=membership,
        view_mode=view_mode,
    )
    _log_read_path_materialization(
        count=materialized_count,
        view_mode=view_mode,
        membership=membership,
    )
    ensure_execution_lifecycle_for_read(establishment_id=membership.establishment_id)

    queryset = action_plan_execution_feed_queryset(
        membership=membership,
        view_mode=view_mode,
    )
    auth_context_hash = action_plan_execution_feed_auth_context_hash(
        memberships=[membership],
        view_mode=view_mode,
        category=category,
        scope="establishment",
    )
    if cursor is not None:
        validate_action_plan_execution_feed_cursor_context(
            cursor,
            view_mode=view_mode,
            category=category,
            auth_context_hash=auth_context_hash,
        )
        as_of = cursor.as_of
        sorted_qs = apply_action_plan_execution_feed_cursor(
            queryset,
            cursor,
            membership=membership,
        )
        sorted_qs = filter_action_plan_execution_feed_category(
            sorted_qs.filter(is_feed_pinned=False),
            category=category,
        )
    else:
        as_of = timezone.now()
        sorted_qs = action_plan_execution_feed_list_queryset(
            queryset,
            membership=membership,
            as_of=as_of,
            category=category,
        )

    candidates = list(sorted_qs[: page_size + 1])
    has_more = len(candidates) > page_size
    served = candidates[:page_size]
    next_cursor = None
    if has_more and served:
        next_cursor = encode_action_plan_execution_feed_cursor(
            served[-1],
            as_of=as_of,
            view_mode=view_mode,
            category=category,
            auth_context_hash=auth_context_hash,
        )

    if cursor is not None:
        return ActionPlanExecutionFeedPage(
            items=served,
            has_more=has_more,
            next_cursor=next_cursor,
            as_of=as_of,
        )

    section_counts = action_plan_execution_feed_section_counts(
        queryset,
        membership=membership,
        as_of=as_of,
        category=category,
    )
    pins = list(
        action_plan_execution_feed_pins_queryset(
            queryset,
            membership=membership,
            as_of=as_of,
            category=category,
        )[:ACTION_PLAN_EXECUTION_FEED_PIN_LIMIT]
    )

    upcoming_qs = scheduled_executions_upcoming_queryset(
        membership=membership,
        view_mode=view_mode,
    )
    scheduled_count = upcoming_qs.count()
    scheduled_next = _scheduled_summary_from_execution(
        scheduled_executions_next_queryset(
            membership=membership,
            view_mode=view_mode,
        ).first()
    )
    return ActionPlanExecutionFeedPage(
        items=served,
        pins=pins,
        has_more=has_more,
        next_cursor=next_cursor,
        as_of=as_of,
        scheduled_count=scheduled_count,
        scheduled_next=scheduled_next,
        section_counts=section_counts,
    )


def build_cross_action_plan_execution_feed_page(
    *,
    memberships: list[EstablishmentMembership],
    view_mode: ExecutionFeedViewMode,
    category: ExecutionFeedCategory,
    page_size: int,
    cursor: ActionPlanExecutionFeedCursor | None = None,
) -> ActionPlanExecutionFeedPage:
    if not memberships:
        as_of = timezone.now()
        return ActionPlanExecutionFeedPage(
            items=[],
            has_more=False,
            next_cursor=None,
            as_of=as_of,
            scheduled_count=0 if cursor is None else None,
            scheduled_next=None,
            section_counts=dict(EMPTY_SECTION_COUNTS) if cursor is None else None,
        )

    combined = None
    prepared_memberships: list[EstablishmentMembership] = []
    for membership in memberships:
        prepared = prepare_execution_read_membership(membership)
        prepared_memberships.append(prepared)
        materialized_count = ensure_visible_action_plan_executions_materialized(
            membership=prepared,
            view_mode=view_mode,
        )
        _log_read_path_materialization(
            count=materialized_count,
            view_mode=view_mode,
            membership=prepared,
        )
        ensure_execution_lifecycle_for_read(establishment_id=prepared.establishment_id)
        queryset = action_plan_execution_feed_queryset(
            membership=prepared,
            view_mode=view_mode,
        )
        combined = queryset if combined is None else combined | queryset

    if cursor is not None:
        auth_context_hash = action_plan_execution_feed_auth_context_hash(
            memberships=prepared_memberships,
            view_mode=view_mode,
            category=category,
            scope="cross",
        )
        validate_action_plan_execution_feed_cursor_context(
            cursor,
            view_mode=view_mode,
            category=category,
            auth_context_hash=auth_context_hash,
        )
        as_of = cursor.as_of
        sorted_qs = apply_action_plan_execution_feed_cursor(
            combined,
            cursor,
            memberships=prepared_memberships,
        )
        sorted_qs = filter_action_plan_execution_feed_category(
            sorted_qs.filter(is_feed_pinned=False),
            category=category,
        )
    else:
        as_of = timezone.now()
        auth_context_hash = action_plan_execution_feed_auth_context_hash(
            memberships=prepared_memberships,
            view_mode=view_mode,
            category=category,
            scope="cross",
        )
        sorted_qs = action_plan_execution_feed_list_queryset(
            combined,
            memberships=prepared_memberships,
            as_of=as_of,
            category=category,
        )

    candidates = list(sorted_qs[: page_size + 1])
    has_more = len(candidates) > page_size
    served = candidates[:page_size]
    next_cursor = None
    if has_more and served:
        next_cursor = encode_action_plan_execution_feed_cursor(
            served[-1],
            as_of=as_of,
            view_mode=view_mode,
            category=category,
            auth_context_hash=auth_context_hash,
        )

    if cursor is not None:
        return ActionPlanExecutionFeedPage(
            items=served,
            has_more=has_more,
            next_cursor=next_cursor,
            as_of=as_of,
        )

    section_counts = action_plan_execution_feed_section_counts(
        combined,
        memberships=prepared_memberships,
        as_of=as_of,
        category=category,
    )
    scheduled_count = 0
    scheduled_next_candidates = []
    for prepared in prepared_memberships:
        upcoming_qs = scheduled_executions_upcoming_queryset(
            membership=prepared,
            view_mode=view_mode,
        )
        scheduled_count += upcoming_qs.count()
        next_execution = scheduled_executions_next_queryset(
            membership=prepared,
            view_mode=view_mode,
        ).first()
        if next_execution is not None:
            scheduled_next_candidates.append(next_execution)
    scheduled_next_candidates.sort(key=lambda execution: (execution.start_at, execution.id))
    scheduled_next = _scheduled_summary_from_execution(
        scheduled_next_candidates[0] if scheduled_next_candidates else None,
    )
    return ActionPlanExecutionFeedPage(
        items=served,
        has_more=has_more,
        next_cursor=next_cursor,
        as_of=as_of,
        scheduled_count=scheduled_count,
        scheduled_next=scheduled_next,
        section_counts=section_counts,
    )


def build_cross_action_plan_execution_feed_pins_page(
    *,
    memberships: list[EstablishmentMembership],
    view_mode: ExecutionFeedViewMode,
    category: ExecutionFeedCategory,
    page_size: int,
    cursor: ActionPlanExecutionFeedPinCursor | None = None,
) -> ActionPlanExecutionFeedPinsPage:
    if not memberships:
        return ActionPlanExecutionFeedPinsPage(
            items=[],
            has_more=False,
            next_cursor=None,
            as_of=timezone.now(),
        )

    combined = None
    prepared_memberships: list[EstablishmentMembership] = []
    for membership in memberships:
        prepared = prepare_execution_read_membership(membership)
        prepared_memberships.append(prepared)
        materialized_count = ensure_visible_action_plan_executions_materialized(
            membership=prepared,
            view_mode=view_mode,
        )
        _log_read_path_materialization(
            count=materialized_count,
            view_mode=view_mode,
            membership=prepared,
        )
        ensure_execution_lifecycle_for_read(establishment_id=prepared.establishment_id)
        queryset = action_plan_execution_feed_queryset(
            membership=prepared,
            view_mode=view_mode,
        )
        combined = queryset if combined is None else combined | queryset

    auth_context_hash = action_plan_execution_feed_auth_context_hash(
        memberships=prepared_memberships,
        view_mode=view_mode,
        category=category,
        scope="cross",
    )
    if cursor is not None:
        validate_action_plan_execution_feed_cursor_context(
            cursor,
            view_mode=view_mode,
            category=category,
            auth_context_hash=auth_context_hash,
        )
        as_of = cursor.as_of
    else:
        as_of = timezone.now()

    pins_qs = action_plan_execution_feed_pins_queryset(
        combined,
        memberships=prepared_memberships,
        as_of=as_of,
        category=category,
    )
    if cursor is not None:
        pins_qs = apply_action_plan_execution_feed_pin_cursor(pins_qs, cursor)

    candidates = list(pins_qs[: page_size + 1])
    has_more = len(candidates) > page_size
    served = candidates[:page_size]
    next_cursor = None
    if has_more and served:
        next_cursor = encode_action_plan_execution_feed_pin_cursor(
            served[-1],
            as_of=as_of,
            view_mode=view_mode,
            category=category,
            auth_context_hash=auth_context_hash,
        )
    return ActionPlanExecutionFeedPinsPage(
        items=served,
        has_more=has_more,
        next_cursor=next_cursor,
        as_of=as_of,
    )
