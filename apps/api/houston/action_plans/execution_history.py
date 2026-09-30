from __future__ import annotations

from dataclasses import dataclass

from django.db.models import (
    Case,
    DateTimeField,
    F,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
    When,
)
from django.db.models.functions import Coalesce

from houston.accounts.display import membership_display_name
from houston.action_plans.constants import (
    CANCEL_ORIGIN_MANUAL,
    CANCEL_ORIGIN_SCHEDULE_SYNC,
    EXECUTION_LIFECYCLE_EVENT_CANCELED,
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    TERMINAL_EXECUTION_STATUSES,
)
from houston.action_plans.feed_cursor import action_plan_execution_feed_auth_context_hash
from houston.action_plans.history_cursor import (
    ExecutionHistoryCursor,
    apply_execution_history_cursor,
    encode_execution_history_cursor,
    execution_history_context_hash,
)
from houston.action_plans.models import (
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionLifecycleEvent,
    ActionPlanExecutionReview,
    ActionPlanExecutionTask,
)
from houston.action_plans.selectors import (
    action_plan_execution_general_feed_visibility_q,
    action_plan_execution_personal_feed_q,
)
from houston.core.civil_time import CivilWindow
from houston.establishments.models import EstablishmentMembership

_EXECUTION_HISTORY_SELECT_RELATED = (
    "establishment",
    "pilot_business_unit",
    "pilot_business_unit__catalog_business_unit",
    "created_by__user",
    "validated_by_membership__user",
    "marked_done_by_membership__user",
    "canceled_by_membership__user",
)
_EXECUTION_HISTORY_CARD_PREFETCH = (
    Prefetch(
        "assignees",
        queryset=ActionPlanAssignee.objects.select_related(
            "membership__user",
            "execution_team__business_unit",
            "execution_team__business_unit__catalog_business_unit",
        ),
    ),
    Prefetch(
        "task_executions",
        queryset=ActionPlanExecutionTask.objects.select_related(
            "execution_team__business_unit",
            "execution_team__business_unit__catalog_business_unit",
        ),
    ),
    Prefetch(
        "reviews",
        queryset=ActionPlanExecutionReview.objects.filter(is_active=True),
        to_attr="_prefetched_active_reviews",
    ),
)


@dataclass(frozen=True)
class ExecutionHistoryPage:
    items: list[ActionPlanExecution]
    has_more: bool
    next_cursor: str | None
    undated_count: int | None


def execution_history_visibility_q(
    *,
    membership: EstablishmentMembership,
    view_mode: str,
) -> Q:
    if view_mode == "personal":
        visible = action_plan_execution_personal_feed_q(membership=membership)
    else:
        visible = action_plan_execution_general_feed_visibility_q(membership=membership)
    return visible & Q(status__in=TERMINAL_EXECUTION_STATUSES)


def _latest_event_subquery(event_types: tuple[str, ...]) -> Subquery:
    return Subquery(
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution_id=OuterRef("pk"),
            event_type__in=event_types,
        )
        .order_by("-occurred_at", "-id")
        .values("occurred_at")[:1],
        output_field=DateTimeField(),
    )


def annotate_execution_terminal_at(
    queryset: QuerySet[ActionPlanExecution],
) -> QuerySet[ActionPlanExecution]:
    return queryset.annotate(
        terminal_at=Case(
            When(
                status=EXECUTION_STATUS_CANCELED,
                then=Coalesce(
                    F("canceled_at"),
                    _latest_event_subquery((EXECUTION_LIFECYCLE_EVENT_CANCELED,)),
                ),
            ),
            When(
                status=EXECUTION_STATUS_DONE,
                validated_at__isnull=False,
                then=F("validated_at"),
            ),
            When(
                status=EXECUTION_STATUS_DONE,
                requires_validation=False,
                marked_done_at__isnull=False,
                then=F("marked_done_at"),
            ),
            When(
                status=EXECUTION_STATUS_DONE,
                requires_validation=True,
                then=_latest_event_subquery((EXECUTION_LIFECYCLE_EVENT_VALIDATED,)),
            ),
            When(
                status=EXECUTION_STATUS_DONE,
                requires_validation=False,
                then=_latest_event_subquery((EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,)),
            ),
            default=Value(None),
            output_field=DateTimeField(),
        )
    )


def execution_history_queryset(
    *,
    memberships: list[EstablishmentMembership],
    view_mode: str,
) -> QuerySet[ActionPlanExecution]:
    if not memberships:
        return annotate_execution_terminal_at(ActionPlanExecution.objects.none())
    visibility = Q()
    for membership in memberships:
        visibility |= execution_history_visibility_q(membership=membership, view_mode=view_mode)
    visible_ids = (
        ActionPlanExecution.objects.filter(visibility)
        .order_by()
        .values("id")
        .distinct()
    )
    return annotate_execution_terminal_at(
        ActionPlanExecution.objects.filter(id__in=Subquery(visible_ids))
    )


def _hydrate_execution_history_items(rows: list[dict]) -> list[ActionPlanExecution]:
    if not rows:
        return []
    executions_by_id = {
        execution.id: execution
        for execution in (
            ActionPlanExecution.objects.filter(id__in=[row["id"] for row in rows])
            .select_related(*_EXECUTION_HISTORY_SELECT_RELATED)
            .prefetch_related(*_EXECUTION_HISTORY_CARD_PREFETCH)
        )
    }
    items = []
    for row in rows:
        execution = executions_by_id[row["id"]]
        execution.terminal_at = row["terminal_at"]
        items.append(execution)
    return items


def execution_terminal_date_source(execution: ActionPlanExecution) -> str:
    if execution.status == EXECUTION_STATUS_CANCELED and execution.canceled_at is not None:
        return "field"
    if execution.status == EXECUTION_STATUS_DONE:
        if execution.validated_at is not None:
            return "field"
        if not execution.requires_validation and execution.marked_done_at is not None:
            return "field"
    if getattr(execution, "terminal_at", None) is not None:
        return "event"
    return "unknown"


def execution_termination(execution: ActionPlanExecution) -> tuple[str, str | None]:
    """Path from stored origin. Manual without an actor stays unknown."""
    if execution.status == EXECUTION_STATUS_CANCELED:
        actor = execution.canceled_by_membership
        if execution.cancel_origin == CANCEL_ORIGIN_MANUAL and actor is None:
            return "unknown", None
        if execution.cancel_origin == CANCEL_ORIGIN_SCHEDULE_SYNC:
            return CANCEL_ORIGIN_SCHEDULE_SYNC, membership_display_name(actor)
        if execution.cancel_origin == CANCEL_ORIGIN_MANUAL and actor is not None:
            return CANCEL_ORIGIN_MANUAL, membership_display_name(actor)
        return "unknown", membership_display_name(actor)
    if execution.status == EXECUTION_STATUS_DONE:
        if execution.validated_at is not None:
            actor = execution.validated_by_membership
        elif not execution.requires_validation and execution.marked_done_at is not None:
            actor = execution.marked_done_by_membership
        else:
            actor = None
        if actor is None:
            return "unknown", None
        return "manual", membership_display_name(actor)
    return "unknown", None


def _order_history(queryset: QuerySet[ActionPlanExecution]) -> QuerySet[ActionPlanExecution]:
    return queryset.order_by(F("terminal_at").desc(nulls_last=True), F("id").desc())


def build_execution_history_page(
    *,
    memberships: list[EstablishmentMembership],
    view_mode: str,
    scope: str,
    status: str,
    period: str,
    period_from: str | None,
    period_to: str | None,
    window: CivilWindow | None,
    page_size: int,
    cursor: ExecutionHistoryCursor | None,
) -> ExecutionHistoryPage:
    auth_hash = action_plan_execution_feed_auth_context_hash(
        memberships=memberships,
        view_mode=view_mode,  # type: ignore[arg-type]
        category="all",
        scope=scope,  # type: ignore[arg-type]
    )
    context_hash = execution_history_context_hash(
        scope=scope,
        view_mode=view_mode,
        status=status,
        period=period,
        period_from=period_from,
        period_to=period_to,
        auth_context_hash=auth_hash,
    )
    if cursor is not None:
        cursor.validate_context(context_hash)

    queryset = execution_history_queryset(memberships=memberships, view_mode=view_mode)
    if status != "all":
        queryset = queryset.filter(status=status)
    undated_count = None
    if cursor is None and window is not None:
        undated_count = queryset.filter(terminal_at__isnull=True).count()
    if window is not None:
        queryset = queryset.filter(terminal_at__gte=window.start, terminal_at__lt=window.end)
    if cursor is not None:
        queryset = apply_execution_history_cursor(
            queryset,
            cursor,
            include_undated=window is None,
        )
    rows = list(_order_history(queryset).values("id", "terminal_at")[: page_size + 1])
    has_more = len(rows) > page_size
    page_rows = rows[:page_size]
    items = _hydrate_execution_history_items(page_rows)
    next_cursor = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = encode_execution_history_cursor(
            scope=scope,
            view_mode=view_mode,
            status=status,
            period=period,
            period_from=period_from,
            period_to=period_to,
            auth_context_hash=auth_hash,
            terminal_at=last["terminal_at"],
            item_id=last["id"],
        )
    return ExecutionHistoryPage(
        items=items,
        has_more=has_more,
        next_cursor=next_cursor,
        undated_count=undated_count,
    )
