from __future__ import annotations

from django.db.models import Q

from houston.signals.models import Signal

DEFAULT_ANALYTICS_SIGNAL_STATUSES = frozenset(
    {
        Signal.Status.OPEN,
        Signal.Status.IN_PROGRESS,
        Signal.Status.INTERESTING,
        Signal.Status.RESOLVED,
        Signal.Status.ARCHIVED,
    }
)
ACTIONABLE_ANALYTICS_SIGNAL_STATUSES = frozenset(
    {
        Signal.Status.OPEN,
        Signal.Status.IN_PROGRESS,
    }
)
RESOLUTION_TIME_ANALYTICS_SIGNAL_STATUSES = frozenset(
    {
        Signal.Status.RESOLVED,
        Signal.Status.ARCHIVED,
    }
)


def default_analytics_signal_q() -> Q:
    return Q(merged_into__isnull=True, status__in=DEFAULT_ANALYTICS_SIGNAL_STATUSES)


def actionable_signal_q() -> Q:
    return Q(
        merged_into__isnull=True,
        status__in=ACTIONABLE_ANALYTICS_SIGNAL_STATUSES,
    )


def recurrence_signal_q() -> Q:
    return default_analytics_signal_q()


def resolution_time_signal_q() -> Q:
    return Q(
        merged_into__isnull=True,
        status__in=RESOLUTION_TIME_ANALYTICS_SIGNAL_STATUSES,
        resolved_at__isnull=False,
    )


def status_anomaly_q() -> Q:
    return Q(
        merged_into__isnull=True,
        status=Signal.Status.RESOLVED,
        resolved_at__isnull=True,
    )


def signal_participates_in_default_analytics(signal: Signal) -> bool:
    if signal.merged_into_id is not None:
        return False
    return signal.status in DEFAULT_ANALYTICS_SIGNAL_STATUSES


def signal_participates_in_actionable_queue(signal: Signal) -> bool:
    if signal.merged_into_id is not None:
        return False
    return signal.status in ACTIONABLE_ANALYTICS_SIGNAL_STATUSES


def signal_participates_in_recurrence(signal: Signal) -> bool:
    return signal_participates_in_default_analytics(signal)


def signal_participates_in_resolution_time(signal: Signal) -> bool:
    if signal.merged_into_id is not None:
        return False
    if signal.status not in RESOLUTION_TIME_ANALYTICS_SIGNAL_STATUSES:
        return False
    return signal.resolved_at is not None


def signal_has_analytics_status_anomaly(signal: Signal) -> bool:
    if signal.merged_into_id is not None:
        return False
    return signal.status == Signal.Status.RESOLVED and signal.resolved_at is None
