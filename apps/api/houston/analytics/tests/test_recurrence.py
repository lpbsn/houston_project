from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone

import pytest
from django.utils import timezone

from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.recurrence import (
    RECURRENCE_MIN_DISTINCT_DAYS,
    RECURRENCE_MIN_OCCURRENCES,
    RECURRENCE_WINDOW_DAYS,
    analytics_pattern_recurrence_stats,
    build_recurrence_window,
    recurrence_stats_for_visible_pattern_ids,
    recurrent_pattern_ids_queryset,
)
from houston.analytics.services import create_operational_pattern
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.factories import build_membership, create_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def create_signal(
    membership,
    *,
    title="Signal",
    status=Signal.Status.OPEN,
    routing_status=Signal.RoutingStatus.RESOLVED,
    created_at=None,
    resolved_at=None,
    merged_into=None,
    affected_business_unit=None,
    responsible_business_unit=None,
):
    signal = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        status=status,
        routing_status=routing_status,
        title=title,
        structured_summary="Structured signal summary.",
        issue_focus=title.lower().replace(" ", "-"),
        resolved_at=resolved_at,
        merged_into=merged_into,
        last_activity_at=created_at or timezone.now(),
    )
    if created_at is not None:
        Signal.objects.filter(pk=signal.pk).update(created_at=created_at)
        signal.refresh_from_db()
    return signal


def create_pattern(membership, *, label="Pattern"):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
    )


def assign_signal(signal, pattern):
    return SignalPatternAssignment.objects.create(
        signal=signal,
        pattern=pattern,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature=f"sig-{signal.id}",
        assigned_classifier_version="classifier-v1",
        assigned_at=timezone.now(),
    )


def add_signal(membership, pattern, *, title, created_at, **kwargs):
    signal = create_signal(
        membership,
        title=title,
        created_at=created_at,
        **kwargs,
    )
    assign_signal(signal, pattern)
    return signal


def test_recurrence_requires_three_occurrences_and_two_distinct_local_days():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    two_signals = create_pattern(owner, label="Two signals")
    one_day = create_pattern(owner, label="One day")
    recurring = create_pattern(owner, label="Recurring")
    as_of = timezone.now()

    for index in range(2):
        add_signal(
            owner,
            two_signals,
            title=f"Two {index}",
            created_at=as_of - timedelta(days=1, minutes=index),
        )
    for index in range(3):
        add_signal(
            owner,
            one_day,
            title=f"One day {index}",
            created_at=as_of - timedelta(days=1, minutes=index),
        )
    for index, created_at in enumerate(
        [
            as_of - timedelta(days=2),
            as_of - timedelta(days=1),
            as_of - timedelta(hours=1),
        ]
    ):
        add_signal(owner, recurring, title=f"Recurring {index}", created_at=created_at)

    stats = analytics_pattern_recurrence_stats(owner.user, as_of=as_of)

    assert stats[two_signals.id].occurrence_count_30d == 2
    assert stats[two_signals.id].is_recurrent is False
    assert stats[one_day.id].occurrence_count_30d == RECURRENCE_MIN_OCCURRENCES
    assert stats[one_day.id].distinct_day_count_30d == 1
    assert stats[one_day.id].is_recurrent is False
    assert stats[recurring.id].occurrence_count_30d == RECURRENCE_MIN_OCCURRENCES
    assert stats[recurring.id].distinct_day_count_30d >= RECURRENCE_MIN_DISTINCT_DAYS
    assert stats[recurring.id].is_recurrent is True

    recurrent_ids = list(
        recurrent_pattern_ids_queryset(owner.user, as_of=as_of).values_list(
            "pattern_id",
            flat=True,
        )
    )
    assert recurrent_ids == [recurring.id]


def test_recurrence_window_start_is_inclusive_and_end_is_exclusive():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Boundary")
    as_of = timezone.now()
    window_start = as_of - timedelta(days=RECURRENCE_WINDOW_DAYS)

    add_signal(owner, pattern, title="Start", created_at=window_start)
    add_signal(owner, pattern, title="Inside one", created_at=as_of - timedelta(days=1))
    add_signal(owner, pattern, title="Inside two", created_at=as_of - timedelta(hours=1))
    add_signal(owner, pattern, title="End", created_at=as_of)
    add_signal(
        owner,
        pattern,
        title="Before",
        created_at=window_start - timedelta(microseconds=1),
    )

    stats = analytics_pattern_recurrence_stats(owner.user, as_of=as_of)[pattern.id]

    assert build_recurrence_window(as_of).window_start == window_start
    assert stats.occurrence_count_30d == 3
    assert stats.is_recurrent is True


@pytest.mark.parametrize(
    "status",
    [
        Signal.Status.INTERESTING,
        Signal.Status.RESOLVED,
        Signal.Status.ARCHIVED,
    ],
)
def test_recurrence_includes_default_analytics_statuses_and_ignores_resolved_at(status):
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label=f"Status {status}")
    as_of = timezone.now()

    for index, created_at in enumerate(
        [
            as_of - timedelta(days=2),
            as_of - timedelta(days=1),
            as_of - timedelta(hours=1),
        ]
    ):
        add_signal(
            owner,
            pattern,
            title=f"Status {index}",
            status=status,
            created_at=created_at,
            resolved_at=None,
        )

    stats = analytics_pattern_recurrence_stats(owner.user, as_of=as_of)[pattern.id]

    assert stats.is_recurrent is True


def test_recurrence_excludes_canceled_and_merged_sources():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Excluded")
    as_of = timezone.now()
    survivor = create_signal(owner, title="Survivor")

    add_signal(
        owner,
        pattern,
        title="Canceled",
        status=Signal.Status.CANCELED,
        created_at=as_of - timedelta(days=1),
    )
    add_signal(
        owner,
        pattern,
        title="Merged",
        created_at=as_of - timedelta(days=2),
        merged_into=survivor,
    )

    stats = analytics_pattern_recurrence_stats(owner.user, as_of=as_of)

    assert pattern.id not in stats


def test_new_signal_after_resolution_counts_as_new_occurrence():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Resolved then new")
    as_of = timezone.now()
    first = add_signal(
        owner,
        pattern,
        title="Resolved old",
        status=Signal.Status.RESOLVED,
        created_at=as_of - timedelta(days=2),
        resolved_at=as_of - timedelta(days=1),
    )
    Signal.objects.filter(pk=first.pk).update(status=Signal.Status.IN_PROGRESS)
    add_signal(owner, pattern, title="New one", created_at=as_of - timedelta(days=1))

    stats = analytics_pattern_recurrence_stats(owner.user, as_of=as_of)[pattern.id]

    assert stats.occurrence_count_30d == 2


def test_recurrence_counts_distinct_establishment_local_days():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    owner.establishment.timezone = "Europe/Paris"
    owner.establishment.save(update_fields=["timezone"])
    pattern = create_pattern(owner, label="Local days")
    as_of = datetime(2026, 1, 3, 12, tzinfo=dt_timezone.utc)

    for index, created_at in enumerate(
        [
            datetime(2026, 1, 1, 22, 30, tzinfo=dt_timezone.utc),
            datetime(2026, 1, 1, 23, 30, tzinfo=dt_timezone.utc),
            datetime(2026, 1, 2, 10, 0, tzinfo=dt_timezone.utc),
        ]
    ):
        add_signal(owner, pattern, title=f"Local {index}", created_at=created_at)

    stats = analytics_pattern_recurrence_stats(owner.user, as_of=as_of)[pattern.id]

    assert stats.occurrence_count_30d == 3
    assert stats.distinct_day_count_30d == 2
    assert stats.is_recurrent is True


def test_recurrence_supports_multi_establishment_timezones_without_counting_pairs():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    other_establishment = Establishment.objects.create(
        name="Tokyo",
        organization=owner.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="Asia/Tokyo",
    )
    other_membership = create_membership(
        establishment=other_establishment,
        user=owner.user,
        role=EstablishmentMembership.Role.OWNER,
    )
    pattern = create_pattern(owner, label="Multi timezone")
    as_of = datetime(2026, 1, 5, 12, tzinfo=dt_timezone.utc)

    add_signal(
        owner,
        pattern,
        title="UTC day one",
        created_at=datetime(2026, 1, 1, 12, tzinfo=dt_timezone.utc),
    )
    add_signal(
        other_membership,
        pattern,
        title="Tokyo same local day",
        created_at=datetime(2026, 1, 1, 3, tzinfo=dt_timezone.utc),
    )
    add_signal(
        owner,
        pattern,
        title="UTC day two",
        created_at=datetime(2026, 1, 2, 12, tzinfo=dt_timezone.utc),
    )

    stats = analytics_pattern_recurrence_stats(owner.user, as_of=as_of)[pattern.id]

    assert stats.occurrence_count_30d == 3
    assert stats.distinct_day_count_30d == 2
    assert stats.is_recurrent is True


def test_recurrence_respects_manager_scope_and_unassigned_visibility():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    pattern = create_pattern(manager, label="Manager recurring")
    in_scope_bu = create_business_unit(establishment=manager.establishment, key="bar")
    out_scope_bu = create_business_unit(
        establishment=manager.establishment,
        key="kitchen",
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=in_scope_bu,
    )
    as_of = timezone.now()

    add_signal(
        manager,
        pattern,
        title="Scoped one",
        created_at=as_of - timedelta(days=3),
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    add_signal(
        manager,
        pattern,
        title="Scoped two",
        created_at=as_of - timedelta(days=2),
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    add_signal(
        manager,
        pattern,
        title="Unassigned",
        created_at=as_of - timedelta(days=1),
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    add_signal(
        manager,
        pattern,
        title="Hidden BU",
        created_at=as_of - timedelta(hours=1),
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )

    stats = analytics_pattern_recurrence_stats(manager.user, as_of=as_of)[pattern.id]

    assert stats.occurrence_count_30d == 3
    assert stats.is_recurrent is True


def test_pattern_ids_are_restrictive_and_do_not_reveal_inaccessible_patterns():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    hidden_owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    visible_pattern = create_pattern(owner, label="Visible")
    hidden_pattern = create_pattern(hidden_owner, label="Hidden")
    as_of = timezone.now()

    for index, created_at in enumerate(
        [
            as_of - timedelta(days=2),
            as_of - timedelta(days=1),
            as_of - timedelta(hours=1),
        ]
    ):
        add_signal(
            hidden_owner,
            hidden_pattern,
            title=f"Hidden {index}",
            created_at=created_at,
        )
    add_signal(owner, visible_pattern, title="Visible", created_at=as_of - timedelta(days=1))

    hidden_stats = analytics_pattern_recurrence_stats(
        owner.user,
        as_of=as_of,
        pattern_ids=[hidden_pattern.id],
    )
    visible_stats = analytics_pattern_recurrence_stats(
        owner.user,
        as_of=as_of,
        pattern_ids=[visible_pattern.id, hidden_pattern.id],
    )

    assert hidden_stats == {}
    assert set(visible_stats) == {visible_pattern.id}


def test_zero_fill_is_limited_to_known_visible_pattern_ids():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Visible no recent")
    as_of = timezone.now()

    stats = recurrence_stats_for_visible_pattern_ids(
        owner.user,
        as_of=as_of,
        visible_pattern_ids=[pattern.id],
    )

    assert stats[pattern.id].is_recurrent is False
    assert stats[pattern.id].occurrence_count_30d == 0
    assert stats[pattern.id].distinct_day_count_30d == 0


def test_recurrence_rejects_missing_or_naive_as_of():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)

    with pytest.raises(AnalyticsValidationError) as missing:
        analytics_pattern_recurrence_stats(owner.user, as_of=None)
    assert missing.value.code == "analytics_recurrence_as_of_required"

    with pytest.raises(AnalyticsValidationError) as naive:
        analytics_pattern_recurrence_stats(
            owner.user,
            as_of=datetime(2026, 1, 1),
        )
    assert naive.value.code == "analytics_recurrence_as_of_naive"
