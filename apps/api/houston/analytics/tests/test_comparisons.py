from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from houston.analytics.comparisons import (
    RELATIVE_CHANGE_COMPUTED,
    RELATIVE_CHANGE_NOT_APPLICABLE,
    RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO,
    build_adjacent_comparison_periods,
    compare_dashboard_metric_values,
    compare_metric_values,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.journal import (
    COVERAGE_COMPLETE,
    COVERAGE_NOT_COMPARABLE,
    COVERAGE_PARTIAL,
)


def test_previous_period_is_adjacent_same_duration():
    period_start = datetime(2026, 3, 8, tzinfo=UTC)
    period_end = period_start + timedelta(days=7)

    current, previous = build_adjacent_comparison_periods(
        period_start=period_start,
        period_end=period_end,
    )

    assert current.period_start == period_start
    assert current.period_end == period_end
    assert previous.period_start == period_start - timedelta(days=7)
    assert previous.period_end == period_start


@pytest.mark.parametrize("days", [7, 30, 90])
def test_adjacent_periods_support_product_period_lengths(days):
    period_end = datetime(2026, 3, 15, tzinfo=UTC)
    period_start = period_end - timedelta(days=days)

    current, previous = build_adjacent_comparison_periods(
        period_start=period_start,
        period_end=period_end,
    )

    assert current.period_start == period_start
    assert current.period_end == period_end
    assert previous.period_start == period_start - timedelta(days=days)
    assert previous.period_end == period_start


@pytest.mark.parametrize(
    ("period_start", "period_end", "expected_code"),
    [
        (None, "end", "analytics_comparison_period_required"),
        ("start", None, "analytics_comparison_period_required"),
        (datetime(2026, 1, 1), "end", "analytics_period_start_naive"),
        ("same", "same", "analytics_period_invalid"),
        ("end", "start", "analytics_period_invalid"),
    ],
)
def test_comparison_rejects_open_naive_empty_or_inverted_periods(
    period_start,
    period_end,
    expected_code,
):
    start = datetime(2026, 3, 1, tzinfo=UTC)
    end = start + timedelta(days=7)
    values = {
        "start": start,
        "end": end,
        "same": start,
        None: None,
    }

    with pytest.raises(AnalyticsValidationError) as exc_info:
        build_adjacent_comparison_periods(
            period_start=values.get(period_start, period_start),
            period_end=values.get(period_end, period_end),
        )

    assert exc_info.value.code == expected_code


def test_relative_change_is_ratio_and_previous_zero_is_undefined():
    undefined = compare_metric_values(current=2, previous=0)
    assert undefined.absolute_delta == 2
    assert undefined.relative_change is None
    assert undefined.relative_change_status == RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO

    computed = compare_metric_values(current=2, previous=1)
    assert computed.absolute_delta == 1
    assert computed.relative_change == 1
    assert computed.relative_change_status == RELATIVE_CHANGE_COMPUTED


def test_none_metric_values_are_not_applicable():
    result = compare_metric_values(current=None, previous=None)
    assert result.absolute_delta is None
    assert result.relative_change is None
    assert result.relative_change_status == RELATIVE_CHANGE_NOT_APPLICABLE


@pytest.mark.parametrize("coverage", [COVERAGE_PARTIAL, COVERAGE_NOT_COMPARABLE])
def test_incomplete_dashboard_coverage_withholds_delta(coverage):
    result = compare_dashboard_metric_values(
        current=10,
        previous=5,
        coverage=coverage,
    )
    assert result.current_value == 10
    assert result.previous_value == 5
    assert result.absolute_delta is None
    assert result.relative_change is None
    assert result.relative_change_status == RELATIVE_CHANGE_NOT_APPLICABLE
    assert result.coverage == coverage


def test_complete_dashboard_coverage_uses_comparison_formula():
    result = compare_dashboard_metric_values(
        current=10,
        previous=5,
        coverage=COVERAGE_COMPLETE,
    )
    assert result.absolute_delta == 5
    assert result.relative_change == 1
    assert result.relative_change_status == RELATIVE_CHANGE_COMPUTED
    assert result.coverage == COVERAGE_COMPLETE


def test_complete_dashboard_points_comparison_uses_absolute_points():
    result = compare_dashboard_metric_values(
        current=0.61,
        previous=0.54,
        coverage=COVERAGE_COMPLETE,
        points=True,
    )
    assert result.relative_change == pytest.approx(0.07)
    assert result.relative_change_status == RELATIVE_CHANGE_COMPUTED
