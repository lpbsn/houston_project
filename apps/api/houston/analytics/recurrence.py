from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from django.db.models import Count, DateField, DateTimeField, F, Func, Max, QuerySet
from django.db.models.functions import Cast
from django.utils import timezone

from houston.accounts.models import User
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.selectors import analytics_recurrence_signals_queryset

RECURRENCE_WINDOW_DAYS = 30
RECURRENCE_MIN_OCCURRENCES = 3
RECURRENCE_MIN_DISTINCT_DAYS = 2
RECURRENCE_STATUS_COMPUTED = "computed"


@dataclass(frozen=True)
class AnalyticsRecurrenceWindow:
    window_start: datetime
    window_end: datetime


@dataclass(frozen=True)
class PatternRecurrenceStats:
    pattern_id: UUID
    is_recurrent: bool
    occurrence_count_30d: int
    distinct_day_count_30d: int
    window: AnalyticsRecurrenceWindow
    last_occurrence_at: datetime | None


def build_recurrence_window(as_of: datetime) -> AnalyticsRecurrenceWindow:
    _validate_recurrence_as_of(as_of)
    return AnalyticsRecurrenceWindow(
        window_start=as_of - timedelta(days=RECURRENCE_WINDOW_DAYS),
        window_end=as_of,
    )


def analytics_pattern_recurrence_stats(
    user: User | None,
    *,
    as_of: datetime,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
    pattern_ids=None,
) -> dict[UUID, PatternRecurrenceStats]:
    _validate_establishment_scope(
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )
    window = build_recurrence_window(as_of)
    rows = _recurrence_rows(
        user,
        window=window,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
        pattern_ids=pattern_ids,
    )
    return {
        row["pattern_id"]: _stats_from_row(row, window=window)
        for row in rows
    }


def recurrence_stats_for_visible_pattern_ids(
    user: User | None,
    *,
    as_of: datetime,
    visible_pattern_ids,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> dict[UUID, PatternRecurrenceStats]:
    _validate_establishment_scope(
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )
    pattern_ids = list(visible_pattern_ids)
    if not pattern_ids:
        return {}

    window = build_recurrence_window(as_of)
    sparse = analytics_pattern_recurrence_stats(
        user,
        as_of=as_of,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
        pattern_ids=pattern_ids,
    )
    return {
        pattern_id: sparse.get(pattern_id)
        or PatternRecurrenceStats(
            pattern_id=pattern_id,
            is_recurrent=False,
            occurrence_count_30d=0,
            distinct_day_count_30d=0,
            window=window,
            last_occurrence_at=None,
        )
        for pattern_id in pattern_ids
    }


def recurrent_pattern_ids_queryset(
    user: User | None,
    *,
    as_of: datetime,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
    pattern_ids=None,
) -> QuerySet:
    _validate_establishment_scope(
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )
    window = build_recurrence_window(as_of)
    return (
        _recurrence_rows(
            user,
            window=window,
            organization_id=organization_id,
            establishment_id=establishment_id,
            establishment_ids=establishment_ids,
            pattern_ids=pattern_ids,
        )
        .filter(
            occurrence_count_30d__gte=RECURRENCE_MIN_OCCURRENCES,
            distinct_day_count_30d__gte=RECURRENCE_MIN_DISTINCT_DAYS,
        )
        .values("pattern_id")
    )


def recurrent_patterns_count_for_contributors(
    user: User | None,
    *,
    as_of: datetime,
    contributor_pattern_ids,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> int:
    return (
        recurrent_pattern_ids_queryset(
            user,
            as_of=as_of,
            organization_id=organization_id,
            establishment_id=establishment_id,
            establishment_ids=establishment_ids,
            pattern_ids=contributor_pattern_ids,
        )
        .distinct()
        .count()
    )


def _recurrence_rows(
    user: User | None,
    *,
    window: AnalyticsRecurrenceWindow,
    organization_id,
    establishment_id,
    establishment_ids,
    pattern_ids=None,
) -> QuerySet:
    recurrence_signals = analytics_recurrence_signals_queryset(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    ).filter(
        created_at__gte=window.window_start,
        created_at__lt=window.window_end,
    )
    assignments = SignalPatternAssignment.objects.filter(
        signal_id__in=recurrence_signals.values("id"),
        pattern_id__isnull=False,
    )
    if pattern_ids is not None:
        assignments = assignments.filter(pattern_id__in=pattern_ids)

    return (
        assignments.annotate(
            local_day=Cast(
                Func(
                    F("signal__establishment__timezone"),
                    F("signal__created_at"),
                    function="timezone",
                    output_field=DateTimeField(),
                ),
                output_field=DateField(),
            )
        )
        .values("pattern_id")
        .annotate(
            occurrence_count_30d=Count("signal_id", distinct=True),
            distinct_day_count_30d=Count("local_day", distinct=True),
            last_occurrence_at=Max("signal__created_at"),
        )
    )


def _stats_from_row(row, *, window: AnalyticsRecurrenceWindow) -> PatternRecurrenceStats:
    occurrence_count = int(row["occurrence_count_30d"])
    distinct_day_count = int(row["distinct_day_count_30d"])
    return PatternRecurrenceStats(
        pattern_id=row["pattern_id"],
        is_recurrent=(
            occurrence_count >= RECURRENCE_MIN_OCCURRENCES
            and distinct_day_count >= RECURRENCE_MIN_DISTINCT_DAYS
        ),
        occurrence_count_30d=occurrence_count,
        distinct_day_count_30d=distinct_day_count,
        window=window,
        last_occurrence_at=row["last_occurrence_at"],
    )


def _validate_recurrence_as_of(as_of: datetime | None) -> None:
    if as_of is None:
        raise AnalyticsValidationError(
            "as_of is required for analytics recurrence.",
            code="analytics_recurrence_as_of_required",
        )
    if timezone.is_naive(as_of):
        raise AnalyticsValidationError(
            "as_of must be timezone-aware.",
            code="analytics_recurrence_as_of_naive",
        )


def _validate_establishment_scope(*, establishment_id, establishment_ids) -> None:
    if establishment_id is not None and establishment_ids is not None:
        raise AnalyticsValidationError(
            "Use either establishment_id or establishment_ids, not both.",
            code="analytics_scope_invalid",
        )
