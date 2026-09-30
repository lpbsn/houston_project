from __future__ import annotations

from datetime import datetime
from datetime import timezone as dt_timezone

import pytest

from houston.analytics.dashboard import (
    REPEATED_PATTERNS_IN_PERIOD,
    REPEATED_PATTERNS_IN_PERIOD_DEFINITION,
    REPEATED_PATTERNS_MIN_SIGNALS,
    get_analytics_dashboard,
)
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.recurrence import (
    PATTERN_RECURRENCE_30D,
    PATTERN_RECURRENCE_30D_DEFINITION,
    RECURRENCE_MIN_DISTINCT_DAYS,
    RECURRENCE_MIN_OCCURRENCES,
    RECURRENCE_WINDOW_DAYS,
    analytics_pattern_recurrence_stats,
)
from houston.analytics.services import create_operational_pattern
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db

AS_OF = datetime(2026, 6, 15, 15, 0, tzinfo=dt_timezone.utc)


def test_metric_names_stay_distinct_and_read_time():
    assert PATTERN_RECURRENCE_30D == "pattern_recurrence_30d"
    assert REPEATED_PATTERNS_IN_PERIOD == "repeated_patterns_in_period"
    assert PATTERN_RECURRENCE_30D != REPEATED_PATTERNS_IN_PERIOD
    assert PATTERN_RECURRENCE_30D_DEFINITION.name == PATTERN_RECURRENCE_30D
    assert REPEATED_PATTERNS_IN_PERIOD_DEFINITION.name == REPEATED_PATTERNS_IN_PERIOD
    assert PATTERN_RECURRENCE_30D_DEFINITION.provenance != (
        REPEATED_PATTERNS_IN_PERIOD_DEFINITION.provenance
    )
    assert "OLTP" in PATTERN_RECURRENCE_30D_DEFINITION.freshness
    assert "OLTP" in REPEATED_PATTERNS_IN_PERIOD_DEFINITION.freshness
    assert RECURRENCE_WINDOW_DAYS == 30
    assert RECURRENCE_MIN_OCCURRENCES == 3
    assert RECURRENCE_MIN_DISTINCT_DAYS == 2
    assert REPEATED_PATTERNS_MIN_SIGNALS == 2


def test_pattern_recurrence_30d_is_not_repeated_patterns_in_period():
    """The two metrics disagree on the same signals.

    Recalculating either one from the other fails at least one assertion.
    """

    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    same_day = _pattern(owner, "Same civil day")
    older = _pattern(owner, "Outside dashboard week")
    with_cancel = _pattern(owner, "Canceled still counted on the dashboard")

    _assign(owner, same_day, "Morning", datetime(2026, 6, 15, 10, 0, tzinfo=dt_timezone.utc))
    _assign(owner, same_day, "Noon", datetime(2026, 6, 15, 12, 0, tzinfo=dt_timezone.utc))

    _assign(owner, older, "Day one", datetime(2026, 5, 20, 10, 0, tzinfo=dt_timezone.utc))
    _assign(owner, older, "Day two", datetime(2026, 5, 21, 10, 0, tzinfo=dt_timezone.utc))
    _assign(owner, older, "Day two later", datetime(2026, 5, 21, 16, 0, tzinfo=dt_timezone.utc))

    _assign(owner, with_cancel, "Open early", datetime(2026, 6, 13, 10, 0, tzinfo=dt_timezone.utc))
    _assign(owner, with_cancel, "Open later", datetime(2026, 6, 14, 10, 0, tzinfo=dt_timezone.utc))
    _assign(
        owner,
        with_cancel,
        "Canceled",
        datetime(2026, 6, 14, 12, 0, tzinfo=dt_timezone.utc),
        status=Signal.Status.CANCELED,
    )

    recurrence = analytics_pattern_recurrence_stats(owner.user, as_of=AS_OF)
    dashboard = get_analytics_dashboard(
        owner.user,
        period_days=7,
        establishment_id=owner.establishment_id,
        now=AS_OF,
    )
    repeated = {item.pattern_id: item.signal_count for item in dashboard.recurring_patterns.items}

    same_day_stats = recurrence[same_day.id]
    assert same_day_stats.is_recurrent is False
    assert same_day_stats.occurrence_count_30d == 2
    assert same_day_stats.distinct_day_count_30d == 1
    assert repeated[same_day.id] == 2

    older_stats = recurrence[older.id]
    assert older_stats.is_recurrent is True
    assert older_stats.occurrence_count_30d == 3
    assert older_stats.distinct_day_count_30d == 2
    assert older.id not in repeated

    canceled_stats = recurrence[with_cancel.id]
    assert canceled_stats.is_recurrent is False
    assert canceled_stats.occurrence_count_30d == 2
    assert repeated[with_cancel.id] == 3


def _pattern(membership, label):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
    )


def _assign(membership, pattern, title, created_at, *, status=Signal.Status.OPEN):
    signal = Signal.objects.create(
        establishment=membership.establishment,
        status=status,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary="Structured signal summary.",
        issue_focus=title.lower().replace(" ", "-"),
        last_activity_at=created_at,
        canceled_at=created_at if status == Signal.Status.CANCELED else None,
    )
    Signal.objects.filter(pk=signal.pk).update(created_at=created_at, updated_at=created_at)
    SignalPatternAssignment.objects.create(
        signal=signal,
        pattern=pattern,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature=f"sig-{signal.id}",
        assigned_classifier_version="classifier-v1",
        assigned_at=created_at,
    )
    return signal
