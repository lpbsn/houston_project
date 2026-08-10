from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Count, Max, Q, QuerySet
from django.utils.dateparse import parse_datetime

from houston.accounts.models import User
from houston.analytics.comparisons import (
    AnalyticsComparisonPeriod,
    MetricComparison,
    build_adjacent_comparison_periods,
    compare_metric_values,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.kpis import RECURRENCE_STATUS_NOT_COMPUTED
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.selectors import (
    analytics_actionable_signals_queryset,
    analytics_default_signals_queryset,
)
from houston.signals.models import Signal

PATTERN_LIST_CURSOR_VERSION = "analytics_pattern_list_v1"
DEFAULT_PATTERN_LIST_PAGE_SIZE = 50
MAX_PATTERN_LIST_PAGE_SIZE = 100
MAX_PATTERN_LIST_ESTABLISHMENTS = 5


@dataclass(frozen=True)
class AnalyticsPatternEstablishmentSummary:
    establishment_id: uuid.UUID
    name: str
    signal_count: int


@dataclass(frozen=True)
class AnalyticsPatternListItem:
    pattern_id: uuid.UUID
    label: str
    normalized_label: str
    status: str
    signal_count: int
    previous_signal_count: int
    signal_count_comparison: MetricComparison
    last_seen_at: datetime
    actionable_signal_count: int
    establishment_count: int
    establishments: tuple[AnalyticsPatternEstablishmentSummary, ...]
    recurrence_status: str


@dataclass(frozen=True)
class AnalyticsPatternListResult:
    current_period: AnalyticsComparisonPeriod
    previous_period: AnalyticsComparisonPeriod
    items: tuple[AnalyticsPatternListItem, ...]
    total_count: int
    page_size: int
    has_more: bool
    next_cursor: str | None
    recurrence_status: str


@dataclass(frozen=True)
class _PatternListCursor:
    signal_count: int
    last_seen_at: datetime
    normalized_label: str
    pattern_id: uuid.UUID


def list_analytics_patterns(
    user: User | None,
    *,
    period_start: datetime,
    period_end: datetime,
    organization_id=None,
    establishment_id=None,
    page_size: int = DEFAULT_PATTERN_LIST_PAGE_SIZE,
    cursor: str | None = None,
) -> AnalyticsPatternListResult:
    current_period, previous_period = build_adjacent_comparison_periods(
        period_start=period_start,
        period_end=period_end,
    )
    validated_page_size = _validate_page_size(page_size)
    context = _cursor_context(
        user=user,
        period=current_period,
        organization_id=organization_id,
        establishment_id=establishment_id,
        page_size=validated_page_size,
    )
    parsed_cursor = _parse_cursor(cursor, expected_context=context)

    current_signals = _filter_created_period(
        analytics_default_signals_queryset(
            user,
            organization_id=organization_id,
            establishment_id=establishment_id,
        ),
        period=current_period,
    )
    current_rows = _current_pattern_rows(current_signals)
    total_count = current_rows.count()
    page_queryset = _apply_cursor(current_rows, parsed_cursor)
    page_rows = list(page_queryset[: validated_page_size + 1])
    has_more = len(page_rows) > validated_page_size
    served_rows = page_rows[:validated_page_size]
    pattern_ids = [row["pattern_id"] for row in served_rows]

    previous_counts = _pattern_counts_for_signals(
        _filter_created_period(
            analytics_default_signals_queryset(
                user,
                organization_id=organization_id,
                establishment_id=establishment_id,
            ),
            period=previous_period,
        ),
        pattern_ids=pattern_ids,
    )
    actionable_counts = _pattern_counts_for_signals(
        _filter_created_period(
            analytics_actionable_signals_queryset(
                user,
                organization_id=organization_id,
                establishment_id=establishment_id,
            ),
            period=current_period,
        ),
        pattern_ids=pattern_ids,
    )
    establishment_counts, establishments = _establishment_summaries(
        current_signals,
        pattern_ids=pattern_ids,
    )

    items = tuple(
        _item_from_row(
            row,
            previous_counts=previous_counts,
            actionable_counts=actionable_counts,
            establishment_counts=establishment_counts,
            establishments=establishments,
        )
        for row in served_rows
    )
    next_cursor = None
    if has_more and items:
        next_cursor = _encode_cursor(context=context, item=items[-1])

    return AnalyticsPatternListResult(
        current_period=current_period,
        previous_period=previous_period,
        items=items,
        total_count=total_count,
        page_size=validated_page_size,
        has_more=has_more,
        next_cursor=next_cursor,
        recurrence_status=RECURRENCE_STATUS_NOT_COMPUTED,
    )


def _current_pattern_rows(queryset: QuerySet[Signal]):
    return (
        SignalPatternAssignment.objects.filter(
            signal_id__in=queryset.values("id"),
            pattern_id__isnull=False,
        )
        .values(
            "pattern_id",
            "pattern__label",
            "pattern__normalized_label",
            "pattern__status",
        )
        .annotate(
            signal_count=Count("signal_id", distinct=True),
            last_seen_at=Max("signal__created_at"),
        )
        .order_by(
            "-signal_count",
            "-last_seen_at",
            "pattern__normalized_label",
            "pattern_id",
        )
    )


def _apply_cursor(queryset, cursor: _PatternListCursor | None):
    if cursor is None:
        return queryset
    return queryset.filter(
        Q(signal_count__lt=cursor.signal_count)
        | Q(signal_count=cursor.signal_count, last_seen_at__lt=cursor.last_seen_at)
        | Q(
            signal_count=cursor.signal_count,
            last_seen_at=cursor.last_seen_at,
            pattern__normalized_label__gt=cursor.normalized_label,
        )
        | Q(
            signal_count=cursor.signal_count,
            last_seen_at=cursor.last_seen_at,
            pattern__normalized_label=cursor.normalized_label,
            pattern_id__gt=cursor.pattern_id,
        )
    )


def _pattern_counts_for_signals(
    queryset: QuerySet[Signal],
    *,
    pattern_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not pattern_ids:
        return {}
    rows = (
        SignalPatternAssignment.objects.filter(
            signal_id__in=queryset.values("id"),
            pattern_id__in=pattern_ids,
        )
        .values("pattern_id")
        .annotate(signal_count=Count("signal_id", distinct=True))
    )
    return {row["pattern_id"]: int(row["signal_count"]) for row in rows}


def _establishment_summaries(
    queryset: QuerySet[Signal],
    *,
    pattern_ids: list[uuid.UUID],
) -> tuple[
    dict[uuid.UUID, int],
    dict[uuid.UUID, tuple[AnalyticsPatternEstablishmentSummary, ...]],
]:
    if not pattern_ids:
        return {}, {}
    rows = (
        SignalPatternAssignment.objects.filter(
            signal_id__in=queryset.values("id"),
            pattern_id__in=pattern_ids,
        )
        .values(
            "pattern_id",
            "signal__establishment_id",
            "signal__establishment__name",
        )
        .annotate(signal_count=Count("signal_id", distinct=True))
        .order_by(
            "pattern_id",
            "-signal_count",
            "signal__establishment__name",
            "signal__establishment_id",
        )
    )
    total_counts: dict[uuid.UUID, int] = {}
    grouped: dict[uuid.UUID, list[AnalyticsPatternEstablishmentSummary]] = {}
    for row in rows:
        pattern_id = row["pattern_id"]
        total_counts[pattern_id] = total_counts.get(pattern_id, 0) + 1
        summaries = grouped.setdefault(pattern_id, [])
        if len(summaries) >= MAX_PATTERN_LIST_ESTABLISHMENTS:
            continue
        summaries.append(
            AnalyticsPatternEstablishmentSummary(
                establishment_id=row["signal__establishment_id"],
                name=row["signal__establishment__name"],
                signal_count=int(row["signal_count"]),
            )
        )
    return total_counts, {
        pattern_id: tuple(summaries) for pattern_id, summaries in grouped.items()
    }


def _item_from_row(
    row,
    *,
    previous_counts: dict[uuid.UUID, int],
    actionable_counts: dict[uuid.UUID, int],
    establishment_counts: dict[uuid.UUID, int],
    establishments: dict[uuid.UUID, tuple[AnalyticsPatternEstablishmentSummary, ...]],
) -> AnalyticsPatternListItem:
    pattern_id = row["pattern_id"]
    signal_count = int(row["signal_count"])
    previous_signal_count = previous_counts.get(pattern_id, 0)
    return AnalyticsPatternListItem(
        pattern_id=pattern_id,
        label=row["pattern__label"],
        normalized_label=row["pattern__normalized_label"],
        status=row["pattern__status"],
        signal_count=signal_count,
        previous_signal_count=previous_signal_count,
        signal_count_comparison=compare_metric_values(
            current=signal_count,
            previous=previous_signal_count,
        ),
        last_seen_at=row["last_seen_at"],
        actionable_signal_count=actionable_counts.get(pattern_id, 0),
        establishment_count=establishment_counts.get(pattern_id, 0),
        establishments=establishments.get(pattern_id, ()),
        recurrence_status=RECURRENCE_STATUS_NOT_COMPUTED,
    )


def _validate_page_size(page_size: int) -> int:
    try:
        parsed = int(page_size)
    except (TypeError, ValueError) as exc:
        raise AnalyticsValidationError(
            "page_size must be an integer.",
            code="analytics_pattern_list_page_size_invalid",
        ) from exc
    if parsed < 1 or parsed > MAX_PATTERN_LIST_PAGE_SIZE:
        raise AnalyticsValidationError(
            f"page_size must be between 1 and {MAX_PATTERN_LIST_PAGE_SIZE}.",
            code="analytics_pattern_list_page_size_invalid",
        )
    return parsed


def _filter_created_period(
    queryset: QuerySet[Signal],
    *,
    period: AnalyticsComparisonPeriod,
) -> QuerySet[Signal]:
    return queryset.filter(
        created_at__gte=period.period_start,
        created_at__lt=period.period_end,
    )


def _cursor_context(
    *,
    user: User | None,
    period: AnalyticsComparisonPeriod,
    organization_id,
    establishment_id,
    page_size: int,
) -> dict[str, str | int | None]:
    return {
        "user_id": str(user.id) if user is not None else None,
        "period_start": period.period_start.isoformat(),
        "period_end": period.period_end.isoformat(),
        "organization_id": str(organization_id) if organization_id is not None else None,
        "establishment_id": str(establishment_id) if establishment_id is not None else None,
        "page_size": page_size,
    }


def _encode_cursor(
    *,
    context: dict[str, str | int | None],
    item: AnalyticsPatternListItem,
) -> str:
    payload = {
        "version": PATTERN_LIST_CURSOR_VERSION,
        "context": context,
        "sort": {
            "signal_count": item.signal_count,
            "last_seen_at": item.last_seen_at.isoformat(),
            "normalized_label": item.normalized_label,
            "pattern_id": str(item.pattern_id),
        },
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _parse_cursor(
    raw: str | None,
    *,
    expected_context: dict[str, str | int | None],
) -> _PatternListCursor | None:
    if not raw:
        return None
    padding = "=" * (-len(raw) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(f"{raw}{padding}").decode())
        if payload.get("version") != PATTERN_LIST_CURSOR_VERSION:
            raise ValueError
        if payload.get("context") != expected_context:
            raise ValueError
        sort = payload["sort"]
        last_seen_at = parse_datetime(sort["last_seen_at"])
        if last_seen_at is None:
            raise ValueError
        return _PatternListCursor(
            signal_count=int(sort["signal_count"]),
            last_seen_at=last_seen_at,
            normalized_label=str(sort["normalized_label"]),
            pattern_id=uuid.UUID(str(sort["pattern_id"])),
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as exc:
        raise AnalyticsValidationError(
            "Invalid analytics pattern list cursor.",
            code="analytics_pattern_list_cursor_invalid",
        ) from exc
