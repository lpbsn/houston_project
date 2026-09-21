from __future__ import annotations

from dataclasses import dataclass

from django.db.models import QuerySet

from houston.signals.feed_cursor import (
    SignalFeedCursor,
    apply_signal_feed_cursor,
    encode_signal_feed_cursor,
    status_for_signal_feed_cursor,
)
from houston.signals.models import Signal

FEED_SECTION_STATUS_ORDER = (
    Signal.Status.OPEN,
    Signal.Status.IN_PROGRESS,
    Signal.Status.INTERESTING,
    Signal.Status.RESOLVED,
    Signal.Status.CANCELED,
)


class SignalFeedPaginationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class SignalFeedSectionPage:
    status: str
    items: list[Signal]
    next_cursor: str | None
    has_more: bool


def paginate_signal_feed_sections(
    queryset: QuerySet[Signal],
    *,
    page_size: int,
    requested_statuses: tuple[str, ...],
    cursor: SignalFeedCursor | None,
) -> list[SignalFeedSectionPage]:
    if cursor is not None:
        if len(requested_statuses) != 1:
            raise SignalFeedPaginationError("cursor requires exactly one statuses value.")
        requested = requested_statuses[0]
        encoded = status_for_signal_feed_cursor(cursor)
        if encoded != requested:
            raise SignalFeedPaginationError("cursor status does not match statuses.")
        return [_paginate_section(queryset, requested, page_size, cursor)]

    statuses = requested_statuses or FEED_SECTION_STATUS_ORDER
    ordered = [status for status in FEED_SECTION_STATUS_ORDER if status in statuses]
    sections: list[SignalFeedSectionPage] = []
    for status in ordered:
        page = _paginate_section(queryset, status, page_size, None)
        if page.items:
            sections.append(page)
    return sections


def _paginate_section(
    queryset: QuerySet[Signal],
    status: str,
    page_size: int,
    cursor: SignalFeedCursor | None,
) -> SignalFeedSectionPage:
    section_qs = queryset.filter(status=status)
    if cursor is not None:
        section_qs = apply_signal_feed_cursor(section_qs, cursor)
    candidates = list(section_qs[: page_size + 1])
    has_more = len(candidates) > page_size
    items = candidates[:page_size]
    next_cursor = encode_signal_feed_cursor(items[-1]) if has_more and items else None
    return SignalFeedSectionPage(
        status=status,
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
    )
