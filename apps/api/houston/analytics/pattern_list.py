from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db.models import BooleanField, Case, Count, Max, Q, QuerySet, Value, When
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from houston.accounts.models import User
from houston.analytics.comparisons import (
    AnalyticsComparisonPeriod,
    MetricComparison,
    build_adjacent_comparison_periods,
    compare_metric_values,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.recurrence import (
    RECURRENCE_STATUS_COMPUTED,
    AnalyticsRecurrenceWindow,
    PatternRecurrenceStats,
    build_recurrence_window,
    recurrence_stats_for_visible_pattern_ids,
    recurrent_pattern_ids_queryset,
)
from houston.analytics.selectors import resolve_analytics_read_scope
from houston.establishments.membership_scope import (
    membership_business_unit_scope_ids,
    membership_scope_prefetch,
)
from houston.establishments.models import BusinessUnit, Establishment, EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES
from houston.organizations.models import Organization
from houston.signals.models import Signal

PATTERN_LIST_CURSOR_VERSION = "analytics_pattern_list_v3"
DEFAULT_PATTERN_LIST_PAGE_SIZE = 50
MAX_PATTERN_LIST_PAGE_SIZE = 100
MAX_PATTERN_LIST_ESTABLISHMENTS = 5
PATTERN_LIST_RECURRENCE_ALL = "all"
PATTERN_LIST_RECURRENCE_RECURRENT = "recurrent"
PATTERN_LIST_RECURRENCE_NON_RECURRENT = "non_recurrent"
PATTERN_LIST_RECURRENCE_FILTERS = frozenset(
    {
        PATTERN_LIST_RECURRENCE_ALL,
        PATTERN_LIST_RECURRENCE_RECURRENT,
        PATTERN_LIST_RECURRENCE_NON_RECURRENT,
    }
)
PATTERN_LIST_SIGNAL_STATUSES = frozenset(
    {
        Signal.Status.OPEN,
        Signal.Status.IN_PROGRESS,
        Signal.Status.INTERESTING,
        Signal.Status.RESOLVED,
        Signal.Status.ARCHIVED,
    }
)
MAX_PATTERN_LIST_SEARCH_LENGTH = 100


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
    is_recurrent: bool
    occurrence_count_30d: int
    distinct_day_count_30d: int
    recurrence_window: AnalyticsRecurrenceWindow
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
    recurrence_window: AnalyticsRecurrenceWindow
    recurrence_status: str


@dataclass(frozen=True)
class AnalyticsPatternFilterEstablishmentOption:
    establishment_id: uuid.UUID
    name: str


@dataclass(frozen=True)
class AnalyticsPatternFilterBusinessUnitOption:
    business_unit_id: uuid.UUID | None
    name: str
    establishment_id: uuid.UUID | None
    is_unassigned: bool = False


@dataclass(frozen=True)
class AnalyticsPatternFilterOptionsResult:
    establishments: tuple[AnalyticsPatternFilterEstablishmentOption, ...]
    responsible_business_units: tuple[AnalyticsPatternFilterBusinessUnitOption, ...]
    includes_unassigned: bool


@dataclass(frozen=True)
class _PatternListCursor:
    is_recurrent: bool
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
    establishment_ids=None,
    q: str | None = None,
    recurrence: str = PATTERN_LIST_RECURRENCE_ALL,
    responsible_business_unit_ids=None,
    responsible_business_unit_unassigned: bool = False,
    signal_statuses=None,
    page_size: int = DEFAULT_PATTERN_LIST_PAGE_SIZE,
    cursor: str | None = None,
) -> AnalyticsPatternListResult:
    filters = _normalize_filters(
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
        q=q,
        recurrence=recurrence,
        responsible_business_unit_ids=responsible_business_unit_ids,
        responsible_business_unit_unassigned=responsible_business_unit_unassigned,
        signal_statuses=signal_statuses,
    )
    current_period, previous_period = build_adjacent_comparison_periods(
        period_start=period_start,
        period_end=period_end,
    )
    recurrence_window = build_recurrence_window(current_period.period_end)
    validated_page_size = _validate_page_size(page_size)
    context = _cursor_context(
        user=user,
        period=current_period,
        recurrence_as_of=current_period.period_end,
        organization_id=organization_id,
        establishment_id=establishment_id,
        filters=filters,
        page_size=validated_page_size,
    )
    parsed_cursor = _parse_cursor(cursor, expected_context=context)
    read_scope = resolve_analytics_read_scope(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=filters["establishment_ids"],
    )

    current_signals = _filter_created_period(
        read_scope.default_signals_queryset(),
        period=current_period,
    )
    current_signals = _apply_signal_filters(current_signals, filters)
    recurrent_ids = recurrent_pattern_ids_queryset(
        user,
        as_of=current_period.period_end,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=filters["establishment_ids"],
        _read_scope=read_scope,
    )
    current_rows = _current_pattern_rows(
        current_signals,
        recurrent_ids=recurrent_ids,
        q=filters["q"],
        recurrence=filters["recurrence"],
    )
    total_count = _pattern_total_count(
        current_signals,
        recurrent_ids=recurrent_ids,
        q=filters["q"],
        recurrence=filters["recurrence"],
    )
    page_queryset = _apply_cursor(current_rows, parsed_cursor)
    page_rows = list(page_queryset[: validated_page_size + 1])
    has_more = len(page_rows) > validated_page_size
    served_rows = page_rows[:validated_page_size]
    pattern_ids = [row["pattern_id"] for row in served_rows]

    previous_counts = _pattern_counts_for_signals(
        _filter_created_period(
            read_scope.default_signals_queryset(),
            period=previous_period,
        ),
        filters,
        pattern_ids=pattern_ids,
    )
    actionable_counts = _pattern_counts_for_signals(
        _filter_created_period(
            read_scope.actionable_signals_queryset(),
            period=current_period,
        ),
        filters,
        pattern_ids=pattern_ids,
    )
    establishment_counts, establishments = _establishment_summaries(
        current_signals,
        pattern_ids=pattern_ids,
    )
    recurrence_stats = recurrence_stats_for_visible_pattern_ids(
        user,
        as_of=current_period.period_end,
        visible_pattern_ids=pattern_ids,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=filters["establishment_ids"],
        _read_scope=read_scope,
    )

    items = tuple(
        _item_from_row(
            row,
            previous_counts=previous_counts,
            actionable_counts=actionable_counts,
            establishment_counts=establishment_counts,
            establishments=establishments,
            recurrence_stats=recurrence_stats,
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
        recurrence_window=recurrence_window,
        recurrence_status=RECURRENCE_STATUS_COMPUTED,
    )


def list_analytics_pattern_filter_options(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> AnalyticsPatternFilterOptionsResult:
    filters = _normalize_filters(
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
        q=None,
        recurrence=PATTERN_LIST_RECURRENCE_ALL,
        responsible_business_unit_ids=None,
        responsible_business_unit_unassigned=False,
        signal_statuses=None,
    )
    memberships = _analytics_filter_option_memberships(
        user=user,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=filters["establishment_ids"],
    )
    establishment_ids_for_options = sorted(
        {membership.establishment_id for membership in memberships},
        key=str,
    )
    establishment_rows = (
        Establishment.objects.filter(id__in=establishment_ids_for_options)
        .values("id", "name")
        .order_by("name", "id")
    )
    admin_establishment_ids = {
        membership.establishment_id
        for membership in memberships
        if membership.role in ADMIN_ROLES
    }
    scoped_business_unit_ids: set[uuid.UUID] = set()
    includes_unassigned = False
    for membership in memberships:
        if membership.role in ADMIN_ROLES:
            includes_unassigned = True
            continue
        if membership.role == EstablishmentMembership.Role.MANAGER:
            includes_unassigned = True
            scoped_business_unit_ids.update(membership_business_unit_scope_ids(membership))
    business_unit_filter = Q(establishment_id__in=admin_establishment_ids)
    if scoped_business_unit_ids:
        business_unit_filter |= Q(id__in=scoped_business_unit_ids)
    business_unit_rows = (
        BusinessUnit.objects.filter(business_unit_filter, active=True)
        .values("id", "specific_name", "establishment_id")
        .order_by("specific_name", "establishment_id", "id")
    )
    return AnalyticsPatternFilterOptionsResult(
        establishments=tuple(
            AnalyticsPatternFilterEstablishmentOption(
                establishment_id=row["id"],
                name=row["name"],
            )
            for row in establishment_rows
        ),
        responsible_business_units=(
            (
                AnalyticsPatternFilterBusinessUnitOption(
                    business_unit_id=None,
                    name="Non assigné",
                    establishment_id=None,
                    is_unassigned=True,
                ),
            )
            if includes_unassigned
            else ()
        )
        + tuple(
            AnalyticsPatternFilterBusinessUnitOption(
                business_unit_id=row["id"],
                name=row["specific_name"],
                establishment_id=row["establishment_id"],
                is_unassigned=False,
            )
            for row in business_unit_rows
        ),
        includes_unassigned=includes_unassigned,
    )


def _analytics_filter_option_memberships(
    *,
    user: User | None,
    organization_id,
    establishment_id,
    establishment_ids,
):
    if user is None or user.status != User.Status.ACTIVE:
        return []
    queryset = (
        EstablishmentMembership.objects.filter(
            user_id=user.id,
            role__in=(
                EstablishmentMembership.Role.OWNER,
                EstablishmentMembership.Role.DIRECTOR,
                EstablishmentMembership.Role.MANAGER,
            ),
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related("establishment", "establishment__organization")
        .prefetch_related(membership_scope_prefetch())
        .order_by("establishment_id", "id")
    )
    if organization_id is not None:
        queryset = queryset.filter(establishment__organization_id=organization_id)
    if establishment_id is not None:
        queryset = queryset.filter(establishment_id=establishment_id)
    if establishment_ids is not None:
        queryset = queryset.filter(establishment_id__in=establishment_ids)
    return list(queryset)


def _current_pattern_rows(
    queryset: QuerySet[Signal],
    *,
    recurrent_ids,
    q: str,
    recurrence: str,
):
    assignments = _pattern_assignments_for_signals(queryset, q=q)
    rows = (
        assignments
        .annotate(
            is_recurrent=Case(
                When(pattern_id__in=recurrent_ids, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        .values(
            "pattern_id",
            "pattern__label",
            "pattern__normalized_label",
            "pattern__status",
            "is_recurrent",
        )
        .annotate(
            signal_count=Count("signal_id", distinct=True),
            last_seen_at=Max("signal__created_at"),
        )
    )
    if recurrence == PATTERN_LIST_RECURRENCE_RECURRENT:
        rows = rows.filter(is_recurrent=True)
    elif recurrence == PATTERN_LIST_RECURRENCE_NON_RECURRENT:
        rows = rows.filter(is_recurrent=False)
    return rows.order_by(
        "-is_recurrent",
        "-signal_count",
        "-last_seen_at",
        "pattern__normalized_label",
        "pattern_id",
    )


def _pattern_total_count(
    queryset: QuerySet[Signal],
    *,
    recurrent_ids,
    q: str,
    recurrence: str,
) -> int:
    assignments = _pattern_assignments_for_signals(queryset, q=q)
    if recurrence == PATTERN_LIST_RECURRENCE_RECURRENT:
        assignments = assignments.filter(pattern_id__in=recurrent_ids)
    elif recurrence == PATTERN_LIST_RECURRENCE_NON_RECURRENT:
        assignments = assignments.exclude(pattern_id__in=recurrent_ids)
    return int(
        assignments.aggregate(total_count=Count("pattern_id", distinct=True))[
            "total_count"
        ]
    )


def _pattern_assignments_for_signals(
    queryset: QuerySet[Signal],
    *,
    q: str,
) -> QuerySet[SignalPatternAssignment]:
    assignments = SignalPatternAssignment.objects.filter(
        signal_id__in=queryset.values("id"),
        pattern_id__isnull=False,
    )
    if q:
        assignments = assignments.filter(
            Q(pattern__label__icontains=q)
            | Q(pattern__normalized_label__icontains=q)
        )
    return assignments


def _apply_cursor(queryset, cursor: _PatternListCursor | None):
    if cursor is None:
        return queryset
    return queryset.filter(
        Q(is_recurrent__lt=cursor.is_recurrent)
        | Q(
            is_recurrent=cursor.is_recurrent,
            signal_count__lt=cursor.signal_count,
        )
        | Q(
            is_recurrent=cursor.is_recurrent,
            signal_count=cursor.signal_count,
            last_seen_at__lt=cursor.last_seen_at,
        )
        | Q(
            is_recurrent=cursor.is_recurrent,
            signal_count=cursor.signal_count,
            last_seen_at=cursor.last_seen_at,
            pattern__normalized_label__gt=cursor.normalized_label,
        )
        | Q(
            is_recurrent=cursor.is_recurrent,
            signal_count=cursor.signal_count,
            last_seen_at=cursor.last_seen_at,
            pattern__normalized_label=cursor.normalized_label,
            pattern_id__gt=cursor.pattern_id,
        )
    )


def _pattern_counts_for_signals(
    queryset: QuerySet[Signal],
    filters,
    *,
    pattern_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    if not pattern_ids:
        return {}
    queryset = _apply_signal_filters(queryset, filters)
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
    recurrence_stats: dict[uuid.UUID, PatternRecurrenceStats],
) -> AnalyticsPatternListItem:
    pattern_id = row["pattern_id"]
    signal_count = int(row["signal_count"])
    previous_signal_count = previous_counts.get(pattern_id, 0)
    recurrence = recurrence_stats[pattern_id]
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
        is_recurrent=recurrence.is_recurrent,
        occurrence_count_30d=recurrence.occurrence_count_30d,
        distinct_day_count_30d=recurrence.distinct_day_count_30d,
        recurrence_window=recurrence.window,
        recurrence_status=RECURRENCE_STATUS_COMPUTED,
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


def _apply_signal_filters(queryset: QuerySet[Signal], filters) -> QuerySet[Signal]:
    if filters["signal_statuses"]:
        queryset = queryset.filter(status__in=filters["signal_statuses"])
    business_unit_ids = filters["responsible_business_unit_ids"]
    include_unassigned = filters["responsible_business_unit_unassigned"]
    if business_unit_ids and include_unassigned:
        queryset = queryset.filter(
            Q(responsible_business_unit_id__in=business_unit_ids)
            | Q(responsible_business_unit_id__isnull=True)
        )
    elif business_unit_ids:
        queryset = queryset.filter(responsible_business_unit_id__in=business_unit_ids)
    elif include_unassigned:
        queryset = queryset.filter(responsible_business_unit_id__isnull=True)
    return queryset


def _normalize_filters(
    *,
    establishment_id,
    establishment_ids,
    q,
    recurrence,
    responsible_business_unit_ids,
    responsible_business_unit_unassigned,
    signal_statuses,
) -> dict:
    normalized_establishment_ids = _normalize_uuid_list(
        establishment_ids,
        field_name="establishment_ids",
    )
    if establishment_id is not None and normalized_establishment_ids is not None:
        raise AnalyticsValidationError(
            "Use either establishment_id or establishment_ids, not both.",
            code="analytics_scope_invalid",
        )
    normalized_q = (q or "").strip()
    if len(normalized_q) > MAX_PATTERN_LIST_SEARCH_LENGTH:
        raise AnalyticsValidationError(
            f"q must be at most {MAX_PATTERN_LIST_SEARCH_LENGTH} characters.",
            code="analytics_pattern_list_filter_invalid",
        )
    normalized_recurrence = (recurrence or PATTERN_LIST_RECURRENCE_ALL).strip()
    if normalized_recurrence not in PATTERN_LIST_RECURRENCE_FILTERS:
        raise AnalyticsValidationError(
            "recurrence must be all, recurrent, or non_recurrent.",
            code="analytics_pattern_list_filter_invalid",
        )
    normalized_responsible_ids = _normalize_uuid_list(
        responsible_business_unit_ids,
        field_name="responsible_business_unit_ids",
    ) or ()
    normalized_statuses = _normalize_statuses(signal_statuses)
    return {
        "establishment_ids": normalized_establishment_ids,
        "q": normalized_q,
        "recurrence": normalized_recurrence,
        "responsible_business_unit_ids": normalized_responsible_ids,
        "responsible_business_unit_unassigned": _normalize_bool(
            responsible_business_unit_unassigned
        ),
        "signal_statuses": normalized_statuses,
    }


def _normalize_uuid_list(values, *, field_name: str) -> tuple[uuid.UUID, ...] | None:
    if values is None:
        return None
    if isinstance(values, str):
        raw_values = values.split(",")
    else:
        raw_values = list(values)
    parsed = []
    try:
        for value in raw_values:
            if value in (None, ""):
                continue
            parsed.append(uuid.UUID(str(value).strip()))
    except (TypeError, ValueError) as exc:
        raise AnalyticsValidationError(
            f"{field_name} must contain valid UUIDs.",
            code="analytics_pattern_list_filter_invalid",
        ) from exc
    return tuple(sorted(set(parsed), key=str))


def _normalize_statuses(values) -> tuple[str, ...]:
    if values is None:
        return ()
    raw_values = values.split(",") if isinstance(values, str) else list(values)
    normalized = tuple(
        sorted({str(value).strip() for value in raw_values if str(value).strip()})
    )
    if any(status not in PATTERN_LIST_SIGNAL_STATUSES for status in normalized):
        raise AnalyticsValidationError(
            "signal_statuses contains an invalid analytics status.",
            code="analytics_pattern_list_filter_invalid",
        )
    return normalized


def _normalize_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return False
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise AnalyticsValidationError(
        "responsible_business_unit_unassigned must be a boolean.",
        code="analytics_pattern_list_filter_invalid",
    )


def _cursor_context(
    *,
    user: User | None,
    period: AnalyticsComparisonPeriod,
    recurrence_as_of: datetime,
    organization_id,
    establishment_id,
    filters,
    page_size: int,
) -> dict[str, object]:
    return {
        "user_id": str(user.id) if user is not None else None,
        "period_start": period.period_start.isoformat(),
        "period_end": period.period_end.isoformat(),
        "recurrence_as_of": recurrence_as_of.isoformat(),
        "organization_id": str(organization_id) if organization_id is not None else None,
        "establishment_id": str(establishment_id) if establishment_id is not None else None,
        "establishment_ids": [str(value) for value in filters["establishment_ids"] or ()],
        "q": filters["q"],
        "recurrence": filters["recurrence"],
        "responsible_business_unit_ids": [
            str(value) for value in filters["responsible_business_unit_ids"]
        ],
        "responsible_business_unit_unassigned": filters[
            "responsible_business_unit_unassigned"
        ],
        "signal_statuses": list(filters["signal_statuses"]),
        "page_size": page_size,
    }


def _encode_cursor(
    *,
    context: dict[str, object],
    item: AnalyticsPatternListItem,
) -> str:
    payload = {
        "version": PATTERN_LIST_CURSOR_VERSION,
        "context": context,
        "sort": {
            "is_recurrent": item.is_recurrent,
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
        if last_seen_at is None or timezone.is_naive(last_seen_at):
            raise ValueError
        if not isinstance(sort["is_recurrent"], bool):
            raise ValueError
        return _PatternListCursor(
            is_recurrent=sort["is_recurrent"],
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
