from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Case, DateTimeField, F, OuterRef, Q, QuerySet, Subquery, Value, When
from django.db.models.functions import Coalesce

from houston.accounts.display import membership_display_name
from houston.core.civil_time import CivilWindow
from houston.establishments.membership_scope import membership_business_unit_scope_ids
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_CANCELED,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    SIGNAL_RESOLUTION_ORIGIN_VALUES,
)
from houston.signals.feed_cursor import signal_feed_auth_context_hash
from houston.signals.history_cursor import (
    SignalHistoryCursor,
    apply_signal_history_cursor,
    encode_signal_history_cursor,
    signal_history_context_hash,
)
from houston.signals.models import Signal, SignalLifecycleEvent
from houston.signals.selectors import signal_read_visibility_q

HISTORY_SIGNAL_STATUSES = frozenset({Signal.Status.RESOLVED, Signal.Status.CANCELED})

_SIGNAL_HISTORY_SELECT_RELATED = (
    "establishment",
    "resolved_by_membership__user",
    "canceled_by_membership__user",
)


@dataclass(frozen=True)
class SignalHistoryPage:
    items: list[Signal]
    has_more: bool
    next_cursor: str | None
    undated_count: int | None


def _canceled_pole_q(membership: EstablishmentMembership) -> Q:
    if membership.role in ADMIN_ROLES:
        return Q(status=Signal.Status.CANCELED)
    scope_ids = membership_business_unit_scope_ids(membership)
    pole = Q(responsible_business_unit_id__in=scope_ids) | Q(
        affected_business_unit_id__in=scope_ids
    )
    if membership.role == EstablishmentMembership.Role.MANAGER:
        pole |= Q(routing_status=Signal.RoutingStatus.UNASSIGNED)
    return Q(status=Signal.Status.CANCELED) & pole


def signal_history_visibility_q(
    *,
    membership: EstablishmentMembership,
    view_mode: str,
) -> Q:
    """Closed-list visibility: feed scope rules, plus detail pole rule for canceled."""
    visible = signal_read_visibility_q(
        membership=membership,
        view_mode=view_mode,  # type: ignore[arg-type]
        statuses=HISTORY_SIGNAL_STATUSES,
    )
    return visible & (Q(status=Signal.Status.RESOLVED) | _canceled_pole_q(membership))


def _latest_event_subquery(event_type: str) -> Subquery:
    return Subquery(
        SignalLifecycleEvent.objects.filter(
            signal_id=OuterRef("pk"),
            event_type=event_type,
        )
        .order_by("-occurred_at", "-id")
        .values("occurred_at")[:1],
        output_field=DateTimeField(),
    )


def annotate_signal_terminal_at(queryset: QuerySet[Signal]) -> QuerySet[Signal]:
    return queryset.annotate(
        terminal_at=Case(
            When(
                status=Signal.Status.RESOLVED,
                then=Coalesce(
                    F("resolved_at"),
                    _latest_event_subquery(SIGNAL_LIFECYCLE_EVENT_RESOLVED),
                ),
            ),
            When(
                status=Signal.Status.CANCELED,
                then=Coalesce(
                    F("canceled_at"),
                    _latest_event_subquery(SIGNAL_LIFECYCLE_EVENT_CANCELED),
                ),
            ),
            default=Value(None),
            output_field=DateTimeField(),
        )
    )


def signal_history_queryset(
    *,
    memberships: list[EstablishmentMembership],
    view_mode: str,
) -> QuerySet[Signal]:
    if not memberships:
        return annotate_signal_terminal_at(Signal.objects.none())
    visibility = Q()
    for membership in memberships:
        visibility |= signal_history_visibility_q(membership=membership, view_mode=view_mode)
    return annotate_signal_terminal_at(Signal.objects.filter(visibility))


def _hydrate_signal_history_items(rows: list[dict]) -> list[Signal]:
    if not rows:
        return []
    signals_by_id = {
        signal.id: signal
        for signal in Signal.objects.filter(id__in=[row["id"] for row in rows]).select_related(
            *_SIGNAL_HISTORY_SELECT_RELATED
        )
    }
    items = []
    for row in rows:
        signal = signals_by_id[row["id"]]
        signal.terminal_at = row["terminal_at"]
        items.append(signal)
    return items


def signal_terminal_date_source(signal: Signal) -> str:
    if signal.status == Signal.Status.RESOLVED and signal.resolved_at is not None:
        return "field"
    if signal.status == Signal.Status.CANCELED and signal.canceled_at is not None:
        return "field"
    if getattr(signal, "terminal_at", None) is not None:
        return "event"
    return "unknown"


def signal_termination(signal: Signal) -> tuple[str, str | None]:
    """Path from stored origin. A missing actor never becomes an automatic path."""
    if signal.status == Signal.Status.RESOLVED:
        origin = signal.resolution_origin
        actor = signal.resolved_by_membership
        if origin == SIGNAL_RESOLUTION_ORIGIN_MANUAL and actor is None:
            return "unknown", None
        if origin in SIGNAL_RESOLUTION_ORIGIN_VALUES:
            return origin, membership_display_name(actor)
        return "unknown", membership_display_name(actor)
    if signal.status == Signal.Status.CANCELED:
        actor = signal.canceled_by_membership
        if actor is None:
            return "unknown", None
        return "manual", membership_display_name(actor)
    return "unknown", None


def _order_history(queryset: QuerySet[Signal]) -> QuerySet[Signal]:
    return queryset.order_by(F("terminal_at").desc(nulls_last=True), F("id").desc())


def build_signal_history_page(
    *,
    memberships: list[EstablishmentMembership],
    view_mode: str,
    scope: str,
    status: str,
    period: str,
    period_from: str | None,
    period_to: str | None,
    window: CivilWindow | None,
    page_size: int,
    cursor: SignalHistoryCursor | None,
) -> SignalHistoryPage:
    auth_hash = signal_feed_auth_context_hash(
        memberships=memberships,
        view_mode=view_mode,
        scope=scope,
    )
    context_hash = signal_history_context_hash(
        scope=scope,
        view_mode=view_mode,
        status=status,
        period=period,
        period_from=period_from,
        period_to=period_to,
        auth_context_hash=auth_hash,
    )
    if cursor is not None:
        cursor.validate_context(context_hash)

    queryset = signal_history_queryset(memberships=memberships, view_mode=view_mode)
    if status != "all":
        queryset = queryset.filter(status=status)
    undated_count = None
    if cursor is None and window is not None:
        undated_count = queryset.filter(terminal_at__isnull=True).count()
    if window is not None:
        queryset = queryset.filter(terminal_at__gte=window.start, terminal_at__lt=window.end)
    if cursor is not None:
        queryset = apply_signal_history_cursor(
            queryset,
            cursor,
            include_undated=window is None,
        )
    rows = list(_order_history(queryset).values("id", "terminal_at")[: page_size + 1])
    has_more = len(rows) > page_size
    page_rows = rows[:page_size]
    items = _hydrate_signal_history_items(page_rows)
    next_cursor = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = encode_signal_history_cursor(
            scope=scope,
            view_mode=view_mode,
            status=status,
            period=period,
            period_from=period_from,
            period_to=period_to,
            auth_context_hash=auth_hash,
            terminal_at=last["terminal_at"],
            item_id=last["id"],
        )
    return SignalHistoryPage(
        items=items,
        has_more=has_more,
        next_cursor=next_cursor,
        undated_count=undated_count,
    )
