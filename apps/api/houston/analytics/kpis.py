from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db.models import (
    Aggregate,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    Q,
    QuerySet,
)
from django.utils import timezone

from houston.accounts.models import User
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.recurrence import (
    RECURRENCE_STATUS_COMPUTED,
    AnalyticsRecurrenceWindow,
    build_recurrence_window,
    recurrent_patterns_count_for_contributors,
)
from houston.analytics.selectors import (
    AnalyticsReadScope,
    resolve_analytics_read_scope,
)
from houston.analytics.status_matrix import actionable_signal_q
from houston.signals.models import Signal


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
    recurring_patterns_count: int
    recurrence_window: AnalyticsRecurrenceWindow
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
    recurrence_as_of: datetime | None = None,
    _read_scope: AnalyticsReadScope | None = None,
) -> AnalyticsKPIResult:
    _validate_period(period_start=period_start, period_end=period_end)
    recurrence_as_of = _resolve_recurrence_as_of(
        period_end=period_end,
        recurrence_as_of=recurrence_as_of,
    )
    recurrence_window = build_recurrence_window(recurrence_as_of)
    read_scope = _read_scope or resolve_analytics_read_scope(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
    )

    population = _filter_created_period(
        read_scope.default_signals_queryset(),
        period_start=period_start,
        period_end=period_end,
    )
    population_stats = population.aggregate(
        population_count=Count("id", distinct=True),
        actionable_count=Count(
            "id",
            filter=actionable_signal_q(),
            distinct=True,
        ),
    )
    population_count = int(population_stats["population_count"])

    assignments = SignalPatternAssignment.objects.filter(
        signal_id__in=population.values("id")
    )
    assignment_stats = _assignment_stats(assignments)
    signals_analyzed_count = assignment_stats["signals_analyzed_count"]
    contributor_pattern_ids = (
        assignments.filter(pattern__isnull=False).values("pattern_id").distinct()
    )
    technical_state = _technical_classification_state(
        assignment_stats=assignment_stats,
        total_count=population_count,
    )

    actionable_count = int(population_stats["actionable_count"])
    operational_patterns_count = assignment_stats["operational_patterns_count"]
    recurring_patterns_count = recurrent_patterns_count_for_contributors(
        user,
        as_of=recurrence_as_of,
        contributor_pattern_ids=contributor_pattern_ids,
        organization_id=organization_id,
        establishment_id=establishment_id,
        _read_scope=read_scope,
    )

    resolution_stats = _resolution_time_stats(
        read_scope,
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
        recurring_patterns_count=recurring_patterns_count,
        recurrence_window=recurrence_window,
        recurrence_status=RECURRENCE_STATUS_COMPUTED,
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


def _resolve_recurrence_as_of(
    *,
    period_end: datetime | None,
    recurrence_as_of: datetime | None,
) -> datetime:
    resolved = recurrence_as_of or period_end
    if resolved is None:
        raise AnalyticsValidationError(
            "recurrence_as_of or period_end is required for analytics recurrence.",
            code="analytics_recurrence_as_of_required",
        )
    if timezone.is_naive(resolved):
        raise AnalyticsValidationError(
            "recurrence_as_of must be timezone-aware.",
            code="analytics_recurrence_as_of_naive",
        )
    return resolved


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
    assignment_stats: dict[str, int],
    total_count: int,
) -> TechnicalClassificationState:
    breakdown = {
        "missing_assignment": total_count - assignment_stats["assignment_count"],
        SignalPatternAssignment.ClassificationStatus.NOT_STARTED: assignment_stats[
            "not_started_count"
        ],
        SignalPatternAssignment.ClassificationStatus.PROCESSING: assignment_stats[
            "processing_count"
        ],
        SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED: assignment_stats[
            "temporary_failed_count"
        ],
        SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED: assignment_stats[
            "permanently_failed_count"
        ],
        SignalPatternAssignment.ClassificationStatus.SUCCEEDED: assignment_stats[
            "succeeded_count"
        ],
    }

    success_count = breakdown[SignalPatternAssignment.ClassificationStatus.SUCCEEDED]
    return TechnicalClassificationState(
        total_count=total_count,
        technical_state_breakdown=breakdown,
        technical_terminal_success_count=success_count,
        technical_pending_or_error_count=total_count - success_count,
    )


def _assignment_stats(
    assignments: QuerySet[SignalPatternAssignment],
) -> dict[str, int]:
    raw = assignments.aggregate(
        assignment_count=Count("id"),
        signals_analyzed_count=Count(
            "id",
            filter=Q(pattern_id__isnull=False),
        ),
        operational_patterns_count=Count("pattern_id", distinct=True),
        not_started_count=Count(
            "id",
            filter=Q(
                classification_status=(
                    SignalPatternAssignment.ClassificationStatus.NOT_STARTED
                )
            ),
        ),
        processing_count=Count(
            "id",
            filter=Q(
                classification_status=(
                    SignalPatternAssignment.ClassificationStatus.PROCESSING
                )
            ),
        ),
        temporary_failed_count=Count(
            "id",
            filter=Q(
                classification_status=(
                    SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED
                )
            ),
        ),
        permanently_failed_count=Count(
            "id",
            filter=Q(
                classification_status=(
                    SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED
                )
            ),
        ),
        succeeded_count=Count(
            "id",
            filter=Q(
                classification_status=(
                    SignalPatternAssignment.ClassificationStatus.SUCCEEDED
                )
            ),
        ),
    )
    return {key: int(value) for key, value in raw.items()}


def _resolution_time_stats(
    read_scope: AnalyticsReadScope,
    *,
    period_start: datetime | None,
    period_end: datetime | None,
) -> dict[str, int | float | None]:
    resolution_queryset = _filter_resolved_period(
        read_scope.resolution_time_signals_queryset(),
        period_start=period_start,
        period_end=period_end,
    )
    stats = resolution_queryset.annotate(
        resolution_duration=ExpressionWrapper(
            F("resolved_at") - F("created_at"),
            output_field=DurationField(),
        )
    ).aggregate(
        invalid_count=Count(
            "id",
            filter=Q(resolved_at__lt=F("created_at")),
            distinct=True,
        ),
        valid_count=Count(
            "id",
            filter=Q(resolved_at__gte=F("created_at")),
            distinct=True,
        ),
        median=PercentileCont(
            "resolution_duration",
            percentile=0.5,
            filter=Q(resolved_at__gte=F("created_at")),
        ),
    )

    return {
        "resolution_time_signal_count": int(stats["valid_count"]),
        "invalid_resolution_duration_count": int(stats["invalid_count"]),
        "median_resolution_seconds": _duration_seconds(stats["median"]),
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
