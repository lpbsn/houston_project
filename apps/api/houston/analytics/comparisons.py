from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from houston.analytics.exceptions import AnalyticsValidationError

RELATIVE_CHANGE_COMPUTED = "computed"
RELATIVE_CHANGE_NOT_APPLICABLE = "not_applicable"
RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO = "undefined_previous_zero"


@dataclass(frozen=True)
class AnalyticsComparisonPeriod:
    period_start: datetime
    period_end: datetime


@dataclass(frozen=True)
class MetricComparison:
    current_value: int | float | None
    previous_value: int | float | None
    absolute_delta: int | float | None
    relative_change: float | None
    relative_change_status: str


def build_adjacent_comparison_periods(
    *,
    period_start: datetime,
    period_end: datetime,
) -> tuple[AnalyticsComparisonPeriod, AnalyticsComparisonPeriod]:
    _validate_comparison_period(period_start=period_start, period_end=period_end)
    duration = period_end - period_start
    previous_start = period_start - duration
    return (
        AnalyticsComparisonPeriod(period_start=period_start, period_end=period_end),
        AnalyticsComparisonPeriod(period_start=previous_start, period_end=period_start),
    )


def _validate_comparison_period(
    *,
    period_start: datetime | None,
    period_end: datetime | None,
) -> None:
    if period_start is None or period_end is None:
        raise AnalyticsValidationError(
            "period_start and period_end are required for analytics comparisons.",
            code="analytics_comparison_period_required",
        )
    for field_name, value in (
        ("period_start", period_start),
        ("period_end", period_end),
    ):
        if timezone.is_naive(value):
            raise AnalyticsValidationError(
                f"{field_name} must be timezone-aware.",
                code=f"analytics_{field_name}_naive",
            )
    if period_start >= period_end:
        raise AnalyticsValidationError(
            "period_start must be before period_end.",
            code="analytics_period_invalid",
        )


def compare_metric_values(
    *,
    current: int | float | None,
    previous: int | float | None,
) -> MetricComparison:
    if current is None or previous is None:
        return MetricComparison(
            current_value=current,
            previous_value=previous,
            absolute_delta=None,
            relative_change=None,
            relative_change_status=RELATIVE_CHANGE_NOT_APPLICABLE,
        )

    absolute_delta = current - previous
    if previous == 0:
        return MetricComparison(
            current_value=current,
            previous_value=previous,
            absolute_delta=absolute_delta,
            relative_change=None,
            relative_change_status=RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO,
        )

    return MetricComparison(
        current_value=current,
        previous_value=previous,
        absolute_delta=absolute_delta,
        relative_change=absolute_delta / previous,
        relative_change_status=RELATIVE_CHANGE_COMPUTED,
    )


@dataclass(frozen=True)
class DashboardMetricComparison:
    current_value: int | float | None
    previous_value: int | float | None
    absolute_delta: int | float | None
    relative_change: float | None
    relative_change_status: str
    coverage: str


def compare_dashboard_metric_values(
    *,
    current: int | float | None,
    previous: int | float | None,
    coverage: str,
    points: bool = False,
) -> DashboardMetricComparison:
    from houston.analytics.journal import COVERAGE_COMPLETE

    if coverage != COVERAGE_COMPLETE:
        return DashboardMetricComparison(
            current_value=current,
            previous_value=previous,
            absolute_delta=None,
            relative_change=None,
            relative_change_status=RELATIVE_CHANGE_NOT_APPLICABLE,
            coverage=coverage,
        )
    base = compare_metric_values(current=current, previous=previous)
    relative_change = base.relative_change
    relative_status = base.relative_change_status
    if (
        points
        and current is not None
        and previous is not None
        and previous != 0
    ):
        relative_change = current - previous
        relative_status = RELATIVE_CHANGE_COMPUTED
    elif points and current is not None and previous == 0:
        relative_change = None
        relative_status = RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO
    return DashboardMetricComparison(
        current_value=base.current_value,
        previous_value=base.previous_value,
        absolute_delta=base.absolute_delta,
        relative_change=relative_change,
        relative_change_status=relative_status,
        coverage=coverage,
    )
