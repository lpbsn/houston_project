from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from houston.accounts.models import User
from houston.analytics.comparisons import (
    AnalyticsComparisonPeriod,
    build_adjacent_comparison_periods,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.selectors import analytics_default_signals_queryset
from houston.establishments.public_serialization import serialize_business_unit_ref
from houston.signals.models import Signal

PATTERN_SIGNALS_CURSOR_VERSION = "analytics_pattern_signals_v1"
DEFAULT_PATTERN_SIGNALS_PAGE_SIZE = 50
MAX_PATTERN_SIGNALS_PAGE_SIZE = 100


@dataclass(frozen=True)
class AnalyticsSignalEstablishmentRef:
    id: uuid.UUID
    name: str


@dataclass(frozen=True)
class AnalyticsSignalBusinessUnitRef:
    id: uuid.UUID
    specific_name: str


@dataclass(frozen=True)
class AnalyticsPatternSignalItem:
    signal_id: uuid.UUID
    title: str
    structured_summary: str
    status: str
    created_at: datetime
    resolved_at: datetime | None
    establishment: AnalyticsSignalEstablishmentRef
    responsible_business_unit: AnalyticsSignalBusinessUnitRef | None


@dataclass(frozen=True)
class AnalyticsPatternSignalsResult:
    period: AnalyticsComparisonPeriod
    items: tuple[AnalyticsPatternSignalItem, ...]
    page_size: int
    has_more: bool
    next_cursor: str | None


@dataclass(frozen=True)
class _PatternSignalsCursor:
    created_at: datetime
    signal_id: uuid.UUID


def list_analytics_pattern_signals(
    user: User | None,
    *,
    pattern_id,
    period_start: datetime,
    period_end: datetime,
    organization_id=None,
    establishment_id=None,
    page_size: int = DEFAULT_PATTERN_SIGNALS_PAGE_SIZE,
    cursor: str | None = None,
) -> AnalyticsPatternSignalsResult:
    period, _previous_period = build_adjacent_comparison_periods(
        period_start=period_start,
        period_end=period_end,
    )
    parsed_pattern_id = _parse_pattern_id(pattern_id)
    validated_page_size = _validate_page_size(page_size)
    context = _cursor_context(
        user=user,
        pattern_id=parsed_pattern_id,
        period=period,
        organization_id=organization_id,
        establishment_id=establishment_id,
        page_size=validated_page_size,
    )
    parsed_cursor = _parse_cursor(cursor, expected_context=context)

    visible_signals = _filter_created_period(
        analytics_default_signals_queryset(
            user,
            organization_id=organization_id,
            establishment_id=establishment_id,
        ),
        period=period,
    )
    base_queryset = _base_assignment_queryset(
        visible_signals,
        pattern_id=parsed_pattern_id,
    )
    if not base_queryset.exists():
        raise AnalyticsValidationError(
            "Analytics pattern was not found.",
            code="analytics_pattern_not_found",
        )

    page_queryset = _apply_cursor(base_queryset, parsed_cursor)
    page_rows = list(page_queryset[: validated_page_size + 1])
    has_more = len(page_rows) > validated_page_size
    served_rows = page_rows[:validated_page_size]
    items = tuple(_item_from_assignment(row) for row in served_rows)
    next_cursor = None
    if has_more and items:
        next_cursor = _encode_cursor(context=context, item=items[-1])

    return AnalyticsPatternSignalsResult(
        period=period,
        items=items,
        page_size=validated_page_size,
        has_more=has_more,
        next_cursor=next_cursor,
    )


def _parse_pattern_id(pattern_id) -> uuid.UUID:
    try:
        return uuid.UUID(str(pattern_id))
    except (TypeError, ValueError) as exc:
        raise AnalyticsValidationError(
            "Analytics pattern was not found.",
            code="analytics_pattern_not_found",
        ) from exc


def _validate_page_size(page_size: int) -> int:
    try:
        parsed = int(page_size)
    except (TypeError, ValueError) as exc:
        raise AnalyticsValidationError(
            "page_size must be an integer.",
            code="analytics_pattern_signals_page_size_invalid",
        ) from exc
    if parsed < 1 or parsed > MAX_PATTERN_SIGNALS_PAGE_SIZE:
        raise AnalyticsValidationError(
            f"page_size must be between 1 and {MAX_PATTERN_SIGNALS_PAGE_SIZE}.",
            code="analytics_pattern_signals_page_size_invalid",
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


def _base_assignment_queryset(
    queryset: QuerySet[Signal],
    *,
    pattern_id: uuid.UUID,
) -> QuerySet[SignalPatternAssignment]:
    return (
        SignalPatternAssignment.objects.filter(
            signal_id__in=queryset.values("id"),
            pattern_id=pattern_id,
        )
        .select_related(
            "signal",
            "signal__establishment",
            "signal__responsible_business_unit",
            "signal__responsible_business_unit__catalog_business_unit",
        )
        .order_by("-signal__created_at", "-signal_id")
    )


def _apply_cursor(
    queryset: QuerySet[SignalPatternAssignment],
    cursor: _PatternSignalsCursor | None,
) -> QuerySet[SignalPatternAssignment]:
    if cursor is None:
        return queryset
    return queryset.filter(
        Q(signal__created_at__lt=cursor.created_at)
        | Q(signal__created_at=cursor.created_at, signal_id__lt=cursor.signal_id)
    )


def _item_from_assignment(
    assignment: SignalPatternAssignment,
) -> AnalyticsPatternSignalItem:
    signal = assignment.signal
    return AnalyticsPatternSignalItem(
        signal_id=signal.id,
        title=signal.title,
        structured_summary=signal.structured_summary,
        status=signal.status,
        created_at=signal.created_at,
        resolved_at=signal.resolved_at,
        establishment=AnalyticsSignalEstablishmentRef(
            id=signal.establishment_id,
            name=signal.establishment.name,
        ),
        responsible_business_unit=_business_unit_ref(signal.responsible_business_unit),
    )


def _business_unit_ref(business_unit) -> AnalyticsSignalBusinessUnitRef | None:
    payload = serialize_business_unit_ref(business_unit=business_unit)
    if payload is None:
        return None
    return AnalyticsSignalBusinessUnitRef(
        id=payload["id"],
        specific_name=payload["specific_name"],
    )


def _cursor_context(
    *,
    user: User | None,
    pattern_id: uuid.UUID,
    period: AnalyticsComparisonPeriod,
    organization_id,
    establishment_id,
    page_size: int,
) -> dict[str, str | int | None]:
    return {
        "user_id": str(user.id) if user is not None else None,
        "pattern_id": str(pattern_id),
        "period_start": period.period_start.isoformat(),
        "period_end": period.period_end.isoformat(),
        "organization_id": str(organization_id) if organization_id is not None else None,
        "establishment_id": str(establishment_id) if establishment_id is not None else None,
        "page_size": page_size,
    }


def _encode_cursor(
    *,
    context: dict[str, str | int | None],
    item: AnalyticsPatternSignalItem,
) -> str:
    payload = {
        "version": PATTERN_SIGNALS_CURSOR_VERSION,
        "context": context,
        "sort": {
            "created_at": item.created_at.isoformat(),
            "signal_id": str(item.signal_id),
        },
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _parse_cursor(
    raw: str | None,
    *,
    expected_context: dict[str, str | int | None],
) -> _PatternSignalsCursor | None:
    if not raw:
        return None
    padding = "=" * (-len(raw) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(f"{raw}{padding}").decode())
        if payload.get("version") != PATTERN_SIGNALS_CURSOR_VERSION:
            raise ValueError
        if payload.get("context") != expected_context:
            raise ValueError
        sort = payload["sort"]
        created_at = parse_datetime(sort["created_at"])
        if created_at is None or timezone.is_naive(created_at):
            raise ValueError
        return _PatternSignalsCursor(
            created_at=created_at,
            signal_id=uuid.UUID(str(sort["signal_id"])),
        )
    except (
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ) as exc:
        raise AnalyticsValidationError(
            "Invalid analytics pattern signals cursor.",
            code="analytics_pattern_signals_cursor_invalid",
        ) from exc
