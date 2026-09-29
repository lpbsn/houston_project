from __future__ import annotations

from dataclasses import dataclass

from houston.establishments.membership_scope import membership_scope_prefetch
from houston.establishments.models import EstablishmentMembership
from houston.signals.constants import SIGNAL_FEED_PIN_LIMIT
from houston.signals.feed_cursor import (
    SignalFeedCursor,
    SignalFeedPinCursor,
    apply_signal_feed_cursor,
    apply_signal_feed_pin_cursor,
    encode_signal_feed_cursor,
    encode_signal_feed_pin_cursor,
    signal_feed_auth_context_hash,
    signal_feed_filter_hash,
    validate_signal_feed_cursor_context,
)
from houston.signals.feed_filters import SignalFeedFilters, signal_feed_status_selection
from houston.signals.models import Signal
from houston.signals.selectors import (
    cross_signal_feed_queryset,
    hydrate_cross_signal_feed_queryset,
    signal_feed_counts,
    signal_feed_list_queryset,
    signal_feed_pins_queryset,
    signal_feed_queryset,
)


@dataclass(frozen=True)
class SignalFeedPage:
    items: list[Signal]
    has_more: bool
    next_cursor: str | None
    pins: list[Signal] | None = None
    counts: dict[str, int] | None = None
    pins_has_more: bool | None = None
    pins_next_cursor: str | None = None


@dataclass(frozen=True)
class SignalFeedPinsPage:
    items: list[Signal]
    has_more: bool
    next_cursor: str | None


def prepare_signal_feed_memberships(
    memberships: list[EstablishmentMembership],
) -> list[EstablishmentMembership]:
    if not memberships:
        return []
    by_id = {
        membership.id: membership
        for membership in EstablishmentMembership.objects.filter(
            pk__in=[membership.pk for membership in memberships],
        )
        .select_related("establishment")
        .prefetch_related(membership_scope_prefetch())
    }
    return [by_id[membership.id] for membership in memberships if membership.id in by_id]


def _context_hashes(
    *,
    memberships: list[EstablishmentMembership],
    view_mode: str,
    scope: str,
    filters: SignalFeedFilters | None,
) -> tuple[str, str, str]:
    status = signal_feed_status_selection(filters)
    filter_hash = signal_feed_filter_hash(
        business_unit_ids=() if filters is None else filters.business_unit_ids,
        activity_subject_ids=() if filters is None else filters.activity_subject_ids,
        needs_qualification=False if filters is None else filters.needs_qualification,
    )
    auth_context_hash = signal_feed_auth_context_hash(
        memberships=memberships,
        view_mode=view_mode,
        scope=scope,
    )
    return status, filter_hash, auth_context_hash


def _page_from_list(
    queryset,
    *,
    page_size: int,
    cursor: SignalFeedCursor | None,
    scope: str,
    view_mode: str,
    status: str,
    filter_hash: str,
    auth_context_hash: str,
) -> tuple[list[Signal], bool, str | None]:
    if cursor is not None:
        queryset = apply_signal_feed_cursor(queryset, cursor)
    candidates = list(queryset[: page_size + 1])
    has_more = len(candidates) > page_size
    items = candidates[:page_size]
    next_cursor = None
    if has_more and items:
        next_cursor = encode_signal_feed_cursor(
            items[-1],
            scope=scope,
            view_mode=view_mode,
            status=status,
            filter_hash=filter_hash,
            auth_context_hash=auth_context_hash,
        )
    return items, has_more, next_cursor


def _pins_page(
    queryset,
    *,
    page_size: int,
    cursor: SignalFeedPinCursor | None,
    scope: str,
    view_mode: str,
    status: str,
    filter_hash: str,
    auth_context_hash: str,
) -> SignalFeedPinsPage:
    if cursor is not None:
        queryset = apply_signal_feed_pin_cursor(queryset, cursor)
    candidates = list(queryset[: page_size + 1])
    has_more = len(candidates) > page_size
    items = candidates[:page_size]
    next_cursor = None
    if has_more and items:
        next_cursor = encode_signal_feed_pin_cursor(
            items[-1],
            scope=scope,
            view_mode=view_mode,
            status=status,
            filter_hash=filter_hash,
            auth_context_hash=auth_context_hash,
        )
    return SignalFeedPinsPage(items=items, has_more=has_more, next_cursor=next_cursor)


def _cross_page_from_list(
    queryset,
    *,
    page_size: int,
    cursor: SignalFeedCursor | None,
    scope: str,
    view_mode: str,
    status: str,
    filter_hash: str,
    auth_context_hash: str,
) -> tuple[list[Signal], bool, str | None]:
    if cursor is not None:
        queryset = apply_signal_feed_cursor(queryset, cursor)
    candidates = list(
        hydrate_cross_signal_feed_queryset(
            queryset,
            limit=page_size + 1,
        )
    )
    has_more = len(candidates) > page_size
    items = candidates[:page_size]
    next_cursor = None
    if has_more and items:
        next_cursor = encode_signal_feed_cursor(
            items[-1],
            scope=scope,
            view_mode=view_mode,
            status=status,
            filter_hash=filter_hash,
            auth_context_hash=auth_context_hash,
        )
    return items, has_more, next_cursor


def _cross_pins_page(
    queryset,
    *,
    page_size: int,
    cursor: SignalFeedPinCursor | None,
    scope: str,
    view_mode: str,
    status: str,
    filter_hash: str,
    auth_context_hash: str,
) -> SignalFeedPinsPage:
    if cursor is not None:
        queryset = apply_signal_feed_pin_cursor(queryset, cursor)
    candidates = list(
        hydrate_cross_signal_feed_queryset(
            queryset,
            limit=page_size + 1,
        )
    )
    has_more = len(candidates) > page_size
    items = candidates[:page_size]
    next_cursor = None
    if has_more and items:
        next_cursor = encode_signal_feed_pin_cursor(
            items[-1],
            scope=scope,
            view_mode=view_mode,
            status=status,
            filter_hash=filter_hash,
            auth_context_hash=auth_context_hash,
        )
    return SignalFeedPinsPage(items=items, has_more=has_more, next_cursor=next_cursor)


def build_signal_feed_page(
    *,
    membership: EstablishmentMembership,
    view_mode: str,
    filters: SignalFeedFilters | None,
    page_size: int,
    cursor: SignalFeedCursor | None = None,
) -> SignalFeedPage:
    prepared = prepare_signal_feed_memberships([membership])
    actor = prepared[0] if prepared else membership
    status, filter_hash, auth_context_hash = _context_hashes(
        memberships=[actor],
        view_mode=view_mode,
        scope="establishment",
        filters=filters,
    )
    if cursor is not None:
        validate_signal_feed_cursor_context(
            cursor,
            scope="establishment",
            view_mode=view_mode,
            status=status,
            filter_hash=filter_hash,
            auth_context_hash=auth_context_hash,
        )
    base = signal_feed_queryset(
        membership=actor,
        view_mode=view_mode,  # type: ignore[arg-type]
        filters=filters,
    )
    items, has_more, next_cursor = _page_from_list(
        signal_feed_list_queryset(base, filters=filters),
        page_size=page_size,
        cursor=cursor,
        scope="establishment",
        view_mode=view_mode,
        status=status,
        filter_hash=filter_hash,
        auth_context_hash=auth_context_hash,
    )
    if cursor is not None:
        return SignalFeedPage(items=items, has_more=has_more, next_cursor=next_cursor)
    pins = list(signal_feed_pins_queryset(base, filters=filters)[:SIGNAL_FEED_PIN_LIMIT])
    return SignalFeedPage(
        items=items,
        has_more=has_more,
        next_cursor=next_cursor,
        pins=pins,
        counts=signal_feed_counts(base, filters=filters),
        pins_has_more=False,
        pins_next_cursor=None,
    )


def build_cross_signal_feed_page(
    *,
    memberships: list[EstablishmentMembership],
    filters: SignalFeedFilters | None,
    page_size: int,
    pins_page_size: int,
    cursor: SignalFeedCursor | None = None,
) -> SignalFeedPage:
    prepared = prepare_signal_feed_memberships(memberships)
    status, filter_hash, auth_context_hash = _context_hashes(
        memberships=prepared,
        view_mode="general",
        scope="cross",
        filters=filters,
    )
    if cursor is not None:
        validate_signal_feed_cursor_context(
            cursor,
            scope="cross",
            view_mode="general",
            status=status,
            filter_hash=filter_hash,
            auth_context_hash=auth_context_hash,
        )
    base = cross_signal_feed_queryset(memberships=prepared, filters=filters)
    items, has_more, next_cursor = _cross_page_from_list(
        signal_feed_list_queryset(base, filters=filters),
        page_size=page_size,
        cursor=cursor,
        scope="cross",
        view_mode="general",
        status=status,
        filter_hash=filter_hash,
        auth_context_hash=auth_context_hash,
    )
    if cursor is not None:
        return SignalFeedPage(items=items, has_more=has_more, next_cursor=next_cursor)
    pins_page = _cross_pins_page(
        signal_feed_pins_queryset(base, filters=filters),
        page_size=pins_page_size,
        cursor=None,
        scope="cross",
        view_mode="general",
        status=status,
        filter_hash=filter_hash,
        auth_context_hash=auth_context_hash,
    )
    return SignalFeedPage(
        items=items,
        has_more=has_more,
        next_cursor=next_cursor,
        pins=pins_page.items,
        counts=signal_feed_counts(base, filters=filters),
        pins_has_more=pins_page.has_more,
        pins_next_cursor=pins_page.next_cursor,
    )


def build_cross_signal_feed_pins_page(
    *,
    memberships: list[EstablishmentMembership],
    filters: SignalFeedFilters | None,
    page_size: int,
    cursor: SignalFeedPinCursor | None = None,
) -> SignalFeedPinsPage:
    prepared = prepare_signal_feed_memberships(memberships)
    status, filter_hash, auth_context_hash = _context_hashes(
        memberships=prepared,
        view_mode="general",
        scope="cross",
        filters=filters,
    )
    if cursor is not None:
        validate_signal_feed_cursor_context(
            cursor,
            scope="cross",
            view_mode="general",
            status=status,
            filter_hash=filter_hash,
            auth_context_hash=auth_context_hash,
        )
    base = cross_signal_feed_queryset(memberships=prepared, filters=filters)
    return _cross_pins_page(
        signal_feed_pins_queryset(base, filters=filters),
        page_size=page_size,
        cursor=cursor,
        scope="cross",
        view_mode="general",
        status=status,
        filter_hash=filter_hash,
        auth_context_hash=auth_context_hash,
    )
