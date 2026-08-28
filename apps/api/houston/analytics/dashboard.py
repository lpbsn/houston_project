"""Decision dashboard aggregations (no warehouse).

Two coverage regimes:

- Live canonical identity (coverage ``complete``): recurring motifs (widget 8.1),
  poles (current ``responsible_business_unit``), locations (current
  ``location_text``). A qualify moves historical period bars. Not gated by
  ``reliable_from``. New motifs share this identity for the pattern; ``first_seen``
  comes from persisted sighting / ``assigned_at`` — not cycle journals, not
  ``reliable_from``, and not a current-state-only read.
- Cycle journals: delays, resolution rate, closures, reopenings, aging, plan
  deadlines. ``history_reliable_from`` applies only here. Transform uses
  ``first_action_plan_associated_at`` (complete), not a classification journal.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Count, Sum
from django.utils import timezone

from houston.accounts.models import User
from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_CANCELED,
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_LIFECYCLE_EVENT_STARTED,
    EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
)
from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionLifecycleEvent
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
    execution_end_at_at,
    execution_status_at,
    first_signal_created_at,
    resolve_history_reliable_from,
    signal_status_at,
)
from houston.analytics.models import (
    OperationalPattern,
    PatternEstablishmentSighting,
    PatternLifecycleEvent,
    SignalPatternAssignment,
)
from houston.analytics.selectors import resolve_analytics_read_scope
from houston.establishments.management_scope import (
    management_establishment_ids_for_user,
)
from houston.establishments.membership_scope import (
    membership_business_unit_scope_ids,
    membership_scope_prefetch,
)
from houston.establishments.models import EstablishmentMembership
from houston.gamification.models import PointTransaction
from houston.signals.constants import (
    ACTIVE_SIGNAL_STATUSES,
    SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
    SIGNAL_LIFECYCLE_EVENT_CANCELED,
    SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
    SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
)
from houston.signals.models import Signal, SignalLifecycleEvent

DASHBOARD_PERIOD_DAYS = frozenset({3, 7, 15, 30, 90})
DEFAULT_DASHBOARD_PERIOD_DAYS = 7
NEW_PATTERNS_PREVIEW_LIMIT = 5
LOCATIONS_PREVIEW_LIMIT = 7
RECURRING_PATTERNS_LIMIT = 5
CONTRIBUTORS_LIMIT = 5
P90_MIN_SAMPLE = 10
AGING_OVER_15_DAYS = 15
UNASSIGNED_LABEL = "Sans pôle"
UNASSIGNED_LOCATION_KEY = "unassigned"
UNASSIGNED_LOCATION_LABEL = "Sans localisation"

SIGNAL_TERMINAL_STATUSES = frozenset(
    {
        Signal.Status.RESOLVED,
        Signal.Status.CANCELED,
        Signal.Status.ARCHIVED,
    }
)
EXECUTION_OPEN_STATUSES = frozenset(
    {
        EXECUTION_STATUS_IN_PROGRESS,
        EXECUTION_STATUS_PENDING_VALIDATION,
    }
)


@dataclass(frozen=True)
class DelayStats:
    median_seconds: float | None
    mean_seconds: float | None
    p90_seconds: float | None
    n: int
    comparison: DashboardMetricComparison
    undatable_in_scope: int
    unstarted_in_scope: int


@dataclass(frozen=True)
class UndatableSignalTerminals:
    canceled: int
    resolved: int
    archived: int


@dataclass(frozen=True)
class UndatableExecutionTerminals:
    canceled: int
    done: int


@dataclass(frozen=True)
class NamedCountItem:
    id: str
    name: str
    count: int
    establishment_id: UUID | None
    establishment_name: str | None
    comparison: DashboardMetricComparison


@dataclass(frozen=True)
class RecurringPatternItem:
    pattern_id: UUID
    name: str
    signal_count: int
    comparison: DashboardMetricComparison


@dataclass(frozen=True)
class NewPatternItem:
    pattern_id: UUID
    name: str
    first_seen_at: datetime
    observation_count: int
    establishment_count: int | None
    establishment_id: UUID | None
    establishment_name: str | None


@dataclass(frozen=True)
class ContributorItem:
    user_id: UUID
    name: str
    pts: int
    roles: tuple[str, ...]
    poles: tuple[str, ...]
    establishment_names: tuple[str, ...]


@dataclass(frozen=True)
class AgingBucket:
    key: str
    label: str
    count: int
    share: float | None


@dataclass(frozen=True)
class DeadlineShare:
    early: float | None
    on_time: float | None
    late: float | None
    n: int
    early_count: int
    on_time_count: int
    late_count: int
    early_comparison: DashboardMetricComparison
    on_time_comparison: DashboardMetricComparison
    late_comparison: DashboardMetricComparison


@dataclass(frozen=True)
class AnalyticsDashboardResult:
    period_days: int
    current_period: AnalyticsComparisonPeriod
    previous_period: AnalyticsComparisonPeriod
    history_reliable_from: datetime
    scope_type: str
    establishment_id: UUID | None
    establishment_ids: tuple[UUID, ...]
    recurring_patterns: tuple[RecurringPatternItem, ...]
    new_patterns: tuple[NewPatternItem, ...]
    new_patterns_preview_limit: int
    contributors: tuple[ContributorItem, ...]
    observation_delay_canceled: DelayStats
    observation_delay_resolved: DelayStats
    observation_delay_transformed: DelayStats
    operational_resolution_rate: DashboardMetricComparison
    closure_resolved_share: DashboardMetricComparison
    closure_measured_resolved_count: int
    closure_measured_canceled_count: int
    undatable_signal_terminals: UndatableSignalTerminals
    undatable_execution_terminals: UndatableExecutionTerminals
    reopenings: DashboardMetricComparison
    open_observation_count: int
    aging_buckets: tuple[AgingBucket, ...]
    aging_over_15d_share: DashboardMetricComparison
    plan_delay_canceled: DelayStats
    plan_delay_resolved: DelayStats
    plan_validation: DelayStats
    plan_deadlines: DeadlineShare
    locations: tuple[NamedCountItem, ...]
    locations_preview_limit: int
    poles: tuple[NamedCountItem, ...]


def get_analytics_dashboard(
    user: User | None,
    *,
    period_days: int = DEFAULT_DASHBOARD_PERIOD_DAYS,
    establishment_id: UUID | None = None,
    now: datetime | None = None,
) -> AnalyticsDashboardResult:
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
    if establishment_id is not None and establishment_id not in allowed_ids:
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
    signals = list(
        read_scope.readable_signals_queryset()
        .filter(merged_into__isnull=True)
        .select_related(
            "establishment",
            "operational_unit",
            "responsible_business_unit",
            "pattern_assignment__pattern__merged_into",
        )
        .prefetch_related("lifecycle_events")
    )
    signal_ids = [signal.id for signal in signals]
    if establishment_id is not None:
        establishment_ids = (establishment_id,)
    else:
        establishment_ids = tuple(sorted(allowed_ids))
    events_by_signal = _group_signal_events(signal_ids)
    executions = list(
        read_scope.readable_executions_queryset()
        .filter(establishment_id__in=establishment_ids)
        .select_related("establishment", "source_signal")
        .prefetch_related("lifecycle_events")
    )
    events_by_execution = _group_execution_events([execution.id for execution in executions])

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
    journal_coverage = comparison_coverage(current=journal_current, previous=journal_previous)
    complete_coverage = COVERAGE_COMPLETE
    undatable_signals = _undatable_signal_terminals(
        signals=signals,
        events_by_signal=events_by_signal,
    )
    undatable_executions = _undatable_execution_terminals(
        executions=executions,
        events_by_execution=events_by_execution,
    )

    recurring = _recurring_patterns(
        signals=signals,
        current_period=current_period,
        previous_period=previous_period,
    )
    new_patterns = _new_patterns(
        signals=signals,
        current_period=current_period,
        establishment_id=establishment_id,
    )
    contributors = _contributors(
        user=user,
        establishment_ids=establishment_ids,
        current_period=current_period,
    )
    obs_canceled = _signal_delay_stats(
        signals=signals,
        events_by_signal=events_by_signal,
        current_period=current_period,
        previous_period=previous_period,
        terminal_event=SIGNAL_LIFECYCLE_EVENT_CANCELED,
        coverage=journal_coverage,
        include_p90=True,
        undatable_in_scope=undatable_signals.canceled,
    )
    obs_resolved = _signal_delay_stats(
        signals=signals,
        events_by_signal=events_by_signal,
        current_period=current_period,
        previous_period=previous_period,
        terminal_event=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        coverage=journal_coverage,
        include_p90=True,
        undatable_in_scope=undatable_signals.resolved,
    )
    obs_transformed = _plan_transform_delay_stats(
        signals=signals,
        current_period=current_period,
        previous_period=previous_period,
        coverage=complete_coverage,
        include_p90=True,
        undatable_in_scope=0,
    )
    operational_rate = _operational_resolution(
        signals=signals,
        events_by_signal=events_by_signal,
        current_period=current_period,
        previous_period=previous_period,
        reliable_from=reliable_from,
        coverage=journal_coverage,
    )
    closure_share, measured_resolved, measured_canceled = _closure_resolved_share(
        signals=signals,
        events_by_signal=events_by_signal,
        current_period=current_period,
        previous_period=previous_period,
        current_coverage=journal_current,
        previous_coverage=journal_previous,
        coverage=journal_coverage,
        undatable_resolved=undatable_signals.resolved,
        undatable_canceled=undatable_signals.canceled,
    )
    reopenings = _reopening_counts(
        events_by_signal=events_by_signal,
        current_period=current_period,
        previous_period=previous_period,
        coverage=journal_coverage,
    )
    open_count, aging_buckets, aging_share = _observation_aging(
        signals=signals,
        events_by_signal=events_by_signal,
        now=moment,
        period_start=current_period.period_start,
        reliable_from=reliable_from,
    )
    plan_canceled = _execution_delay_stats(
        executions=executions,
        events_by_execution=events_by_execution,
        current_period=current_period,
        previous_period=previous_period,
        terminal_event=EXECUTION_LIFECYCLE_EVENT_CANCELED,
        coverage=journal_coverage,
        include_p90=False,
        undatable_in_scope=undatable_executions.canceled,
        unstarted_in_scope=_canceled_unstarted_execution_count(
            executions=executions,
            events_by_execution=events_by_execution,
        ),
    )
    plan_resolved = _execution_delay_stats(
        executions=executions,
        events_by_execution=events_by_execution,
        current_period=current_period,
        previous_period=previous_period,
        terminal_event=EXECUTION_LIFECYCLE_EVENT_VALIDATED,
        coverage=journal_coverage,
        include_p90=False,
        also_marked_done_done=True,
        undatable_in_scope=undatable_executions.done,
    )
    plan_validation = _validation_delay_stats(
        executions=executions,
        events_by_execution=events_by_execution,
        current_period=current_period,
        previous_period=previous_period,
        coverage=journal_coverage,
        undatable_in_scope=undatable_executions.done,
    )
    deadlines = _deadline_respect(
        executions=executions,
        events_by_execution=events_by_execution,
        current_period=current_period,
        previous_period=previous_period,
        reliable_from=reliable_from,
        now=moment,
        coverage=journal_coverage,
    )
    locations = _location_counts(
        signals=signals,
        current_period=current_period,
        previous_period=previous_period,
        cross=establishment_id is None,
    )
    poles = _dimension_counts(
        signals=signals,
        current_period=current_period,
        previous_period=previous_period,
        cross=establishment_id is None,
    )

    return AnalyticsDashboardResult(
        period_days=period_days,
        current_period=current_period,
        previous_period=previous_period,
        history_reliable_from=reliable_from,
        scope_type="establishment" if establishment_id is not None else "cross",
        establishment_id=establishment_id,
        establishment_ids=tuple(establishment_ids),
        recurring_patterns=recurring,
        new_patterns=new_patterns,
        new_patterns_preview_limit=NEW_PATTERNS_PREVIEW_LIMIT,
        contributors=contributors,
        observation_delay_canceled=obs_canceled,
        observation_delay_resolved=obs_resolved,
        observation_delay_transformed=obs_transformed,
        operational_resolution_rate=operational_rate,
        closure_resolved_share=closure_share,
        closure_measured_resolved_count=measured_resolved,
        closure_measured_canceled_count=measured_canceled,
        undatable_signal_terminals=undatable_signals,
        undatable_execution_terminals=undatable_executions,
        reopenings=reopenings,
        open_observation_count=open_count,
        aging_buckets=aging_buckets,
        aging_over_15d_share=aging_share,
        plan_delay_canceled=plan_canceled,
        plan_delay_resolved=plan_resolved,
        plan_validation=plan_validation,
        plan_deadlines=deadlines,
        locations=locations,
        locations_preview_limit=LOCATIONS_PREVIEW_LIMIT,
        poles=poles,
    )


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


def _duration_stats(
    values: list[float], *, include_p90: bool
) -> tuple[float | None, float | None, float | None, int]:
    n = len(values)
    if n == 0:
        return None, None, None, 0
    median = float(statistics.median(values))
    mean = float(statistics.fmean(values))
    p90 = None
    if include_p90 and n >= P90_MIN_SAMPLE:
        p90 = float(statistics.quantiles(values, n=10, method="inclusive")[8])
    return median, mean, p90, n


def _first_event_at(events: list[JournalEvent], event_type: str) -> datetime | None:
    for event in events:
        if event.event_type == event_type:
            return event.occurred_at
    return None


def _has_event(events: list[JournalEvent], event_type: str) -> bool:
    return any(event.event_type == event_type for event in events)


def _signal_canonical_terminal_at(signal: Signal, event_type: str) -> datetime | None:
    if event_type == SIGNAL_LIFECYCLE_EVENT_CANCELED:
        return signal.canceled_at
    if event_type == SIGNAL_LIFECYCLE_EVENT_RESOLVED:
        return signal.resolved_at
    if event_type == SIGNAL_LIFECYCLE_EVENT_ARCHIVED:
        return signal.archived_at
    return None


def _signal_measurable_terminal_at(
    events: list[JournalEvent],
    *,
    signal: Signal,
    event_type: str,
) -> datetime | None:
    return _first_event_at(events, event_type) or _signal_canonical_terminal_at(
        signal, event_type
    )


def _execution_done_canonical_at(execution: ActionPlanExecution) -> datetime | None:
    """DONE is dated by validate (`validated_at`) or mark-done without
    validation (`marked_done_at`).
    """
    if execution.validated_at is not None:
        return execution.validated_at
    return execution.marked_done_at


def _execution_measurable_cancel_at(
    events: list[JournalEvent],
    *,
    execution: ActionPlanExecution,
) -> datetime | None:
    return _first_event_at(events, EXECUTION_LIFECYCLE_EVENT_CANCELED) or execution.canceled_at


def _execution_measurable_done_at(
    events: list[JournalEvent],
    *,
    execution: ActionPlanExecution,
    also_marked_done_done: bool,
) -> datetime | None:
    for event in events:
        if event.event_type == EXECUTION_LIFECYCLE_EVENT_VALIDATED:
            return event.occurred_at
        if (
            also_marked_done_done
            and event.event_type == EXECUTION_LIFECYCLE_EVENT_MARKED_DONE
            and (event.metadata_safe.get("to_status") or EXECUTION_STATUS_DONE)
            == EXECUTION_STATUS_DONE
        ):
            return event.occurred_at
    return _execution_done_canonical_at(execution)


def _signal_is_undatable(
    signal: Signal,
    events: list[JournalEvent],
    *,
    status: str,
    event_type: str,
) -> bool:
    if signal.status != status:
        return False
    if _signal_canonical_terminal_at(signal, event_type) is not None:
        return False
    return not _has_event(events, event_type)


def _undatable_signal_terminals(
    *,
    signals: list[Signal],
    events_by_signal: dict[UUID, list[JournalEvent]],
) -> UndatableSignalTerminals:
    canceled = resolved = archived = 0
    for signal in signals:
        events = events_by_signal.get(signal.id, [])
        if _signal_is_undatable(
            signal,
            events,
            status=Signal.Status.CANCELED,
            event_type=SIGNAL_LIFECYCLE_EVENT_CANCELED,
        ):
            canceled += 1
        elif _signal_is_undatable(
            signal,
            events,
            status=Signal.Status.RESOLVED,
            event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        ):
            resolved += 1
        elif _signal_is_undatable(
            signal,
            events,
            status=Signal.Status.ARCHIVED,
            event_type=SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
        ):
            archived += 1
    return UndatableSignalTerminals(
        canceled=canceled,
        resolved=resolved,
        archived=archived,
    )


def _undatable_execution_terminals(
    *,
    executions: list[ActionPlanExecution],
    events_by_execution: dict[UUID, list[JournalEvent]],
) -> UndatableExecutionTerminals:
    canceled = done = 0
    for execution in executions:
        events = events_by_execution.get(execution.id, [])
        if execution.status == EXECUTION_STATUS_CANCELED:
            if execution.canceled_at is None and not _has_event(
                events, EXECUTION_LIFECYCLE_EVENT_CANCELED
            ):
                canceled += 1
            continue
        if execution.status != EXECUTION_STATUS_DONE:
            continue
        if execution.marked_done_at is not None or execution.validated_at is not None:
            continue
        if _has_event(events, EXECUTION_LIFECYCLE_EVENT_VALIDATED) or _has_event(
            events, EXECUTION_LIFECYCLE_EVENT_MARKED_DONE
        ):
            continue
        done += 1
    return UndatableExecutionTerminals(canceled=canceled, done=done)


def _canceled_unstarted_execution_count(
    *,
    executions: list[ActionPlanExecution],
    events_by_execution: dict[UUID, list[JournalEvent]],
) -> int:
    count = 0
    for execution in executions:
        events = events_by_execution.get(execution.id, [])
        if _execution_measurable_cancel_at(events, execution=execution) is None:
            continue
        if _first_started_at(events, fallback=execution.started_at) is None:
            count += 1
    return count


def _delay_from_values(
    *,
    current_values: list[float],
    previous_values: list[float],
    coverage: str,
    include_p90: bool,
    undatable_in_scope: int = 0,
    unstarted_in_scope: int = 0,
) -> DelayStats:
    median, mean, p90, n = _duration_stats(current_values, include_p90=include_p90)
    prev_median, _, _, _ = _duration_stats(previous_values, include_p90=include_p90)
    return DelayStats(
        median_seconds=median,
        mean_seconds=mean,
        p90_seconds=p90,
        n=n,
        comparison=compare_dashboard_metric_values(
            current=median,
            previous=prev_median,
            coverage=coverage,
        ),
        undatable_in_scope=undatable_in_scope,
        unstarted_in_scope=unstarted_in_scope,
    )


def _signal_delay_stats(
    *,
    signals: list[Signal],
    events_by_signal: dict[UUID, list[JournalEvent]],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    terminal_event: str,
    coverage: str,
    include_p90: bool,
    undatable_in_scope: int = 0,
) -> DelayStats:
    current: list[float] = []
    previous: list[float] = []
    for signal in signals:
        events = events_by_signal.get(signal.id, [])
        created_at = first_signal_created_at(events, fallback=signal.created_at)
        if created_at is None:
            continue
        first_terminal = _signal_measurable_terminal_at(
            events,
            signal=signal,
            event_type=terminal_event,
        )
        if first_terminal is None or first_terminal < created_at:
            continue
        duration = (first_terminal - created_at).total_seconds()
        if _in_period(first_terminal, current_period):
            current.append(duration)
        elif _in_period(first_terminal, previous_period):
            previous.append(duration)
    return _delay_from_values(
        current_values=current,
        previous_values=previous,
        coverage=coverage,
        include_p90=include_p90,
        undatable_in_scope=undatable_in_scope,
    )


def _plan_transform_delay_stats(
    *,
    signals: list[Signal],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    coverage: str,
    include_p90: bool,
    undatable_in_scope: int = 0,
) -> DelayStats:
    current: list[float] = []
    previous: list[float] = []
    for signal in signals:
        plan_at = signal.first_action_plan_associated_at
        start_at = signal.created_at
        if plan_at is None or start_at is None or plan_at < start_at:
            continue
        duration = (plan_at - start_at).total_seconds()
        if _in_period(plan_at, current_period):
            current.append(duration)
        elif _in_period(plan_at, previous_period):
            previous.append(duration)
    return _delay_from_values(
        current_values=current,
        previous_values=previous,
        coverage=coverage,
        include_p90=include_p90,
        undatable_in_scope=undatable_in_scope,
    )


def _first_started_at(events: list[JournalEvent], *, fallback: datetime | None) -> datetime | None:
    started = [
        event.occurred_at
        for event in events
        if event.event_type == EXECUTION_LIFECYCLE_EVENT_STARTED
    ]
    if started:
        return min(started)
    return fallback


def _execution_delay_stats(
    *,
    executions: list[ActionPlanExecution],
    events_by_execution: dict[UUID, list[JournalEvent]],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    terminal_event: str,
    coverage: str,
    include_p90: bool,
    also_marked_done_done: bool = False,
    undatable_in_scope: int = 0,
    unstarted_in_scope: int = 0,
) -> DelayStats:
    current: list[float] = []
    previous: list[float] = []
    for execution in executions:
        events = events_by_execution.get(execution.id, [])
        started_at = _first_started_at(events, fallback=execution.started_at)
        if started_at is None:
            continue
        if terminal_event == EXECUTION_LIFECYCLE_EVENT_CANCELED:
            first_terminal = _execution_measurable_cancel_at(events, execution=execution)
        else:
            first_terminal = _execution_measurable_done_at(
                events,
                execution=execution,
                also_marked_done_done=also_marked_done_done,
            )
        if first_terminal is None or first_terminal < started_at:
            continue
        duration = (first_terminal - started_at).total_seconds()
        if _in_period(first_terminal, current_period):
            current.append(duration)
        elif _in_period(first_terminal, previous_period):
            previous.append(duration)
    return _delay_from_values(
        current_values=current,
        previous_values=previous,
        coverage=coverage,
        include_p90=include_p90,
        undatable_in_scope=undatable_in_scope,
        unstarted_in_scope=unstarted_in_scope,
    )


def _validation_delay_stats(
    *,
    executions: list[ActionPlanExecution],
    events_by_execution: dict[UUID, list[JournalEvent]],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    coverage: str,
    undatable_in_scope: int = 0,
) -> DelayStats:
    current: list[float] = []
    previous: list[float] = []
    for execution in executions:
        events = events_by_execution.get(execution.id, [])
        pending_at = None
        validated_at = None
        for event in events:
            if (
                pending_at is None
                and event.event_type == EXECUTION_LIFECYCLE_EVENT_MARKED_DONE
                and event.metadata_safe.get("to_status") == EXECUTION_STATUS_PENDING_VALIDATION
            ):
                pending_at = event.occurred_at
            if event.event_type == EXECUTION_LIFECYCLE_EVENT_VALIDATED:
                validated_at = event.occurred_at
                break
        if pending_at is None:
            pending_at = (
                execution.marked_done_at
                if execution.requires_validation and execution.marked_done_at is not None
                else None
            )
        if validated_at is None:
            validated_at = execution.validated_at
        if pending_at is None or validated_at is None or validated_at < pending_at:
            continue
        duration = (validated_at - pending_at).total_seconds()
        if _in_period(validated_at, current_period):
            current.append(duration)
        elif _in_period(validated_at, previous_period):
            previous.append(duration)
    return _delay_from_values(
        current_values=current,
        previous_values=previous,
        coverage=coverage,
        include_p90=False,
        undatable_in_scope=undatable_in_scope,
    )


def _operational_resolution(
    *,
    signals: list[Signal],
    events_by_signal: dict[UUID, list[JournalEvent]],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    reliable_from: datetime,
    coverage: str,
) -> DashboardMetricComparison:
    def rate_for(period: AnalyticsComparisonPeriod) -> float | None:
        workload: set[UUID] = set()
        for signal in signals:
            events = events_by_signal.get(signal.id, [])
            status_at_start = signal_status_at(
                at=period.period_start,
                reliable_from=reliable_from,
                events=events,
            )
            created_at = first_signal_created_at(events, fallback=signal.created_at)
            if status_at_start is not None and status_at_start not in SIGNAL_TERMINAL_STATUSES:
                workload.add(signal.id)
            if created_at is not None and _in_period(created_at, period):
                workload.add(signal.id)
            for event in events:
                if event.event_type in {
                    SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
                    SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
                } and event.metadata_safe.get("from_status") == Signal.Status.RESOLVED:
                    if _in_period(event.occurred_at, period):
                        workload.add(signal.id)
        if not workload:
            return None
        resolved = 0
        for signal_id in workload:
            signal = next(item for item in signals if item.id == signal_id)
            status_at_end = signal_status_at(
                at=period.period_end,
                reliable_from=reliable_from,
                events=events_by_signal.get(signal.id, []),
            )
            if status_at_end == Signal.Status.RESOLVED:
                resolved += 1
        return resolved / len(workload)

    return compare_dashboard_metric_values(
        current=rate_for(current_period),
        previous=rate_for(previous_period),
        coverage=coverage,
        points=True,
    )


_CLOSURE_TERMINAL_EVENTS = frozenset(
    {
        SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        SIGNAL_LIFECYCLE_EVENT_CANCELED,
    }
)


def _last_journal_closure_event(
    events: list[JournalEvent],
    period: AnalyticsComparisonPeriod,
) -> JournalEvent | None:
    last = None
    for event in events:
        if event.event_type in _CLOSURE_TERMINAL_EVENTS and _in_period(
            event.occurred_at, period
        ):
            last = event
    return last


def _last_column_closure_event_type(
    signal: Signal,
    period: AnalyticsComparisonPeriod,
) -> str | None:
    candidates: list[tuple[datetime, str]] = []
    if signal.resolved_at is not None and _in_period(signal.resolved_at, period):
        candidates.append((signal.resolved_at, SIGNAL_LIFECYCLE_EVENT_RESOLVED))
    if signal.canceled_at is not None and _in_period(signal.canceled_at, period):
        candidates.append((signal.canceled_at, SIGNAL_LIFECYCLE_EVENT_CANCELED))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def _closure_counts_for_period(
    *,
    signals: list[Signal],
    events_by_signal: dict[UUID, list[JournalEvent]],
    period: AnalyticsComparisonPeriod,
    coverage: str,
) -> tuple[int, int]:
    resolved = 0
    canceled = 0
    allow_column_fallback = coverage != COVERAGE_COMPLETE
    for signal in signals:
        events = events_by_signal.get(signal.id, [])
        last_event = _last_journal_closure_event(events, period)
        if last_event is not None:
            event_type = last_event.event_type
        elif allow_column_fallback:
            event_type = _last_column_closure_event_type(signal, period)
        else:
            event_type = None
        if event_type == SIGNAL_LIFECYCLE_EVENT_RESOLVED:
            resolved += 1
        elif event_type == SIGNAL_LIFECYCLE_EVENT_CANCELED:
            canceled += 1
    return resolved, canceled


def _closure_resolved_share(
    *,
    signals: list[Signal],
    events_by_signal: dict[UUID, list[JournalEvent]],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    current_coverage: str,
    previous_coverage: str,
    coverage: str,
    undatable_resolved: int,
    undatable_canceled: int,
) -> tuple[DashboardMetricComparison, int, int]:
    current_resolved, current_canceled = _closure_counts_for_period(
        signals=signals,
        events_by_signal=events_by_signal,
        period=current_period,
        coverage=current_coverage,
    )
    previous_resolved, previous_canceled = _closure_counts_for_period(
        signals=signals,
        events_by_signal=events_by_signal,
        period=previous_period,
        coverage=previous_coverage,
    )
    withhold_ratio = (undatable_resolved + undatable_canceled) > 0

    def share(resolved: int, canceled: int) -> float | None:
        denominator = resolved + canceled
        if denominator == 0:
            return None
        return resolved / denominator

    comparison = compare_dashboard_metric_values(
        current=None if withhold_ratio else share(current_resolved, current_canceled),
        previous=None if withhold_ratio else share(previous_resolved, previous_canceled),
        coverage=coverage,
        points=True,
    )
    return comparison, current_resolved, current_canceled


def _reopening_counts(
    *,
    events_by_signal: dict[UUID, list[JournalEvent]],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    coverage: str,
) -> DashboardMetricComparison:
    def count_for(period: AnalyticsComparisonPeriod) -> int:
        reopened: set[UUID] = set()
        for signal_id, events in events_by_signal.items():
            for event in events:
                if event.event_type in {
                    SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
                    SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
                } and event.metadata_safe.get("from_status") == Signal.Status.RESOLVED:
                    if _in_period(event.occurred_at, period):
                        reopened.add(signal_id)
        return len(reopened)

    return compare_dashboard_metric_values(
        current=count_for(current_period),
        previous=count_for(previous_period),
        coverage=coverage,
    )


def _aging_bucket(age_days: float) -> str:
    if age_days < 3:
        return "< 3 j"
    if age_days < 8:
        return "3–7 j"
    if age_days <= 15:
        return "8–15 j"
    return "> 15 j"


def _observation_aging(
    *,
    signals: list[Signal],
    events_by_signal: dict[UUID, list[JournalEvent]],
    now: datetime,
    period_start: datetime,
    reliable_from: datetime,
) -> tuple[int, tuple[AgingBucket, ...], DashboardMetricComparison]:
    open_now = [signal for signal in signals if signal.status in ACTIVE_SIGNAL_STATUSES]
    total = len(open_now)
    counts = {"< 3 j": 0, "3–7 j": 0, "8–15 j": 0, "> 15 j": 0}
    for signal in open_now:
        age_days = (now - signal.created_at).total_seconds() / 86400
        counts[_aging_bucket(age_days)] += 1
    buckets = tuple(
        AgingBucket(
            key=key,
            label=key,
            count=count,
            share=(count / total) if total else None,
        )
        for key, count in counts.items()
    )
    current_share = (counts["> 15 j"] / total) if total else None

    previous_coverage = coverage_for_window(
        window_start=period_start,
        window_end=now,
        reliable_from=reliable_from,
        needs_journal=True,
        previous_end=period_start,
    )
    previous_open = []
    if previous_coverage == COVERAGE_COMPLETE:
        for signal in signals:
            status = signal_status_at(
                at=period_start,
                reliable_from=reliable_from,
                events=events_by_signal.get(signal.id, []),
            )
            if status in ACTIVE_SIGNAL_STATUSES:
                previous_open.append(signal)
    previous_total = len(previous_open)
    previous_over = 0
    for signal in previous_open:
        age_days = (period_start - signal.created_at).total_seconds() / 86400
        if age_days > AGING_OVER_15_DAYS:
            previous_over += 1
    previous_share = (previous_over / previous_total) if previous_total else None
    aging_coverage = (
        COVERAGE_COMPLETE if previous_coverage == COVERAGE_COMPLETE else previous_coverage
    )
    return (
        total,
        buckets,
        compare_dashboard_metric_values(
            current=current_share,
            previous=previous_share,
            coverage=aging_coverage,
            points=True,
        ),
    )


def _recurring_patterns(
    *,
    signals: list[Signal],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
) -> tuple[RecurringPatternItem, ...]:
    """Widget 8.1: ≥2 surviving Signals in the dashboard period, live canonical motif."""
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
    for pattern_id, payload in recurrent[:RECURRING_PATTERNS_LIMIT]:
        items.append(
            RecurringPatternItem(
                pattern_id=pattern_id,
                name=payload["name"],
                signal_count=payload["count"],
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
    establishment_id: UUID | None,
) -> tuple[NewPatternItem, ...]:
    assigned = [
        signal
        for signal in signals
        if getattr(signal, "pattern_assignment", None) is not None
        and signal.pattern_assignment.pattern_id is not None
        and (establishment_id is None or signal.establishment_id == establishment_id)
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
    )
    if establishment_id is not None:
        sighting_qs = sighting_qs.filter(establishment_id=establishment_id)
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
        if establishment_id is None:
            items.append(
                NewPatternItem(
                    pattern_id=canonical_id,
                    name=pattern.label,
                    first_seen_at=first_seen,
                    observation_count=len(related_signals),
                    establishment_count=len(
                        {signal.establishment_id for signal in related_signals}
                    ),
                    establishment_id=None,
                    establishment_name=None,
                )
            )
            continue
        items.append(
            NewPatternItem(
                pattern_id=canonical_id,
                name=pattern.label,
                first_seen_at=first_seen,
                observation_count=len(related_signals),
                establishment_count=None,
                establishment_id=establishment_id,
                establishment_name=related_signals[0].establishment.name,
            )
        )

    items.sort(key=lambda item: item.first_seen_at, reverse=True)
    return tuple(items)


def _contributors(
    *,
    user: User | None,
    establishment_ids: tuple[UUID, ...],
    current_period: AnalyticsComparisonPeriod,
) -> tuple[ContributorItem, ...]:
    if not establishment_ids:
        return ()
    rows = list(
        PointTransaction.objects.filter(
            establishment_id__in=establishment_ids,
            occurred_at__gte=current_period.period_start,
            occurred_at__lt=current_period.period_end,
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
    cross: bool,
) -> tuple[NamedCountItem, ...]:
    def key_for(signal: Signal) -> tuple:
        dim_id = _normalized_location_key(signal.location_text)
        if cross:
            return (signal.establishment_id, dim_id, signal.establishment.name)
        return (None, dim_id, None)

    def counts_for(
        period: AnalyticsComparisonPeriod,
    ) -> tuple[dict[tuple, int], dict[tuple, dict[str, int]]]:
        grouped: dict[tuple, int] = defaultdict(int)
        spellings: dict[tuple, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for signal in signals:
            if not _in_period(signal.created_at, period):
                continue
            key = key_for(signal)
            grouped[key] += 1
            stripped = (signal.location_text or "").strip()
            if key[1] != UNASSIGNED_LOCATION_KEY:
                spellings[key][stripped] += 1
        return grouped, spellings

    current, current_spellings = counts_for(current_period)
    previous, _ = counts_for(previous_period)
    items = []
    for key, count in current.items():
        establishment_id, dim_id, establishment_name = key
        item_id = dim_id
        if establishment_id is not None:
            item_id = f"{establishment_id}:{item_id}"
        items.append(
            NamedCountItem(
                id=item_id,
                name=_location_display_name(
                    dim_id=dim_id,
                    spellings=current_spellings.get(key, {}),
                ),
                count=count,
                establishment_id=establishment_id,
                establishment_name=establishment_name,
                comparison=compare_dashboard_metric_values(
                    current=count,
                    previous=previous.get(key, 0),
                    coverage=COVERAGE_COMPLETE,
                ),
            )
        )
    items.sort(key=lambda item: (-item.count, item.name))
    return tuple(items)


def _dimension_counts(
    *,
    signals: list[Signal],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    cross: bool,
) -> tuple[NamedCountItem, ...]:
    def key_for(signal: Signal) -> tuple:
        dim_id = signal.responsible_business_unit_id
        name = (
            _dimension_label(signal.responsible_business_unit)
            if signal.responsible_business_unit_id
            else UNASSIGNED_LABEL
        )
        if cross:
            return (signal.establishment_id, dim_id, name, signal.establishment.name)
        return (None, dim_id, name, None)

    def counts_for(period: AnalyticsComparisonPeriod) -> dict[tuple, int]:
        grouped: dict[tuple, int] = defaultdict(int)
        for signal in signals:
            if not _in_period(signal.created_at, period):
                continue
            grouped[key_for(signal)] += 1
        return grouped

    current = counts_for(current_period)
    previous = counts_for(previous_period)
    items = []
    for key, count in current.items():
        establishment_id, dim_id, name, establishment_name = key
        item_id = str(dim_id) if dim_id is not None else "unassigned"
        if establishment_id is not None:
            item_id = f"{establishment_id}:{item_id}"
        items.append(
            NamedCountItem(
                id=item_id,
                name=name,
                count=count,
                establishment_id=establishment_id,
                establishment_name=establishment_name,
                comparison=compare_dashboard_metric_values(
                    current=count,
                    previous=previous.get(key, 0),
                    coverage=COVERAGE_COMPLETE,
                ),
            )
        )
    items.sort(key=lambda item: (-item.count, item.name))
    return tuple(items)


def _dimension_label(business_unit) -> str:
    if business_unit is None:
        return UNASSIGNED_LABEL
    value = (getattr(business_unit, "specific_name", None) or "").strip()
    return value or UNASSIGNED_LABEL


def _local_date(moment: datetime, timezone_name: str):
    try:
        tzinfo = ZoneInfo(timezone_name or "Europe/Paris")
    except ZoneInfoNotFoundError:
        tzinfo = ZoneInfo("Europe/Paris")
    return timezone.localtime(moment, tzinfo).date()


def _deadline_respect(
    *,
    executions: list[ActionPlanExecution],
    events_by_execution: dict[UUID, list[JournalEvent]],
    current_period: AnalyticsComparisonPeriod,
    previous_period: AnalyticsComparisonPeriod,
    reliable_from: datetime,
    now: datetime,
    coverage: str,
) -> DeadlineShare:
    def shares_for(
        *,
        at: datetime,
        period: AnalyticsComparisonPeriod | None,
    ) -> tuple[float | None, float | None, float | None, int, int, int, int]:
        early = on_time = late = 0
        for execution in executions:
            events = events_by_execution.get(execution.id, [])
            end_at = execution_end_at_at(
                at=at,
                reliable_from=reliable_from,
                events=events,
            )
            if end_at is None:
                continue
            status = execution_status_at(
                at=at,
                reliable_from=reliable_from,
                events=events,
            )
            if status == EXECUTION_STATUS_CANCELED:
                continue
            tz_name = execution.establishment.timezone or "Europe/Paris"
            due_day = _local_date(end_at, tz_name)

            if status == EXECUTION_STATUS_DONE:
                validated = None
                for event in events:
                    if event.event_type == EXECUTION_LIFECYCLE_EVENT_VALIDATED:
                        validated = event.occurred_at
                        break
                    if (
                        event.event_type == EXECUTION_LIFECYCLE_EVENT_MARKED_DONE
                        and event.metadata_safe.get("to_status") == EXECUTION_STATUS_DONE
                    ):
                        validated = event.occurred_at
                if validated is None:
                    continue
                if period is not None and not _in_period(validated, period):
                    continue
                done_day = _local_date(validated, tz_name)
                if done_day < due_day:
                    early += 1
                elif done_day == due_day:
                    on_time += 1
                else:
                    late += 1
            elif status in EXECUTION_OPEN_STATUSES:
                if _local_date(at, tz_name) > due_day:
                    late += 1
        total = early + on_time + late
        if total == 0:
            return None, None, None, 0, 0, 0, 0
        return early / total, on_time / total, late / total, total, early, on_time, late

    cur_early, cur_on_time, cur_late, n, early_count, on_time_count, late_count = shares_for(
        at=now,
        period=current_period,
    )
    prev_early, prev_on_time, prev_late, _prev_n, _pe, _po, _pl = shares_for(
        at=current_period.period_start,
        period=previous_period,
    )
    return DeadlineShare(
        early=cur_early,
        on_time=cur_on_time,
        late=cur_late,
        n=n,
        early_count=early_count,
        on_time_count=on_time_count,
        late_count=late_count,
        early_comparison=compare_dashboard_metric_values(
            current=cur_early, previous=prev_early, coverage=coverage, points=True
        ),
        on_time_comparison=compare_dashboard_metric_values(
            current=cur_on_time, previous=prev_on_time, coverage=coverage, points=True
        ),
        late_comparison=compare_dashboard_metric_values(
            current=cur_late, previous=prev_late, coverage=coverage, points=True
        ),
    )
