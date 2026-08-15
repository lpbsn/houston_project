from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Case, Count, IntegerField, Max, QuerySet, Value, When
from django.db.models.functions import TruncDate

from houston.accounts.models import User
from houston.analytics.comparisons import (
    AnalyticsComparisonPeriod,
    MetricComparison,
    build_adjacent_comparison_periods,
    compare_metric_values,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.permissions import analytics_accessible_establishment_ids_for_user
from houston.analytics.recurrence import (
    RECURRENCE_STATUS_COMPUTED,
    AnalyticsRecurrenceWindow,
    build_recurrence_window,
    recurrence_stats_for_visible_pattern_ids,
)
from houston.analytics.selectors import resolve_analytics_read_scope
from houston.establishments.models import DEFAULT_ESTABLISHMENT_TIMEZONE, Establishment
from houston.signals.models import Signal

MAX_PATTERN_DETAIL_ESTABLISHMENTS = 20
MAX_PATTERN_DETAIL_BUSINESS_UNITS = 20
TREND_TIMEZONE_UTC = "UTC"
UNASSIGNED_BUSINESS_UNIT_LABEL = "Unassigned"


@dataclass(frozen=True)
class AnalyticsPatternIdentity:
    pattern_id: uuid.UUID
    label: str
    status: str
    created_at: datetime
    merged_into_pattern_id: uuid.UUID | None


@dataclass(frozen=True)
class AnalyticsPatternDetailMetrics:
    signal_count: int
    previous_signal_count: int
    signal_count_comparison: MetricComparison
    actionable_signal_count: int
    last_seen_at: datetime
    establishment_count: int


@dataclass(frozen=True)
class AnalyticsPatternTrendBucket:
    bucket_date: date
    bucket_start: datetime
    bucket_end: datetime
    signal_count: int


@dataclass(frozen=True)
class AnalyticsPatternStatusDistributionBucket:
    status: str
    signal_count: int


@dataclass(frozen=True)
class AnalyticsPatternEstablishmentDistributionBucket:
    establishment_id: uuid.UUID
    name: str
    signal_count: int


@dataclass(frozen=True)
class AnalyticsPatternBusinessUnitDistributionBucket:
    business_unit_id: uuid.UUID | None
    name: str
    signal_count: int


@dataclass(frozen=True)
class AnalyticsPatternDrilldownContext:
    pattern_id: uuid.UUID
    period_start: datetime
    period_end: datetime
    organization_id: uuid.UUID | None
    establishment_id: uuid.UUID | None


@dataclass(frozen=True)
class AnalyticsPatternDetailResult:
    identity: AnalyticsPatternIdentity
    current_period: AnalyticsComparisonPeriod
    previous_period: AnalyticsComparisonPeriod
    metrics: AnalyticsPatternDetailMetrics
    is_recurrent: bool
    occurrence_count_30d: int
    distinct_day_count_30d: int
    recurrence_window: AnalyticsRecurrenceWindow
    recurrence_status: str
    trend_timezone: str
    trend: tuple[AnalyticsPatternTrendBucket, ...]
    status_distribution: tuple[AnalyticsPatternStatusDistributionBucket, ...]
    establishments: tuple[AnalyticsPatternEstablishmentDistributionBucket, ...]
    establishment_bucket_count: int
    establishment_other_signal_count: int
    responsible_business_units: tuple[
        AnalyticsPatternBusinessUnitDistributionBucket,
        ...,
    ]
    business_unit_bucket_count: int
    business_unit_other_signal_count: int
    drilldown_context: AnalyticsPatternDrilldownContext


def get_analytics_pattern_detail(
    user: User | None,
    *,
    pattern_id,
    period_start: datetime,
    period_end: datetime,
    organization_id=None,
    establishment_id=None,
) -> AnalyticsPatternDetailResult:
    current_period, previous_period = build_adjacent_comparison_periods(
        period_start=period_start,
        period_end=period_end,
    )
    parsed_pattern_id = _parse_pattern_id(pattern_id)
    read_scope = resolve_analytics_read_scope(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
    )
    current_signals = _filter_created_period(
        read_scope.default_signals_queryset(),
        period=current_period,
    )
    pattern_rows = _current_pattern_rows(current_signals, pattern_id=parsed_pattern_id)
    if not pattern_rows:
        raise AnalyticsValidationError(
            "Analytics pattern was not found.",
            code="analytics_pattern_not_found",
        )

    pattern_ids = [parsed_pattern_id]
    previous_signal_count = _pattern_count_for_signals(
        _filter_created_period(
            read_scope.default_signals_queryset(),
            period=previous_period,
        ),
        pattern_id=parsed_pattern_id,
    )
    actionable_signal_count = _pattern_count_for_signals(
        _filter_created_period(
            read_scope.actionable_signals_queryset(),
            period=current_period,
        ),
        pattern_id=parsed_pattern_id,
    )
    recurrence = recurrence_stats_for_visible_pattern_ids(
        user,
        as_of=current_period.period_end,
        visible_pattern_ids=pattern_ids,
        organization_id=organization_id,
        establishment_id=establishment_id,
        _read_scope=read_scope,
    )[parsed_pattern_id]
    recurrence_window = build_recurrence_window(current_period.period_end)
    trend_timezone = _resolve_trend_timezone_name(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
    )
    trend_tz = ZoneInfo(trend_timezone)
    status_distribution = _status_distribution_from_rows(pattern_rows)
    establishment_bucket_count, establishments, establishment_other_signal_count = (
        _establishment_distribution(current_signals, pattern_id=parsed_pattern_id)
    )
    business_unit_bucket_count, business_units, business_unit_other_signal_count = (
        _responsible_business_unit_distribution(
            current_signals,
            pattern_id=parsed_pattern_id,
        )
    )
    pattern_row = pattern_rows[0]
    signal_count = sum(int(row["signal_count"]) for row in pattern_rows)
    last_seen_at = max(row["last_seen_at"] for row in pattern_rows)

    return AnalyticsPatternDetailResult(
        identity=AnalyticsPatternIdentity(
            pattern_id=parsed_pattern_id,
            label=pattern_row["pattern__label"],
            status=pattern_row["pattern__status"],
            created_at=pattern_row["pattern__created_at"],
            merged_into_pattern_id=pattern_row["pattern__merged_into_id"],
        ),
        current_period=current_period,
        previous_period=previous_period,
        metrics=AnalyticsPatternDetailMetrics(
            signal_count=signal_count,
            previous_signal_count=previous_signal_count,
            signal_count_comparison=compare_metric_values(
                current=signal_count,
                previous=previous_signal_count,
            ),
            actionable_signal_count=actionable_signal_count,
            last_seen_at=last_seen_at,
            establishment_count=establishment_bucket_count,
        ),
        is_recurrent=recurrence.is_recurrent,
        occurrence_count_30d=recurrence.occurrence_count_30d,
        distinct_day_count_30d=recurrence.distinct_day_count_30d,
        recurrence_window=recurrence_window,
        recurrence_status=RECURRENCE_STATUS_COMPUTED,
        trend_timezone=trend_timezone,
        trend=_trend_buckets(
            current_signals,
            pattern_id=parsed_pattern_id,
            period=current_period,
            trend_tz=trend_tz,
        ),
        status_distribution=status_distribution,
        establishments=establishments,
        establishment_bucket_count=establishment_bucket_count,
        establishment_other_signal_count=establishment_other_signal_count,
        responsible_business_units=business_units,
        business_unit_bucket_count=business_unit_bucket_count,
        business_unit_other_signal_count=business_unit_other_signal_count,
        drilldown_context=AnalyticsPatternDrilldownContext(
            pattern_id=parsed_pattern_id,
            period_start=current_period.period_start,
            period_end=current_period.period_end,
            organization_id=organization_id,
            establishment_id=establishment_id,
        ),
    )


def _parse_pattern_id(pattern_id) -> uuid.UUID:
    try:
        return uuid.UUID(str(pattern_id))
    except (TypeError, ValueError) as exc:
        raise AnalyticsValidationError(
            "Analytics pattern was not found.",
            code="analytics_pattern_not_found",
        ) from exc


def _filter_created_period(
    queryset: QuerySet[Signal],
    *,
    period: AnalyticsComparisonPeriod,
) -> QuerySet[Signal]:
    return queryset.filter(
        created_at__gte=period.period_start,
        created_at__lt=period.period_end,
    )


def _current_pattern_rows(
    queryset: QuerySet[Signal],
    *,
    pattern_id: uuid.UUID,
):
    return list(
        SignalPatternAssignment.objects.filter(
            signal_id__in=queryset.values("id"),
            pattern_id=pattern_id,
        )
        .values(
            "pattern__label",
            "pattern__status",
            "pattern__created_at",
            "pattern__merged_into_id",
            "signal__status",
        )
        .annotate(
            signal_count=Count("signal_id", distinct=True),
            last_seen_at=Max("signal__created_at"),
        )
        .order_by("signal__status")
    )


def _pattern_count_for_signals(
    queryset: QuerySet[Signal],
    *,
    pattern_id: uuid.UUID,
) -> int:
    return (
        SignalPatternAssignment.objects.filter(
            signal_id__in=queryset.values("id"),
            pattern_id=pattern_id,
        )
        .values("pattern_id")
        .annotate(signal_count=Count("signal_id", distinct=True))
        .order_by("pattern_id")
        .values_list("signal_count", flat=True)
        .first()
        or 0
    )


def _resolve_trend_timezone_name(
    user: User | None,
    *,
    organization_id,
    establishment_id,
) -> str:
    if establishment_id is not None:
        return (
            Establishment.objects.filter(pk=establishment_id)
            .values_list("timezone", flat=True)
            .first()
            or DEFAULT_ESTABLISHMENT_TIMEZONE
        )

    establishment_ids = analytics_accessible_establishment_ids_for_user(
        user,
        organization_id=organization_id,
    )
    if len(establishment_ids) == 1:
        return (
            Establishment.objects.filter(pk=establishment_ids[0])
            .values_list("timezone", flat=True)
            .first()
            or DEFAULT_ESTABLISHMENT_TIMEZONE
        )
    return TREND_TIMEZONE_UTC


def _trend_buckets(
    queryset: QuerySet[Signal],
    *,
    pattern_id: uuid.UUID,
    period: AnalyticsComparisonPeriod,
    trend_tz: ZoneInfo,
) -> tuple[AnalyticsPatternTrendBucket, ...]:
    rows = (
        SignalPatternAssignment.objects.filter(
            signal_id__in=queryset.values("id"),
            pattern_id=pattern_id,
        )
        .annotate(bucket_date=TruncDate("signal__created_at", tzinfo=trend_tz))
        .values("bucket_date")
        .annotate(signal_count=Count("signal_id", distinct=True))
    )
    counts = {row["bucket_date"]: int(row["signal_count"]) for row in rows}
    return tuple(
        AnalyticsPatternTrendBucket(
            bucket_date=bucket_date,
            bucket_start=bucket_start,
            bucket_end=bucket_end,
            signal_count=counts.get(bucket_date, 0),
        )
        for bucket_date, bucket_start, bucket_end in _iter_daily_buckets(
            period=period,
            trend_tz=trend_tz,
        )
    )


def _iter_daily_buckets(
    *,
    period: AnalyticsComparisonPeriod,
    trend_tz: ZoneInfo,
):
    local_period_start = period.period_start.astimezone(trend_tz)
    local_period_end = period.period_end.astimezone(trend_tz)
    bucket_date = period.period_start.astimezone(trend_tz).date()
    while True:
        bucket_start = datetime.combine(bucket_date, time.min, tzinfo=trend_tz)
        if bucket_start >= local_period_end:
            break
        next_date = bucket_date + timedelta(days=1)
        bucket_end = datetime.combine(next_date, time.min, tzinfo=trend_tz)
        if bucket_end > local_period_start:
            yield (
                bucket_date,
                max(bucket_start, local_period_start),
                min(bucket_end, local_period_end),
            )
        bucket_date = next_date


def _status_distribution_from_rows(
    rows,
) -> tuple[AnalyticsPatternStatusDistributionBucket, ...]:
    counts = {row["signal__status"]: int(row["signal_count"]) for row in rows}
    return tuple(
        AnalyticsPatternStatusDistributionBucket(
            status=status,
            signal_count=counts.get(status, 0),
        )
        for status, _label in Signal.Status.choices
    )


def _establishment_distribution(
    queryset: QuerySet[Signal],
    *,
    pattern_id: uuid.UUID,
) -> tuple[
    int,
    tuple[AnalyticsPatternEstablishmentDistributionBucket, ...],
    int,
]:
    rows = list(
        SignalPatternAssignment.objects.filter(
            signal_id__in=queryset.values("id"),
            pattern_id=pattern_id,
        )
        .values(
            "signal__establishment_id",
            "signal__establishment__name",
        )
        .annotate(signal_count=Count("signal_id", distinct=True))
        .order_by(
            "-signal_count",
            "signal__establishment__name",
            "signal__establishment_id",
        )
    )
    summaries = tuple(
        AnalyticsPatternEstablishmentDistributionBucket(
            establishment_id=row["signal__establishment_id"],
            name=row["signal__establishment__name"],
            signal_count=int(row["signal_count"]),
        )
        for row in rows[:MAX_PATTERN_DETAIL_ESTABLISHMENTS]
    )
    top_signal_count = sum(summary.signal_count for summary in summaries)
    total_signal_count = sum(int(row["signal_count"]) for row in rows)
    return len(rows), summaries, total_signal_count - top_signal_count


def _responsible_business_unit_distribution(
    queryset: QuerySet[Signal],
    *,
    pattern_id: uuid.UUID,
) -> tuple[
    int,
    tuple[AnalyticsPatternBusinessUnitDistributionBucket, ...],
    int,
]:
    rows = list(
        SignalPatternAssignment.objects.filter(
            signal_id__in=queryset.values("id"),
            pattern_id=pattern_id,
        )
        .values(
            "signal__responsible_business_unit_id",
            "signal__responsible_business_unit__specific_name",
        )
        .annotate(signal_count=Count("signal_id", distinct=True))
        .annotate(
            business_unit_is_null=Case(
                When(signal__responsible_business_unit_id__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
        )
    )
    rows.sort(
        key=lambda row: (
            -int(row["signal_count"]),
            int(row["business_unit_is_null"]),
            row["signal__responsible_business_unit__specific_name"]
            or UNASSIGNED_BUSINESS_UNIT_LABEL,
            str(row["signal__responsible_business_unit_id"] or ""),
        )
    )
    summaries = tuple(
        AnalyticsPatternBusinessUnitDistributionBucket(
            business_unit_id=row["signal__responsible_business_unit_id"],
            name=(
                row["signal__responsible_business_unit__specific_name"]
                or UNASSIGNED_BUSINESS_UNIT_LABEL
            ),
            signal_count=int(row["signal_count"]),
        )
        for row in rows[:MAX_PATTERN_DETAIL_BUSINESS_UNITS]
    )
    top_signal_count = sum(summary.signal_count for summary in summaries)
    total_signal_count = sum(int(row["signal_count"]) for row in rows)
    return len(rows), summaries, total_signal_count - top_signal_count
