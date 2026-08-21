"""Journal reconstruction helpers for Analytics (status_at, end_at_at, coverage)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.utils.dateparse import parse_datetime

from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_CANCELED,
    EXECUTION_LIFECYCLE_EVENT_CREATED,
    EXECUTION_LIFECYCLE_EVENT_DEADLINE_CHANGED,
    EXECUTION_LIFECYCLE_EVENT_HISTORY_BASELINE,
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_LIFECYCLE_EVENT_REACTIVATED,
    EXECUTION_LIFECYCLE_EVENT_REOPENED,
    EXECUTION_LIFECYCLE_EVENT_STARTED,
    EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.analytics.models import AnalyticsHistoryCoverage
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
    SIGNAL_LIFECYCLE_EVENT_CANCELED,
    SIGNAL_LIFECYCLE_EVENT_CREATED,
    SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
    SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING,
    SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
    SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
)
from houston.signals.models import Signal

COVERAGE_COMPLETE = "complete"
COVERAGE_PARTIAL = "partial"
COVERAGE_NOT_COMPARABLE = "not_comparable"

SIGNAL_STATUS_CHANGING_EVENTS = frozenset(
    {
        SIGNAL_LIFECYCLE_EVENT_CREATED,
        SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
        SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING,
        SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
        SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        SIGNAL_LIFECYCLE_EVENT_CANCELED,
        SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS,
        SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN,
    }
)

SIGNAL_EVENT_TO_STATUS = {
    SIGNAL_LIFECYCLE_EVENT_CREATED: Signal.Status.OPEN,
    SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING: Signal.Status.INTERESTING,
    SIGNAL_LIFECYCLE_EVENT_ARCHIVED: Signal.Status.ARCHIVED,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED: Signal.Status.RESOLVED,
    SIGNAL_LIFECYCLE_EVENT_CANCELED: Signal.Status.CANCELED,
    SIGNAL_LIFECYCLE_EVENT_MOVED_IN_PROGRESS: Signal.Status.IN_PROGRESS,
    SIGNAL_LIFECYCLE_EVENT_MOVED_OPEN: Signal.Status.OPEN,
}

EXECUTION_STATUS_CHANGING_EVENTS = frozenset(
    {
        EXECUTION_LIFECYCLE_EVENT_CREATED,
        EXECUTION_LIFECYCLE_EVENT_STARTED,
        EXECUTION_LIFECYCLE_EVENT_HISTORY_BASELINE,
        EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
        EXECUTION_LIFECYCLE_EVENT_VALIDATED,
        EXECUTION_LIFECYCLE_EVENT_CANCELED,
        EXECUTION_LIFECYCLE_EVENT_REOPENED,
        EXECUTION_LIFECYCLE_EVENT_REACTIVATED,
    }
)

EXECUTION_EVENT_TO_STATUS = {
    EXECUTION_LIFECYCLE_EVENT_STARTED: EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_LIFECYCLE_EVENT_VALIDATED: EXECUTION_STATUS_DONE,
    EXECUTION_LIFECYCLE_EVENT_CANCELED: EXECUTION_STATUS_CANCELED,
    EXECUTION_LIFECYCLE_EVENT_REOPENED: EXECUTION_STATUS_IN_PROGRESS,
}


@dataclass(frozen=True)
class JournalEvent:
    event_type: str
    occurred_at: datetime
    metadata_safe: dict[str, Any]


def get_history_reliable_from() -> datetime | None:
    coverage = (
        AnalyticsHistoryCoverage.objects.filter(
            singleton_key=AnalyticsHistoryCoverage.SINGLETON_KEY,
        )
        .only("reliable_from")
        .first()
    )
    if coverage is None:
        return None
    return coverage.reliable_from


def resolve_history_reliable_from(*, now: datetime) -> datetime:
    """Return persisted cutover, or ``now`` when the singleton is not yet written."""
    reliable_from = get_history_reliable_from()
    return reliable_from if reliable_from is not None else now


def coverage_for_window(
    *,
    window_start: datetime,
    window_end: datetime,
    reliable_from: datetime,
    needs_journal: bool,
    previous_end: datetime | None = None,
) -> str:
    if not needs_journal:
        return COVERAGE_COMPLETE
    if previous_end is not None and previous_end <= reliable_from:
        return COVERAGE_NOT_COMPARABLE
    if window_end <= reliable_from:
        return COVERAGE_NOT_COMPARABLE
    if window_start < reliable_from:
        return COVERAGE_PARTIAL
    return COVERAGE_COMPLETE


def comparison_coverage(*, current: str, previous: str) -> str:
    if current == COVERAGE_NOT_COMPARABLE or previous == COVERAGE_NOT_COMPARABLE:
        return COVERAGE_NOT_COMPARABLE
    if current == COVERAGE_PARTIAL or previous == COVERAGE_PARTIAL:
        return COVERAGE_PARTIAL
    return COVERAGE_COMPLETE


def parse_metadata_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    parsed = parse_datetime(str(value))
    return parsed


def _status_from_event(event: JournalEvent, *, fallback: str | None) -> str | None:
    metadata_status = event.metadata_safe.get("to_status") or event.metadata_safe.get(
        "initial_status"
    )
    if metadata_status:
        return str(metadata_status)
    mapped = SIGNAL_EVENT_TO_STATUS.get(event.event_type)
    if mapped is not None:
        return mapped
    return fallback


def signal_status_at(
    *,
    at: datetime,
    reliable_from: datetime,
    events: list[JournalEvent],
) -> str | None:
    """Return reconstructed status strictly before ``at``, or None if not reconstructable."""
    if at < reliable_from:
        return None

    ordered = sorted(
        (event for event in events if event.event_type in SIGNAL_STATUS_CHANGING_EVENTS),
        key=lambda event: (event.occurred_at, event.event_type),
    )
    origin = None
    for event in ordered:
        if event.event_type in {
            SIGNAL_LIFECYCLE_EVENT_CREATED,
            SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
        } and event.occurred_at <= at:
            origin = event
            break
    if origin is None:
        return None
    if origin.event_type == SIGNAL_LIFECYCLE_EVENT_CREATED and origin.occurred_at >= at:
        return None

    status = _status_from_event(origin, fallback=Signal.Status.OPEN)
    for event in ordered:
        if event.occurred_at <= origin.occurred_at:
            continue
        if event.occurred_at >= at:
            break
        if event.event_type in {
            SIGNAL_LIFECYCLE_EVENT_CREATED,
            SIGNAL_LIFECYCLE_EVENT_HISTORY_BASELINE,
        }:
            continue
        status = _status_from_event(event, fallback=status)
    return status


def _execution_status_from_event(event: JournalEvent, *, fallback: str | None) -> str | None:
    metadata_status = event.metadata_safe.get("to_status") or event.metadata_safe.get(
        "initial_status"
    )
    if metadata_status:
        return str(metadata_status)
    mapped = EXECUTION_EVENT_TO_STATUS.get(event.event_type)
    if mapped is not None:
        return mapped
    if event.event_type == EXECUTION_LIFECYCLE_EVENT_MARKED_DONE:
        to_status = event.metadata_safe.get("to_status")
        if to_status:
            return str(to_status)
        return EXECUTION_STATUS_DONE
    return fallback


def execution_status_at(
    *,
    at: datetime,
    reliable_from: datetime,
    events: list[JournalEvent],
) -> str | None:
    if at < reliable_from:
        return None

    ordered = sorted(
        (event for event in events if event.event_type in EXECUTION_STATUS_CHANGING_EVENTS),
        key=lambda event: (event.occurred_at, event.event_type),
    )
    origin = None
    for event in ordered:
        if event.event_type in {
            EXECUTION_LIFECYCLE_EVENT_CREATED,
            EXECUTION_LIFECYCLE_EVENT_HISTORY_BASELINE,
        } and event.occurred_at <= at:
            origin = event
            break
    if origin is None:
        return None
    if origin.event_type == EXECUTION_LIFECYCLE_EVENT_CREATED and origin.occurred_at >= at:
        return None

    status = _execution_status_from_event(origin, fallback=EXECUTION_STATUS_SCHEDULED)
    for event in ordered:
        if event.occurred_at <= origin.occurred_at:
            continue
        if event.occurred_at >= at:
            break
        if event.event_type in {
            EXECUTION_LIFECYCLE_EVENT_CREATED,
            EXECUTION_LIFECYCLE_EVENT_HISTORY_BASELINE,
        }:
            continue
        status = _execution_status_from_event(event, fallback=status)
    return status


def execution_end_at_at(
    *,
    at: datetime,
    reliable_from: datetime,
    events: list[JournalEvent],
) -> datetime | None:
    if at < reliable_from:
        return None

    ordered = sorted(events, key=lambda event: (event.occurred_at, event.event_type))
    origin_end_at = None
    last_deadline_to = None
    terminal_end_at = None
    terminal_occurred_at = None
    for event in ordered:
        if event.occurred_at >= at:
            break
        if event.event_type in {
            EXECUTION_LIFECYCLE_EVENT_CREATED,
            EXECUTION_LIFECYCLE_EVENT_HISTORY_BASELINE,
            EXECUTION_LIFECYCLE_EVENT_STARTED,
        }:
            parsed = parse_metadata_datetime(event.metadata_safe.get("end_at"))
            if parsed is not None or "end_at" in event.metadata_safe:
                origin_end_at = parsed
        elif event.event_type == EXECUTION_LIFECYCLE_EVENT_DEADLINE_CHANGED:
            last_deadline_to = parse_metadata_datetime(event.metadata_safe.get("to_end_at"))
        elif event.event_type in {
            EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
            EXECUTION_LIFECYCLE_EVENT_VALIDATED,
            EXECUTION_LIFECYCLE_EVENT_CANCELED,
        }:
            parsed = parse_metadata_datetime(event.metadata_safe.get("end_at"))
            if parsed is not None or "end_at" in event.metadata_safe:
                terminal_end_at = parsed
                terminal_occurred_at = event.occurred_at

    status = execution_status_at(at=at, reliable_from=reliable_from, events=events)
    if status in {EXECUTION_STATUS_DONE, EXECUTION_STATUS_CANCELED} and terminal_occurred_at is not None:
        return terminal_end_at if terminal_end_at is not None else (
            last_deadline_to if last_deadline_to is not None else origin_end_at
        )
    if last_deadline_to is not None:
        return last_deadline_to
    return origin_end_at


def first_signal_created_at(events: list[JournalEvent], *, fallback: datetime | None) -> datetime | None:
    created = [
        event.occurred_at
        for event in events
        if event.event_type == SIGNAL_LIFECYCLE_EVENT_CREATED
    ]
    if created:
        return min(created)
    return fallback
