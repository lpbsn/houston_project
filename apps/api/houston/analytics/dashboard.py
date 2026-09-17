"""Establishment dashboard aggregations (no warehouse)."""

from __future__ import annotations

import base64
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from django.db.models import Count, Q, Sum
from django.utils import timezone

from houston.accounts.models import User
from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.models import (
    ActionPlanExecution,
    ActionPlanExecutionLifecycleEvent,
    ActionPlanExecutionReview,
)
from houston.analytics.comparisons import (
    AnalyticsComparisonPeriod,
    DashboardMetricComparison,
    build_adjacent_comparison_periods,
    compare_dashboard_metric_values,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.journal import (
    COVERAGE_COMPLETE,
    JournalEvent,
    comparison_coverage,
    coverage_for_window,
    first_signal_created_at,
    parse_metadata_datetime,
    resolve_history_reliable_from,
    signal_status_at,
)
from houston.analytics.models import (
    OperationalPattern,
    PatternEstablishmentSighting,
    PatternLifecycleEvent,
    SignalPatternAssignment,
)
from houston.analytics.selectors import AnalyticsReadScope, resolve_analytics_read_scope
from houston.establishments.management_scope import (
    list_management_memberships_for_user,
    management_establishment_ids_for_user,
)
from houston.establishments.membership_scope import (
    membership_business_unit_scope_ids,
    membership_scope_prefetch,
)
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES
from houston.gamification.constants import (
    SOURCE_TYPE_ACTION_PLAN_EXECUTION,
    SOURCE_TYPE_SIGNAL,
    SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST,
)
from houston.gamification.models import PointTransaction
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_CANCELED,
    SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING,
    SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
    SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN,
    SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST,
)
from houston.signals.models import Signal, SignalLifecycleEvent, SignalResolutionRequest

DASHBOARD_PERIOD_DAYS = frozenset({3, 7, 15, 30, 90})
DEFAULT_DASHBOARD_PERIOD_DAYS = 7
DASHBOARD_PREVIEW_LIMIT = 5
CONTRIBUTORS_LIMIT = 5
UNASSIGNED_LABEL = "Sans pôle"
UNASSIGNED_LOCATION_KEY = "unassigned"
UNASSIGNED_LOCATION_LABEL = "Sans localisation"
VOLUME_WINDOW_COUNT = 5
ON_TIME_WINDOW_RATIO = 0.10
RANKING_CURSOR_VERSION = "analytics_dashboard_rankings_v1"
DEFAULT_RANKING_PAGE_SIZE = 50
MAX_RANKING_PAGE_SIZE = 100
RANKING_KIND_RECURRING = "recurring"
RANKING_KIND_NEW = "new"
RANKING_KIND_LOCATIONS = "locations"
RANKING_KINDS = frozenset(
    {RANKING_KIND_RECURRING, RANKING_KIND_NEW, RANKING_KIND_LOCATIONS}
)

DESTINATION_WAITING = "waiting"
DESTINATION_INTERESTING = "interesting"
DESTINATION_ACTION_PLAN_IN_PROGRESS = "action_plan_in_progress"
DESTINATION_RESOLVED_DIRECT = "resolved_direct"
DESTINATION_RESOLVED_VIA_ACTION_PLAN = "resolved_via_action_plan"
DESTINATION_RESOLVED_VIA_RESOLUTION_REQUEST = "resolved_via_resolution_request"
DESTINATION_CANCELED = "canceled"
DESTINATION_KEYS = (
    DESTINATION_WAITING,
    DESTINATION_INTERESTING,
    DESTINATION_ACTION_PLAN_IN_PROGRESS,
    DESTINATION_RESOLVED_DIRECT,
    DESTINATION_RESOLVED_VIA_ACTION_PLAN,
    DESTINATION_RESOLVED_VIA_RESOLUTION_REQUEST,
    DESTINATION_CANCELED,
)
DESTINATION_DELAY_KEYS = tuple(
    key for key in DESTINATION_KEYS if key != DESTINATION_WAITING
)
VOLUME_LABEL_KEYS = (
    "four_periods_ago",
    "three_periods_ago",
    "two_periods_ago",
    "previous",
    "current",
)
OVERRUN_BUCKET_KEYS = (
    "lt_10",
    "from_10_to_25",
    "from_25_to_50",
    "from_50_to_100",
    "gte_100",
)
ORIGIN_TO_DESTINATION = {
    SIGNAL_RESOLUTION_ORIGIN_MANUAL: DESTINATION_RESOLVED_DIRECT,
    SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN: DESTINATION_RESOLVED_VIA_ACTION_PLAN,
    SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST: DESTINATION_RESOLVED_VIA_RESOLUTION_REQUEST,
}
CYCLE_BREAK_EVENTS = frozenset(
    {
        SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
        SIGNAL_LIFECYCLE_EVENT_CANCELED,
        SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    }
)


@dataclass(frozen=True)
class RecurringPatternItem:
    pattern_id: UUID
    name: str
    signal_count: int
    last_seen_at: datetime
    comparison: DashboardMetricComparison


@dataclass(frozen=True)
class NewPatternItem:
    pattern_id: UUID
    name: str
    first_seen_at: datetime


@dataclass(frozen=True)
class NamedCountItem:
    id: str
    name: str
    count: int
    comparison: DashboardMetricComparison


@dataclass(frozen=True)
class PreviewList:
    items: tuple
    total_count: int


@dataclass(frozen=True)
class ContributorItem:
    user_id: UUID
    name: str
    pts: int
    roles: tuple[str, ...]
    poles: tuple[str, ...]
    establishment_names: tuple[str, ...]


@dataclass(frozen=True)
class DestinationShare:
    count: int
    share: float | None
    comparison: DashboardMetricComparison


@dataclass(frozen=True)
class DestinationDelay:
    mean_seconds: float | None
    n: int
    undatable_in_scope: int


@dataclass(frozen=True)
class VolumeSegment:
    pole_id: str
    name: str
    count: int
    share: float | None


@dataclass(frozen=True)
class VolumeWindow:
    offset: int
    label_key: str
    total: int
    segments: tuple[VolumeSegment, ...]


@dataclass(frozen=True)
class ObservationVolume:
    windows: tuple[VolumeWindow, ...]
    current_total: int
    comparison: DashboardMetricComparison


@dataclass(frozen=True)
class DeadlineShare:
    early: float | None
    on_time: float | None
    late: float | None
    n: int
    early_count: int
    on_time_count: int
    late_count: int
    excluded_count: int
    early_comparison: DashboardMetricComparison
    on_time_comparison: DashboardMetricComparison
    late_comparison: DashboardMetricComparison


@dataclass(frozen=True)
class OverrunBucket:
    key: str
    count: int
    share: float | None


@dataclass(frozen=True)
class QualityBucket:
    stars: int
    count: int
    share: float | None


@dataclass(frozen=True)
class AnalyticsDashboardResult:
    period_days: int
    current_period: AnalyticsComparisonPeriod
    previous_period: AnalyticsComparisonPeriod
    history_reliable_from: datetime
    establishment_id: UUID
    establishment_name: str
    recurring_patterns: PreviewList
    new_patterns: PreviewList
    locations: PreviewList
    observation_volume: dict[str, ObservationVolume]
    observation_destinations: dict[str, DestinationShare]
    observation_destination_delays: dict[str, DestinationDelay]
    plan_deadline_respect: DeadlineShare
    plan_overrun: tuple[OverrunBucket, ...]
    resolution_quality: tuple[QualityBucket, ...]
    contributors: tuple[ContributorItem, ...]


@dataclass(frozen=True)
class AnalyticsDashboardRankingsResult:
    kind: str
    current_period: AnalyticsComparisonPeriod
    items: tuple
    total_count: int
    page_size: int
    has_more: bool
    next_cursor: str | None


def get_analytics_dashboard(
    user: User | None,
    *,
    period_days: int = DEFAULT_DASHBOARD_PERIOD_DAYS,
    establishment_id: UUID,
    now: datetime | None = None,
) -> AnalyticsDashboardResult:
    context = _load_dashboard_context(
        user,
        period_days=period_days,
        establishment_id=establishment_id,
        now=now,
    )
    recurring = _recurring_patterns(
        signals=context.signals,
        current_period=context.current_period,
        previous_period=context.previous_period,
    )
    new_patterns = _new_patterns(
        signals=context.signals,
        current_period=context.current_period,
        establishment_id=establishment_id,
    )
    locations = _location_counts(
        signals=context.signals,
        current_period=context.current_period,
        previous_period=context.previous_period,
    )
    return AnalyticsDashboardResult(
        period_days=period_days,
        current_period=context.current_period,
        previous_period=context.previous_period,
        history_reliable_from=context.reliable_from,
        establishment_id=establishment_id,
        establishment_name=context.establishment_name,
        recurring_patterns=_preview(recurring),
        new_patterns=_preview(new_patterns),
        locations=_preview(locations),
        observation_volume=_observation_volume(
            signals=context.signals,
            period_days=period_days,
            period_end=context.current_period.period_end,
        ),
        observation_destinations=_observation_destinations(
            signals=context.signals,
            events_by_signal=context.events_by_signal,
            current_period=context.current_period,
            previous_period=context.previous_period,
            reliable_from=context.reliable_from,
            coverage=context.journal_coverage,
        ),
        observation_destination_delays=_observation_destination_delays(
            signals=context.signals,
            events_by_signal=context.events_by_signal,
            current_period=context.current_period,
            reliable_from=context.reliable_from,
        ),
        plan_deadline_respect=_deadline_respect(
            executions=context.deadline_executions,
            events_by_execution=context.events_by_execution,
            current_period=context.current_period,
            previous_period=context.previous_period,
            coverage=context.journal_coverage,
        ),
        plan_overrun=_plan_overrun(executions=context.live_executions, now=context.moment),
        resolution_quality=_resolution_quality(
            establishment_id=establishment_id,
            current_period=context.current_period,
        ),
        contributors=_contributors(
            user=user,
            read_scope=context.read_scope,
            establishment_ids=(establishment_id,),
            current_period=context.current_period,
        ),
    )


def list_analytics_dashboard_rankings(
    user: User | None,
    *,
    establishment_id: UUID,
    kind: str,
    period_days: int = DEFAULT_DASHBOARD_PERIOD_DAYS,
    page_size: int = DEFAULT_RANKING_PAGE_SIZE,
    cursor: str | None = None,
    now: datetime | None = None,
) -> AnalyticsDashboardRankingsResult:
    if kind not in RANKING_KINDS:
        raise AnalyticsValidationError(
            "kind must be recurring, new, or locations.",
            code="analytics_dashboard_rankings_kind_invalid",
        )
    size = _parse_ranking_page_size(page_size)
    offset = _parse_ranking_cursor(cursor)
    context = _load_dashboard_context(
        user,
        period_days=period_days,
        establishment_id=establishment_id,
        now=now,
    )
    if kind == RANKING_KIND_RECURRING:
        items = _recurring_patterns(
            signals=context.signals,
            current_period=context.current_period,
            previous_period=context.previous_period,
        )
    elif kind == RANKING_KIND_NEW:
        items = _new_patterns(
            signals=context.signals,
            current_period=context.current_period,
            establishment_id=establishment_id,
        )
    else:
        items = _location_counts(
            signals=context.signals,
            current_period=context.current_period,
            previous_period=context.previous_period,
        )
    total = len(items)
    page = items[offset : offset + size]
    next_offset = offset + size
    has_more = next_offset < total
    return AnalyticsDashboardRankingsResult(
        kind=kind,
        current_period=context.current_period,
        items=page,
        total_count=total,
        page_size=size,
        has_more=has_more,
        next_cursor=_encode_ranking_cursor(next_offset) if has_more else None,
    )


@dataclass(frozen=True)
class _DashboardContext:
    moment: datetime
    current_period: AnalyticsComparisonPeriod
    previous_period: AnalyticsComparisonPeriod
    reliable_from: datetime
    journal_coverage: str
    establishment_name: str
    read_scope: AnalyticsReadScope
    signals: list[Signal]
    events_by_signal: dict[UUID, list[JournalEvent]]
    deadline_executions: list[ActionPlanExecution]
    live_executions: list[ActionPlanExecution]
    events_by_execution: dict[UUID, list[JournalEvent]]


def _load_dashboard_context(
    user: User | None,
    *,
    period_days: int,
    establishment_id: UUID,
    now: datetime | None,
) -> _DashboardContext:
    if period_days not in DASHBOARD_PERIOD_DAYS:
        raise AnalyticsValidationError(
            "period_days must be one of 3, 7, 15, 30, 90.",
            code="analytics_period_invalid",
        )
    moment = now or timezone.now()
    if timezone.is_naive(moment):
        raise AnalyticsValidationError(
            "now must be timezone-aware.",
            code="analytics_period_end_naive",
        )
    allowed_ids = set(management_establishment_ids_for_user(user))
    if not allowed_ids:
        raise AnalyticsValidationError(
            "You do not have permission to access analytics.",
            code="analytics_scope_forbidden",
        )
    if establishment_id not in allowed_ids:
        raise AnalyticsValidationError(
            "Establishment is outside the analytics scope.",
            code="analytics_scope_forbidden",
        )
    period_end = moment
    period_start = moment - timedelta(days=period_days)
    current_period, previous_period = build_adjacent_comparison_periods(
        period_start=period_start,
        period_end=period_end,
    )
    reliable_from = resolve_history_reliable_from(now=moment)
    read_scope = resolve_analytics_read_scope(
        user,
        establishment_id=establishment_id,
    )
    volume_start = period_end - timedelta(days=period_days * VOLUME_WINDOW_COUNT)
    signals = list(
        read_scope.readable_signals_queryset()
        .filter(merged_into__isnull=True)
        .filter(
            Q(created_at__gte=volume_start, created_at__lt=period_end)
            | Q(
                pattern_assignment__assigned_at__gte=current_period.period_start,
                pattern_assignment__assigned_at__lt=current_period.period_end,
            )
        )
        .select_related(
            "establishment",
            "operational_unit",
            "responsible_business_unit",
            "pattern_assignment__pattern__merged_into",
        )
    )
    signal_ids = [signal.id for signal in signals]
    events_by_signal = _group_signal_events(signal_ids)
    live_executions = list(
        read_scope.readable_executions_queryset()
        .filter(
            establishment_id=establishment_id,
            status__in=(EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS),
            end_at__lt=moment,
        )
        .select_related("establishment")
    )
    marked_done_ids = list(
        ActionPlanExecutionLifecycleEvent.objects.filter(
            establishment_id=establishment_id,
            event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
            occurred_at__gte=previous_period.period_start,
            occurred_at__lt=current_period.period_end,
        )
        .values_list("action_plan_execution_id", flat=True)
        .distinct()
    )
    deadline_executions = list(
        read_scope.readable_executions_queryset()
        .filter(id__in=marked_done_ids, establishment_id=establishment_id)
        .select_related("establishment")
        if marked_done_ids
        else []
    )
    events_by_execution = _group_execution_events(
        [execution.id for execution in deadline_executions]
    )
    journal_current = coverage_for_window(
        window_start=current_period.period_start,
        window_end=current_period.period_end,
        reliable_from=reliable_from,
        needs_journal=True,
    )
    journal_previous = coverage_for_window(
        window_start=previous_period.period_start,
        window_end=previous_period.period_end,
        reliable_from=reliable_from,
        needs_journal=True,
        previous_end=previous_period.period_end,
    )
    establishment_name = (
        Establishment.objects.filter(pk=establishment_id).values_list("name", flat=True).first()
        or ""
    )
    return _DashboardContext(
        moment=moment,
        current_period=current_period,
        previous_period=previous_period,
        reliable_from=reliable_from,
        journal_coverage=comparison_coverage(
            current=journal_current, previous=journal_previous
        ),
        establishment_name=establishment_name,
        read_scope=read_scope,
        signals=signals,
        events_by_signal=events_by_signal,
        deadline_executions=deadline_executions,
        live_executions=live_executions,
        events_by_execution=events_by_execution,
    )


def _preview(items: tuple, *, limit: int = DASHBOARD_PREVIEW_LIMIT) -> PreviewList:
    return PreviewList(items=tuple(items[:limit]), total_count=len(items))


def _parse_ranking_page_size(page_size) -> int:
    try:
        size = int(page_size)
    except (TypeError, ValueError) as exc:
        raise AnalyticsValidationError(
            "page_size must be a positive integer.",
            code="analytics_dashboard_rankings_page_size_invalid",
        ) from exc
    if size < 1 or size > MAX_RANKING_PAGE_SIZE:
        raise AnalyticsValidationError(
            "page_size must be between 1 and 100.",
            code="analytics_dashboard_rankings_page_size_invalid",
        )
    return size


def _encode_ranking_cursor(offset: int) -> str:
    raw = json.dumps(
        {"version": RANKING_CURSOR_VERSION, "offset": offset},
        separators=(",", ":"),
    )
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _parse_ranking_cursor(cursor: str | None) -> int:
    if cursor in (None, ""):
        return 0
    padded = cursor + ("=" * (-len(cursor) % 4))
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        if payload.get("version") != RANKING_CURSOR_VERSION:
            raise ValueError("version")
        offset = int(payload["offset"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise AnalyticsValidationError(
            "cursor is invalid.",
            code="analytics_dashboard_rankings_cursor_invalid",
        ) from exc
    if offset < 0:
        raise AnalyticsValidationError(
            "cursor is invalid.",
            code="analytics_dashboard_rankings_cursor_invalid",
        )
    return offset


def _group_signal_events(signal_ids: list[UUID]) -> dict[UUID, list[JournalEvent]]:
    grouped: dict[UUID, list[JournalEvent]] = defaultdict(list)
    if not signal_ids:
        return grouped
    for event in SignalLifecycleEvent.objects.filter(signal_id__in=signal_ids).order_by(
        "occurred_at", "id"
    ):
        grouped[event.signal_id].append(
            JournalEvent(
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                metadata_safe=event.metadata_safe or {},
            )
        )
    return grouped


def _group_execution_events(execution_ids: list[UUID]) -> dict[UUID, list[JournalEvent]]:
    grouped: dict[UUID, list[JournalEvent]] = defaultdict(list)
    if not execution_ids:
        return grouped
    for event in ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution_id__in=execution_ids
    ).order_by("occurred_at", "id"):
        grouped[event.action_plan_execution_id].append(
            JournalEvent(
                event_type=event.event_type,
                occurred_at=event.occurred_at,
                metadata_safe=event.metadata_safe or {},
            )
        )
    return grouped


def _in_period(moment: datetime, period: AnalyticsComparisonPeriod) -> bool:
    return period.period_start <= moment < period.period_end


def _canonical_pattern(assignment: SignalPatternAssignment) -> OperationalPattern | None:
    pattern = assignment.pattern
    if pattern is None:
        return None
    if pattern.merged_into_id is not None:
        return pattern.merged_into
    return pattern


def _pattern_merge_sources_by_target(
    patterns: dict[UUID, OperationalPattern],
) -> dict[UUID, list[UUID]]:
    by_target: dict[UUID, list[UUID]] = defaultdict(list)
    for pattern_id, pattern in patterns.items():
        if pattern.merged_into_id is not None:
            by_target[pattern.merged_into_id].append(pattern_id)
    return by_target


def _pattern_merge_lineage_ids(
    *,
    canonical_id: UUID,
    sources_by_target: dict[UUID, list[UUID]],
) -> set[UUID]:
    lineage = {canonical_id}
    stack = [canonical_id]
    while stack:
        current = stack.pop()
        for source_id in sources_by_target.get(current, ()):
            if source_id not in lineage:
                lineage.add(source_id)
                stack.append(source_id)
    return lineage


def _dimension_label(business_unit) -> str:
    if business_unit is None:
        return UNASSIGNED_LABEL
    value = (
        getattr(business_unit, "specific_name", None)
        or getattr(business_unit, "label", None)
        or ""
    ).strip()
    return value or UNASSIGNED_LABEL


def _last_event_before(
    events: list[JournalEvent],
    event_type: str,
    *,
    before: datetime,
) -> JournalEvent | None:
    last = None
    for event in events:
        if event.event_type == event_type and event.occurred_at < before:
            last = event
    return last


def _destination_for_signal(
    *,
    signal: Signal,
    events: list[JournalEvent],
    period: AnalyticsComparisonPeriod,
    reliable_from: datetime,
) -> str | None:
    if not _in_period(signal.created_at, period):
        return None
    status = signal_status_at(
        at=period.period_end,
        reliable_from=reliable_from,
        events=events,
    )
    if status == Signal.Status.ARCHIVED or status is None:
        return None
    if status == Signal.Status.OPEN:
        return DESTINATION_WAITING
    if status == Signal.Status.INTERESTING:
        return DESTINATION_INTERESTING
    if status == Signal.Status.IN_PROGRESS:
        return DESTINATION_ACTION_PLAN_IN_PROGRESS
    if status == Signal.Status.CANCELED:
        return DESTINATION_CANCELED
    if status == Signal.Status.RESOLVED:
        resolved = _last_event_before(
            events, SIGNAL_LIFECYCLE_EVENT_RESOLVED, before=period.period_end
        )
        if resolved is None:
            return None
        origin = resolved.metadata_safe.get("resolution_origin")
        return ORIGIN_TO_DESTINATION.get(str(origin)) if origin else None
    return None


def _reached_at(
    *,
    destination: str,
    signal: Signal,
    events: list[JournalEvent],
    period_end: datetime,
) -> datetime | None:
    if destination == DESTINATION_INTERESTING:
        event = _last_event_before(
            events, SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING, before=period_end
        )
        if event is not None:
            return event.occurred_at
        if signal.marked_interesting_at is not None and signal.marked_interesting_at < period_end:
            return signal.marked_interesting_at
        return None
    if destination == DESTINATION_CANCELED:
        event = _last_event_before(
            events, SIGNAL_LIFECYCLE_EVENT_CANCELED, before=period_end
        )
        if event is not None:
            return event.occurred_at
        if signal.canceled_at is not None and signal.canceled_at < period_end:
            return signal.canceled_at
        return None
    if destination in {
        DESTINATION_RESOLVED_DIRECT,
        DESTINATION_RESOLVED_VIA_ACTION_PLAN,
        DESTINATION_RESOLVED_VIA_RESOLUTION_REQUEST,
    }:
        event = _last_event_before(
            events, SIGNAL_LIFECYCLE_EVENT_RESOLVED, before=period_end
        )
        return event.occurred_at if event is not None else None
    if destination == DESTINATION_ACTION_PLAN_IN_PROGRESS:
        return _in_progress_cycle_start(
            signal=signal, events=events, period_end=period_end
        )
    return None


def _in_progress_cycle_start(
    *,
    signal: Signal,
    events: list[JournalEvent],
    period_end: datetime,
) -> datetime | None:
    moved = [
        event
        for event in events
        if event.event_type == SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS
        and event.occurred_at < period_end
    ]
    if not moved:
        return None
    last = moved[-1]
    for event in events:
        if (
            last.occurred_at < event.occurred_at < period_end
            and event.event_type in CYCLE_BREAK_EVENTS
        ):
            return None
    associated_at = signal.first_action_plan_associated_at
    if (
        len(moved) == 1
        and associated_at is not None
        and associated_at < period_end
        and not any(
            event.event_type == SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN
            and event.occurred_at < last.occurred_at
            for event in events
        )
        and associated_at <= last.occurred_at
    ):
        earlier_cycle = associated_at < last.occurred_at
        if earlier_cycle:
            return last.occurred_at
        return associated_at
    return last.occurred_at


def _observation_destinations(
    *,
    signals: list[Signal],
    events_by_signal: dict[UUID, list[JournalEvent]],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    reliable_from: datetime,
    coverage: str,
) -> dict[str, DestinationShare]:
    def counts_for(period: AnalyticsComparisonPeriod) -> dict[str, int]:
        counts = {key: 0 for key in DESTINATION_KEYS}
        for signal in signals:
            destination = _destination_for_signal(
                signal=signal,
                events=events_by_signal.get(signal.id, []),
                period=period,
                reliable_from=reliable_from,
            )
            if destination is not None:
                counts[destination] += 1
        return counts

    current = counts_for(current_period)
    previous = counts_for(previous_period)
    current_total = sum(current.values())
    previous_total = sum(previous.values())
    result: dict[str, DestinationShare] = {}
    for key in DESTINATION_KEYS:
        current_count = current[key]
        previous_count = previous[key]
        current_share = (current_count / current_total) if current_total else None
        previous_share = (previous_count / previous_total) if previous_total else None
        result[key] = DestinationShare(
            count=current_count,
            share=current_share,
            comparison=compare_dashboard_metric_values(
                current=current_share,
                previous=previous_share,
                coverage=coverage,
                points=True,
            ),
        )
    return result


def _observation_destination_delays(
    *,
    signals: list[Signal],
    events_by_signal: dict[UUID, list[JournalEvent]],
    current_period: AnalyticsComparisonPeriod,
    reliable_from: datetime,
) -> dict[str, DestinationDelay]:
    values: dict[str, list[float]] = {key: [] for key in DESTINATION_DELAY_KEYS}
    undatable: dict[str, int] = {key: 0 for key in DESTINATION_DELAY_KEYS}
    for signal in signals:
        events = events_by_signal.get(signal.id, [])
        destination = _destination_for_signal(
            signal=signal,
            events=events,
            period=current_period,
            reliable_from=reliable_from,
        )
        if destination not in values:
            continue
        created_at = first_signal_created_at(events, fallback=signal.created_at)
        reached_at = _reached_at(
            destination=destination,
            signal=signal,
            events=events,
            period_end=current_period.period_end,
        )
        if created_at is None or reached_at is None or reached_at < created_at:
            undatable[destination] += 1
            continue
        values[destination].append((reached_at - created_at).total_seconds())
    result: dict[str, DestinationDelay] = {}
    for key in DESTINATION_DELAY_KEYS:
        samples = values[key]
        mean = (sum(samples) / len(samples)) if samples else None
        result[key] = DestinationDelay(
            mean_seconds=mean,
            n=len(samples),
            undatable_in_scope=undatable[key],
        )
    return result


def _observation_volume(
    *,
    signals: list[Signal],
    period_days: int,
    period_end: datetime,
) -> dict[str, ObservationVolume]:
    delta = timedelta(days=period_days)
    windows_spec = []
    for index, label_key in enumerate(VOLUME_LABEL_KEYS):
        offset = VOLUME_WINDOW_COUNT - 1 - index
        window_end = period_end - (offset * delta)
        window_start = window_end - delta
        windows_spec.append((offset, label_key, window_start, window_end))

    def build(mode: str) -> ObservationVolume:
        window_models: list[VolumeWindow] = []
        current_total = 0
        previous_total = 0
        for offset, label_key, window_start, window_end in windows_spec:
            grouped: dict[tuple[str, str], int] = defaultdict(int)
            for signal in signals:
                if not (window_start <= signal.created_at < window_end):
                    continue
                if mode == "affected":
                    pole = signal.operational_unit
                    pole_id = (
                        str(signal.operational_unit_id)
                        if signal.operational_unit_id
                        else "unassigned"
                    )
                else:
                    pole = signal.responsible_business_unit
                    pole_id = (
                        str(signal.responsible_business_unit_id)
                        if signal.responsible_business_unit_id
                        else "unassigned"
                    )
                grouped[(pole_id, _dimension_label(pole))] += 1
            total = sum(grouped.values())
            segments = tuple(
                VolumeSegment(
                    pole_id=pole_id,
                    name=name,
                    count=count,
                    share=(count / total) if total else None,
                )
                for (pole_id, name), count in sorted(
                    grouped.items(), key=lambda item: (-item[1], item[0][1])
                )
            )
            window_models.append(
                VolumeWindow(
                    offset=offset,
                    label_key=label_key,
                    total=total,
                    segments=segments,
                )
            )
            if label_key == "current":
                current_total = total
            if label_key == "previous":
                previous_total = total
        return ObservationVolume(
            windows=tuple(window_models),
            current_total=current_total,
            comparison=compare_dashboard_metric_values(
                current=current_total,
                previous=previous_total,
                coverage=COVERAGE_COMPLETE,
            ),
        )

    return {
        "affected": build("affected"),
        "responsible": build("responsible"),
    }


def _team_finish_event(
    events: list[JournalEvent], *, before: datetime
) -> JournalEvent | None:
    last = None
    for event in events:
        if event.event_type != EXECUTION_LIFECYCLE_EVENT_MARKED_DONE:
            continue
        if event.occurred_at >= before:
            continue
        to_status = event.metadata_safe.get("to_status") or EXECUTION_STATUS_DONE
        if to_status in {EXECUTION_STATUS_PENDING_VALIDATION, EXECUTION_STATUS_DONE}:
            last = event
    return last


def _classify_deadline(event: JournalEvent) -> str | None:
    start_at = parse_metadata_datetime(event.metadata_safe.get("start_at"))
    end_at = parse_metadata_datetime(event.metadata_safe.get("end_at"))
    finished_at = event.occurred_at
    if start_at is None or end_at is None or finished_at is None:
        return None
    if timezone.is_naive(start_at) or timezone.is_naive(end_at) or timezone.is_naive(finished_at):
        return None
    planned = end_at - start_at
    if planned.total_seconds() <= 0:
        return None
    window = planned * ON_TIME_WINDOW_RATIO
    threshold = end_at - window
    if finished_at < threshold:
        return "early"
    if finished_at <= end_at:
        return "on_time"
    return "late"


def _deadline_respect(
    *,
    executions: list[ActionPlanExecution],
    events_by_execution: dict[UUID, list[JournalEvent]],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    coverage: str,
) -> DeadlineShare:
    def shares_for(period: AnalyticsComparisonPeriod) -> tuple[int, int, int, int, int]:
        early = on_time = late = excluded = 0
        for execution in executions:
            events = events_by_execution.get(execution.id, [])
            finish = _team_finish_event(events, before=period.period_end)
            if finish is None or not _in_period(finish.occurred_at, period):
                continue
            bucket = _classify_deadline(finish)
            if bucket is None:
                excluded += 1
                continue
            if bucket == "early":
                early += 1
            elif bucket == "on_time":
                on_time += 1
            else:
                late += 1
        return early, on_time, late, excluded, early + on_time + late

    cur_early, cur_on_time, cur_late, excluded, n = shares_for(current_period)
    prev_early, prev_on_time, prev_late, _pe, prev_n = shares_for(previous_period)

    def share(count: int, total: int) -> float | None:
        if total == 0:
            return None
        return count / total

    return DeadlineShare(
        early=share(cur_early, n),
        on_time=share(cur_on_time, n),
        late=share(cur_late, n),
        n=n,
        early_count=cur_early,
        on_time_count=cur_on_time,
        late_count=cur_late,
        excluded_count=excluded,
        early_comparison=compare_dashboard_metric_values(
            current=share(cur_early, n),
            previous=share(prev_early, prev_n),
            coverage=coverage,
            points=True,
        ),
        on_time_comparison=compare_dashboard_metric_values(
            current=share(cur_on_time, n),
            previous=share(prev_on_time, prev_n),
            coverage=coverage,
            points=True,
        ),
        late_comparison=compare_dashboard_metric_values(
            current=share(cur_late, n),
            previous=share(prev_late, prev_n),
            coverage=coverage,
            points=True,
        ),
    )


def _overrun_bucket_key(percent: float) -> str:
    if percent < 10:
        return "lt_10"
    if percent < 25:
        return "from_10_to_25"
    if percent < 50:
        return "from_25_to_50"
    if percent < 100:
        return "from_50_to_100"
    return "gte_100"


def _plan_overrun(
    *,
    executions: list[ActionPlanExecution],
    now: datetime,
) -> tuple[OverrunBucket, ...]:
    counts = {key: 0 for key in OVERRUN_BUCKET_KEYS}
    for execution in executions:
        if execution.status not in {EXECUTION_STATUS_SCHEDULED, EXECUTION_STATUS_IN_PROGRESS}:
            continue
        if execution.status in {
            EXECUTION_STATUS_PENDING_VALIDATION,
            EXECUTION_STATUS_DONE,
            EXECUTION_STATUS_CANCELED,
        }:
            continue
        if execution.start_at is None or execution.end_at is None:
            continue
        if execution.end_at >= now:
            continue
        planned = execution.end_at - execution.start_at
        if planned.total_seconds() <= 0:
            continue
        percent = ((now - execution.end_at) / planned) * 100
        counts[_overrun_bucket_key(percent)] += 1
    total = sum(counts.values())
    return tuple(
        OverrunBucket(
            key=key,
            count=counts[key],
            share=(counts[key] / total) if total else None,
        )
        for key in OVERRUN_BUCKET_KEYS
    )


def _resolution_quality(
    *,
    establishment_id: UUID,
    current_period: AnalyticsComparisonPeriod,
) -> tuple[QualityBucket, ...]:
    rows = (
        ActionPlanExecutionReview.objects.filter(
            is_active=True,
            reviewed_at__gte=current_period.period_start,
            reviewed_at__lt=current_period.period_end,
            action_plan_execution__establishment_id=establishment_id,
        )
        .values("stars")
        .annotate(count=Count("id"))
    )
    counts = {stars: 0 for stars in range(6)}
    for row in rows:
        stars = int(row["stars"])
        if 0 <= stars <= 5:
            counts[stars] = int(row["count"])
    total = sum(counts.values())
    return tuple(
        QualityBucket(
            stars=stars,
            count=counts[stars],
            share=(counts[stars] / total) if total else None,
        )
        for stars in range(5, -1, -1)
    )


def _recurring_patterns(
    *,
    signals: list[Signal],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
) -> tuple[RecurringPatternItem, ...]:
    def counts_for(period: AnalyticsComparisonPeriod) -> dict[UUID, dict]:
        grouped: dict[UUID, dict] = {}
        for signal in signals:
            if not _in_period(signal.created_at, period):
                continue
            assignment = getattr(signal, "pattern_assignment", None)
            if assignment is None or assignment.pattern_id is None:
                continue
            pattern = _canonical_pattern(assignment)
            if pattern is None:
                continue
            entry = grouped.setdefault(
                pattern.id,
                {"name": pattern.label, "count": 0, "last_seen": signal.created_at},
            )
            entry["count"] += 1
            if signal.created_at > entry["last_seen"]:
                entry["last_seen"] = signal.created_at
        return grouped

    current = counts_for(current_period)
    previous = counts_for(previous_period)
    recurrent = [
        (pattern_id, payload)
        for pattern_id, payload in current.items()
        if payload["count"] >= 2
    ]
    recurrent.sort(
        key=lambda item: (-item[1]["count"], -item[1]["last_seen"].timestamp(), item[1]["name"])
    )
    items = []
    for pattern_id, payload in recurrent:
        items.append(
            RecurringPatternItem(
                pattern_id=pattern_id,
                name=payload["name"],
                signal_count=payload["count"],
                last_seen_at=payload["last_seen"],
                comparison=compare_dashboard_metric_values(
                    current=payload["count"],
                    previous=previous.get(pattern_id, {}).get("count", 0),
                    coverage=COVERAGE_COMPLETE,
                ),
            )
        )
    return tuple(items)


def _new_patterns(
    *,
    signals: list[Signal],
    current_period: AnalyticsComparisonPeriod,
    establishment_id: UUID,
) -> tuple[NewPatternItem, ...]:
    assigned = [
        signal
        for signal in signals
        if getattr(signal, "pattern_assignment", None) is not None
        and signal.pattern_assignment.pattern_id is not None
        and signal.establishment_id == establishment_id
    ]
    if not assigned:
        return ()
    org_ids = {signal.establishment.organization_id for signal in assigned}
    patterns = {
        pattern.id: pattern
        for pattern in OperationalPattern.objects.filter(organization_id__in=org_ids)
    }
    related_by_canonical: dict[UUID, list[Signal]] = defaultdict(list)
    assignment_min: dict[UUID, datetime] = {}
    for signal in assigned:
        pattern = _canonical_pattern(signal.pattern_assignment)
        if pattern is None:
            continue
        related_by_canonical[pattern.id].append(signal)
        assigned_at = signal.pattern_assignment.assigned_at
        if assigned_at is None:
            continue
        previous = assignment_min.get(pattern.id)
        if previous is None or assigned_at < previous:
            assignment_min[pattern.id] = assigned_at
    if not related_by_canonical:
        return ()

    canonical_ids = set(related_by_canonical)
    sighting_qs = PatternEstablishmentSighting.objects.filter(
        pattern_id__in=canonical_ids,
        pattern__organization_id__in=org_ids,
        establishment_id=establishment_id,
    )
    sighting_min: dict[UUID, datetime] = {}
    for sighting in sighting_qs:
        previous = sighting_min.get(sighting.pattern_id)
        if previous is None or sighting.observed_at < previous:
            sighting_min[sighting.pattern_id] = sighting.observed_at

    sources_by_target = _pattern_merge_sources_by_target(patterns)
    lineage_ids: set[UUID] = set()
    for canonical_id in canonical_ids:
        lineage_ids.update(
            _pattern_merge_lineage_ids(
                canonical_id=canonical_id,
                sources_by_target=sources_by_target,
            )
        )
    split_created_ids = {
        event.pattern_id
        for event in PatternLifecycleEvent.objects.filter(
            event_type=PatternLifecycleEvent.EventType.CREATED,
            pattern_id__in=lineage_ids,
            organization_id__in=org_ids,
        )
        if event.metadata_safe.get("created_for_split") is True
    }
    entirely_split = {
        canonical_id
        for canonical_id in canonical_ids
        if _pattern_merge_lineage_ids(
            canonical_id=canonical_id,
            sources_by_target=sources_by_target,
        ).issubset(split_created_ids)
    }

    items: list[NewPatternItem] = []
    for canonical_id, related_signals in related_by_canonical.items():
        if canonical_id in entirely_split:
            continue
        pattern = patterns.get(canonical_id)
        if pattern is None:
            continue
        candidates = [
            ts
            for ts in (sighting_min.get(canonical_id), assignment_min.get(canonical_id))
            if ts is not None
        ]
        first_seen = min(candidates) if candidates else None
        if first_seen is None or not _in_period(first_seen, current_period):
            continue
        items.append(
            NewPatternItem(
                pattern_id=canonical_id,
                name=pattern.label,
                first_seen_at=first_seen,
            )
        )

    items.sort(key=lambda item: item.first_seen_at, reverse=True)
    return tuple(items)


def _parse_ledger_source_uuid(source_id: str) -> UUID | None:
    try:
        return UUID(str(source_id))
    except (TypeError, ValueError, AttributeError):
        return None


def _admin_establishment_ids_for_user(
    user: User | None,
    establishment_ids: tuple[UUID, ...],
) -> frozenset[UUID]:
    allowed = set(establishment_ids)
    return frozenset(
        membership.establishment_id
        for membership in list_management_memberships_for_user(user)
        if membership.role in ADMIN_ROLES and membership.establishment_id in allowed
    )


def _effective_contributor_source(
    transaction: PointTransaction,
) -> tuple[str, UUID] | None:
    origin = (
        transaction.reversed_transaction
        if transaction.reversed_transaction_id is not None
        else transaction
    )
    source_id = _parse_ledger_source_uuid(origin.source_id)
    if source_id is None:
        return None
    return origin.source_type, source_id


def _manager_in_scope_transaction_ids(
    transactions: list[PointTransaction],
    read_scope: AnalyticsReadScope,
) -> set[UUID]:
    if not transactions:
        return set()

    signal_ids: set[UUID] = set()
    request_ids: set[UUID] = set()
    execution_ids: set[UUID] = set()
    effective: dict[UUID, tuple[str, UUID]] = {}
    for transaction in transactions:
        parsed = _effective_contributor_source(transaction)
        if parsed is None:
            continue
        source_type, source_id = parsed
        effective[transaction.id] = parsed
        if source_type == SOURCE_TYPE_SIGNAL:
            signal_ids.add(source_id)
        elif source_type == SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST:
            request_ids.add(source_id)
        elif source_type == SOURCE_TYPE_ACTION_PLAN_EXECUTION:
            execution_ids.add(source_id)

    authorized_signals = set()
    if signal_ids:
        authorized_signals = set(
            read_scope.readable_signals_queryset()
            .filter(id__in=signal_ids)
            .values_list("id", "establishment_id")
        )

    authorized_requests = set()
    if request_ids:
        request_rows = list(
            SignalResolutionRequest.objects.filter(id__in=request_ids).values_list(
                "id",
                "signal_id",
                "signal__establishment_id",
            )
        )
        readable_request_signals = set(
            read_scope.readable_signals_queryset()
            .filter(id__in={signal_id for _, signal_id, _ in request_rows})
            .values_list("id", flat=True)
        )
        authorized_requests = {
            (request_id, establishment_id)
            for request_id, signal_id, establishment_id in request_rows
            if signal_id in readable_request_signals
        }

    authorized_executions = set()
    if execution_ids:
        authorized_executions = set(
            read_scope.readable_executions_queryset()
            .filter(id__in=execution_ids)
            .values_list("id", "establishment_id")
        )

    allowed: set[UUID] = set()
    for transaction in transactions:
        parsed = effective.get(transaction.id)
        if parsed is None:
            continue
        source_type, source_id = parsed
        source_key = (source_id, transaction.establishment_id)
        if source_type == SOURCE_TYPE_SIGNAL and source_key in authorized_signals:
            allowed.add(transaction.id)
        elif (
            source_type == SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST
            and source_key in authorized_requests
        ):
            allowed.add(transaction.id)
        elif (
            source_type == SOURCE_TYPE_ACTION_PLAN_EXECUTION
            and source_key in authorized_executions
        ):
            allowed.add(transaction.id)
    return allowed


def _foreign_source_transaction_ids(transactions: list[PointTransaction]) -> set[UUID]:
    signal_ids: set[UUID] = set()
    request_ids: set[UUID] = set()
    execution_ids: set[UUID] = set()
    parsed_by_tx: dict[UUID, tuple[str, UUID]] = {}
    for transaction in transactions:
        parsed = _effective_contributor_source(transaction)
        if parsed is None:
            continue
        parsed_by_tx[transaction.id] = parsed
        source_type, source_id = parsed
        if source_type == SOURCE_TYPE_SIGNAL:
            signal_ids.add(source_id)
        elif source_type == SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST:
            request_ids.add(source_id)
        elif source_type == SOURCE_TYPE_ACTION_PLAN_EXECUTION:
            execution_ids.add(source_id)

    signal_establishments = (
        dict(Signal.objects.filter(id__in=signal_ids).values_list("id", "establishment_id"))
        if signal_ids
        else {}
    )
    request_establishments = (
        dict(
            SignalResolutionRequest.objects.filter(id__in=request_ids).values_list(
                "id",
                "signal__establishment_id",
            )
        )
        if request_ids
        else {}
    )
    execution_establishments = (
        dict(
            ActionPlanExecution.objects.filter(id__in=execution_ids).values_list(
                "id",
                "establishment_id",
            )
        )
        if execution_ids
        else {}
    )

    foreign: set[UUID] = set()
    for transaction in transactions:
        parsed = parsed_by_tx.get(transaction.id)
        if parsed is None:
            continue
        source_type, source_id = parsed
        if source_type == SOURCE_TYPE_SIGNAL:
            source_establishment = signal_establishments.get(source_id)
        elif source_type == SOURCE_TYPE_SIGNAL_RESOLUTION_REQUEST:
            source_establishment = request_establishments.get(source_id)
        elif source_type == SOURCE_TYPE_ACTION_PLAN_EXECUTION:
            source_establishment = execution_establishments.get(source_id)
        else:
            continue
        if (
            source_establishment is not None
            and source_establishment != transaction.establishment_id
        ):
            foreign.add(transaction.id)
    return foreign


def _contributor_transactions(
    *,
    user: User | None,
    read_scope: AnalyticsReadScope,
    establishment_ids: tuple[UUID, ...],
    current_period: AnalyticsComparisonPeriod,
):
    queryset = PointTransaction.objects.filter(
        establishment_id__in=establishment_ids,
        occurred_at__gte=current_period.period_start,
        occurred_at__lt=current_period.period_end,
    )
    foreign_ids = _foreign_source_transaction_ids(
        list(queryset.select_related("reversed_transaction"))
    )
    if foreign_ids:
        queryset = queryset.exclude(pk__in=foreign_ids)
    admin_ids = _admin_establishment_ids_for_user(user, establishment_ids)
    if admin_ids == set(establishment_ids):
        return queryset

    manager_queryset = (
        queryset.exclude(establishment_id__in=admin_ids) if admin_ids else queryset
    )
    authorized_ids = _manager_in_scope_transaction_ids(
        list(manager_queryset.select_related("reversed_transaction")),
        read_scope,
    )
    if admin_ids:
        return queryset.filter(
            Q(establishment_id__in=admin_ids) | Q(pk__in=authorized_ids)
        )
    return queryset.filter(pk__in=authorized_ids)


def _contributors(
    *,
    user: User | None,
    read_scope: AnalyticsReadScope,
    establishment_ids: tuple[UUID, ...],
    current_period: AnalyticsComparisonPeriod,
) -> tuple[ContributorItem, ...]:
    if not establishment_ids:
        return ()
    rows = list(
        _contributor_transactions(
            user=user,
            read_scope=read_scope,
            establishment_ids=establishment_ids,
            current_period=current_period,
        )
        .values("membership__user_id")
        .annotate(
            pts=Sum("delta"),
            contribution_count=Count("id"),
        )
        .order_by("-pts", "-contribution_count", "membership__user_id")[:CONTRIBUTORS_LIMIT]
    )
    user_ids = [row["membership__user_id"] for row in rows if row["membership__user_id"]]
    memberships = list(
        EstablishmentMembership.objects.filter(
            user_id__in=user_ids,
            establishment_id__in=establishment_ids,
        )
        .select_related("user", "establishment")
        .prefetch_related(membership_scope_prefetch())
    )
    by_user: dict[UUID, list[EstablishmentMembership]] = defaultdict(list)
    for membership in memberships:
        by_user[membership.user_id].append(membership)
    items = []
    for row in rows:
        user_id = row["membership__user_id"]
        user_memberships = by_user.get(user_id, [])
        person = user_memberships[0].user if user_memberships else None
        name = ""
        if person is not None:
            name = (person.get_full_name() or person.email or person.username or "").strip()
        roles = tuple(sorted({membership.role for membership in user_memberships}))
        poles: list[str] = []
        for membership in user_memberships:
            bu_ids = membership_business_unit_scope_ids(membership)
            if not bu_ids:
                poles.append(UNASSIGNED_LABEL)
                continue
            for scope in membership.scope_links.all():
                if scope.business_unit_id in bu_ids:
                    poles.append(_dimension_label(scope.business_unit))
        unique_poles = tuple(sorted(set(poles))) or (UNASSIGNED_LABEL,)
        establishment_names = tuple(
            sorted(
                {
                    membership.establishment.name
                    for membership in user_memberships
                    if membership.establishment.name
                }
            )
        )
        items.append(
            ContributorItem(
                user_id=user_id,
                name=name,
                pts=int(row["pts"] or 0),
                roles=roles,
                poles=unique_poles,
                establishment_names=establishment_names,
            )
        )
    return tuple(items)


def _normalized_location_key(location_text: str) -> str:
    stripped = (location_text or "").strip()
    if not stripped:
        return UNASSIGNED_LOCATION_KEY
    return stripped.casefold()


def _location_display_name(*, dim_id: str, spellings: dict[str, int]) -> str:
    if dim_id == UNASSIGNED_LOCATION_KEY or not spellings:
        return UNASSIGNED_LOCATION_LABEL
    return min(spellings.items(), key=lambda item: (-item[1], item[0]))[0]


def _location_counts(
    *,
    signals: list[Signal],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
) -> tuple[NamedCountItem, ...]:
    def key_for(signal: Signal) -> str:
        return _normalized_location_key(signal.location_text)

    def counts_for(
        period: AnalyticsComparisonPeriod,
    ) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
        grouped: dict[str, int] = defaultdict(int)
        spellings: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for signal in signals:
            if not _in_period(signal.created_at, period):
                continue
            key = key_for(signal)
            grouped[key] += 1
            stripped = (signal.location_text or "").strip()
            if key != UNASSIGNED_LOCATION_KEY:
                spellings[key][stripped] += 1
        return grouped, spellings

    current, current_spellings = counts_for(current_period)
    previous, _ = counts_for(previous_period)
    items = []
    for dim_id, count in current.items():
        items.append(
            NamedCountItem(
                id=dim_id,
                name=_location_display_name(
                    dim_id=dim_id,
                    spellings=current_spellings.get(dim_id, {}),
                ),
                count=count,
                comparison=compare_dashboard_metric_values(
                    current=count,
                    previous=previous.get(dim_id, 0),
                    coverage=COVERAGE_COMPLETE,
                ),
            )
        )
    items.sort(key=lambda item: (-item.count, item.name))
    return tuple(items)
