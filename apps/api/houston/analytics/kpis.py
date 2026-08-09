from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db.models import (
    Aggregate,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    QuerySet,
)
from django.utils import timezone

from houston.accounts.models import User
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.selectors import (
    analytics_actionable_signals_queryset,
    analytics_default_signals_queryset,
    analytics_resolution_time_signals_queryset,
)
from houston.signals.models import Signal

RECURRENCE_STATUS_NOT_COMPUTED = "not_computed_until_ticket_16"


@dataclass(frozen=True)
class BusinessAssignmentCoverage:
    total_count: int
    with_pattern_count: int
    without_pattern_count: int
    coverage_rate: float | None


@dataclass(frozen=True)
class TechnicalClassificationState:
    total_count: int
    technical_state_breakdown: dict[str, int]
    technical_terminal_success_count: int
    technical_pending_or_error_count: int


@dataclass(frozen=True)
class AnalyticsKPIResult:
    analytics_signal_population_count: int
    signals_analyzed_count: int
    operational_patterns_count: int
    actionable_signals_count: int
    median_resolution_seconds: float | None
    resolution_time_signal_count: int
    invalid_resolution_duration_count: int
    business_assignment_coverage: BusinessAssignmentCoverage
    technical_classification_state: TechnicalClassificationState
    recurring_patterns_count: int | None
    recurrence_status: str


class PercentileCont(Aggregate):
    function = "PERCENTILE_CONT"
    name = "PercentileCont"
    template = "%(function)s(%(percentile)s) WITHIN GROUP (ORDER BY %(expressions)s)"
    output_field = DurationField()

    def __init__(self, expression, *, percentile: float, **extra):
        super().__init__(expression, percentile=percentile, **extra)


def get_analytics_kpis(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> AnalyticsKPIResult:
    _validate_period(period_start=period_start, period_end=period_end)

    population = _filter_created_period(
        analytics_default_signals_queryset(
            user,
            organization_id=organization_id,
            establishment_id=establishment_id,
        ),
        period_start=period_start,
        period_end=period_end,
    )
    population_count = population.count()

    assignments = SignalPatternAssignment.objects.filter(
        signal_id__in=population.values("id")
    )
    signals_analyzed_count = assignments.filter(pattern__isnull=False).count()
    technical_state = _technical_classification_state(
        assignments=assignments,
        total_count=population_count,
    )

    actionable_count = _filter_created_period(
        analytics_actionable_signals_queryset(
            user,
            organization_id=organization_id,
            establishment_id=establishment_id,
        ),
        period_start=period_start,
        period_end=period_end,
    ).count()

    operational_patterns_count = (
        assignments.filter(pattern__isnull=False)
        .values("pattern_id")
        .distinct()
        .count()
    )

    resolution_stats = _resolution_time_stats(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
        period_start=period_start,
        period_end=period_end,
    )

    return AnalyticsKPIResult(
        analytics_signal_population_count=population_count,
        signals_analyzed_count=signals_analyzed_count,
        operational_patterns_count=operational_patterns_count,
        actionable_signals_count=actionable_count,
        median_resolution_seconds=resolution_stats["median_resolution_seconds"],
        resolution_time_signal_count=resolution_stats["resolution_time_signal_count"],
        invalid_resolution_duration_count=resolution_stats[
            "invalid_resolution_duration_count"
        ],
        business_assignment_coverage=BusinessAssignmentCoverage(
            total_count=population_count,
            with_pattern_count=signals_analyzed_count,
            without_pattern_count=population_count - signals_analyzed_count,
            coverage_rate=_rate(
                numerator=signals_analyzed_count,
                denominator=population_count,
            ),
        ),
        technical_classification_state=technical_state,
        recurring_patterns_count=None,
        recurrence_status=RECURRENCE_STATUS_NOT_COMPUTED,
    )


def _validate_period(
    *,
    period_start: datetime | None,
    period_end: datetime | None,
) -> None:
    for field_name, value in (
        ("period_start", period_start),
        ("period_end", period_end),
    ):
        if value is not None and timezone.is_naive(value):
            raise AnalyticsValidationError(
                f"{field_name} must be timezone-aware.",
                code=f"analytics_{field_name}_naive",
            )
    if period_start is not None and period_end is not None and period_start >= period_end:
        raise AnalyticsValidationError(
            "period_start must be before period_end.",
            code="analytics_period_invalid",
        )


def _filter_created_period(
    queryset: QuerySet[Signal],
    *,
    period_start: datetime | None,
    period_end: datetime | None,
) -> QuerySet[Signal]:
    if period_start is not None:
        queryset = queryset.filter(created_at__gte=period_start)
    if period_end is not None:
        queryset = queryset.filter(created_at__lt=period_end)
    return queryset


def _filter_resolved_period(
    queryset: QuerySet[Signal],
    *,
    period_start: datetime | None,
    period_end: datetime | None,
) -> QuerySet[Signal]:
    if period_start is not None:
        queryset = queryset.filter(resolved_at__gte=period_start)
    if period_end is not None:
        queryset = queryset.filter(resolved_at__lt=period_end)
    return queryset


def _technical_classification_state(
    *,
    assignments: QuerySet[SignalPatternAssignment],
    total_count: int,
) -> TechnicalClassificationState:
    breakdown = {
        "missing_assignment": 0,
        SignalPatternAssignment.ClassificationStatus.NOT_STARTED: 0,
        SignalPatternAssignment.ClassificationStatus.PROCESSING: 0,
        SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED: 0,
        SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED: 0,
        SignalPatternAssignment.ClassificationStatus.SUCCEEDED: 0,
    }
    status_counts = assignments.values("classification_status").annotate(count=Count("id"))
    assignment_count = 0
    for row in status_counts:
        count = int(row["count"])
        breakdown[row["classification_status"]] = count
        assignment_count += count
    breakdown["missing_assignment"] = total_count - assignment_count

    success_count = breakdown[SignalPatternAssignment.ClassificationStatus.SUCCEEDED]
    return TechnicalClassificationState(
        total_count=total_count,
        technical_state_breakdown=breakdown,
        technical_terminal_success_count=success_count,
        technical_pending_or_error_count=total_count - success_count,
    )


def _resolution_time_stats(
    user: User | None,
    *,
    organization_id,
    establishment_id,
    period_start: datetime | None,
    period_end: datetime | None,
) -> dict[str, int | float | None]:
    resolution_queryset = _filter_resolved_period(
        analytics_resolution_time_signals_queryset(
            user,
            organization_id=organization_id,
            establishment_id=establishment_id,
        ),
        period_start=period_start,
        period_end=period_end,
    )
    invalid_count = resolution_queryset.filter(resolved_at__lt=F("created_at")).count()
    valid_queryset = resolution_queryset.filter(resolved_at__gte=F("created_at"))
    valid_count = valid_queryset.count()
    median_duration = None
    if valid_count:
        median_duration = valid_queryset.annotate(
            resolution_duration=ExpressionWrapper(
                F("resolved_at") - F("created_at"),
                output_field=DurationField(),
            )
        ).aggregate(
            median=PercentileCont("resolution_duration", percentile=0.5),
        )["median"]

    return {
        "resolution_time_signal_count": valid_count,
        "invalid_resolution_duration_count": invalid_count,
        "median_resolution_seconds": _duration_seconds(median_duration),
    }


def _duration_seconds(value: timedelta | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, timedelta):
        return value.total_seconds()
    return float(value)


def _rate(*, numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator
