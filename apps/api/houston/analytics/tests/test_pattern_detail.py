from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from houston.analytics.comparisons import (
    RELATIVE_CHANGE_COMPUTED,
    RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.pattern_detail import (
    MAX_PATTERN_DETAIL_BUSINESS_UNITS,
    MAX_PATTERN_DETAIL_ESTABLISHMENTS,
    TREND_TIMEZONE_UTC,
    UNASSIGNED_BUSINESS_UNIT_LABEL,
    get_analytics_pattern_detail,
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
    merged_into=None,
    affected_business_unit=None,
    responsible_business_unit=None,
):
    signal = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        routing_status=routing_status,
        status=status,
        title=title,
        structured_summary="Structured signal summary.",
        issue_focus=title.lower().replace(" ", "-"),
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


def test_pattern_detail_counts_current_previous_trend_and_actionable_scope():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Water leak")
    start = datetime(2026, 1, 8, 0, tzinfo=dt_timezone.utc)
    end = datetime(2026, 1, 15, 0, tzinfo=dt_timezone.utc)
    previous_start = start - timedelta(days=7)

    add_signal(owner, pattern, title="Previous", created_at=previous_start)
    add_signal(owner, pattern, title="Current start", created_at=start)
    add_signal(
        owner,
        pattern,
        title="Interesting",
        status=Signal.Status.INTERESTING,
        created_at=start + timedelta(days=1),
    )
    add_signal(
        owner,
        pattern,
        title="Latest",
        status=Signal.Status.IN_PROGRESS,
        created_at=start + timedelta(days=3),
    )
    add_signal(owner, pattern, title="End excluded", created_at=end)

    result = get_analytics_pattern_detail(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert result.identity.pattern_id == pattern.id
    assert result.current_period.period_start == start
    assert result.previous_period.period_start == previous_start
    assert result.metrics.signal_count == 3
    assert result.metrics.previous_signal_count == 1
    assert result.metrics.signal_count_comparison.absolute_delta == 2
    assert result.metrics.signal_count_comparison.relative_change == 2
    assert (
        result.metrics.signal_count_comparison.relative_change_status
        == RELATIVE_CHANGE_COMPUTED
    )
    assert result.metrics.actionable_signal_count == 2
    assert result.metrics.last_seen_at == start + timedelta(days=3)
    assert sum(bucket.signal_count for bucket in result.trend) == 3
    assert {bucket.signal_count for bucket in result.trend} >= {0, 1}
    assert result.drilldown_context.pattern_id == pattern.id


def test_pattern_detail_masks_missing_out_of_scope_and_previous_only_patterns():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    hidden_owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Visible")
    previous_only = create_pattern(owner, label="Previous only")
    hidden_pattern = create_pattern(hidden_owner, label="Hidden")
    start = timezone.now()
    end = start + timedelta(days=1)

    add_signal(owner, pattern, title="Visible", created_at=start)
    add_signal(owner, previous_only, title="Old", created_at=start - timedelta(days=1))
    add_signal(hidden_owner, hidden_pattern, title="Hidden", created_at=start)

    for pattern_id in [previous_only.id, hidden_pattern.id, "not-a-uuid"]:
        with pytest.raises(AnalyticsValidationError) as exc_info:
            get_analytics_pattern_detail(
                owner.user,
                pattern_id=pattern_id,
                period_start=start,
                period_end=end,
            )
        assert exc_info.value.code == "analytics_pattern_not_found"


def test_pattern_detail_uses_only_readable_signals_for_shared_pattern():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    hidden_establishment = Establishment.objects.create(
        name="Hidden",
        organization=owner.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    hidden_membership = create_membership(
        establishment=hidden_establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    pattern = create_pattern(owner, label="Shared")
    start = timezone.now()
    end = start + timedelta(days=1)

    add_signal(owner, pattern, title="Visible", created_at=start)
    add_signal(hidden_membership, pattern, title="Hidden", created_at=start)

    result = get_analytics_pattern_detail(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert result.metrics.signal_count == 1
    assert result.establishment_bucket_count == 1
    assert result.establishments[0].name == owner.establishment.name


def test_pattern_detail_respects_manager_business_unit_and_unassigned_scope():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    pattern = create_pattern(manager, label="Manager visible")
    in_scope_bu = create_business_unit(establishment=manager.establishment, key="bar")
    out_scope_bu = create_business_unit(
        establishment=manager.establishment,
        key="kitchen",
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=in_scope_bu,
    )
    start = timezone.now()
    end = start + timedelta(days=1)

    add_signal(
        manager,
        pattern,
        title="Scoped",
        created_at=start,
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    add_signal(
        manager,
        pattern,
        title="Unassigned",
        created_at=start + timedelta(hours=1),
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    add_signal(
        manager,
        pattern,
        title="Hidden BU",
        created_at=start + timedelta(hours=2),
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )

    result = get_analytics_pattern_detail(
        manager.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert result.metrics.signal_count == 2


def test_pattern_detail_excludes_canceled_and_merged_but_includes_default_statuses():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Status mix")
    start = timezone.now()
    end = start + timedelta(days=1)
    survivor = create_signal(owner, title="Survivor", created_at=start)

    for index, status in enumerate(
        [
            Signal.Status.OPEN,
            Signal.Status.INTERESTING,
            Signal.Status.RESOLVED,
            Signal.Status.ARCHIVED,
        ]
    ):
        add_signal(
            owner,
            pattern,
            title=f"Included {status}",
            status=status,
            created_at=start + timedelta(minutes=index),
        )
    add_signal(
        owner,
        pattern,
        title="Canceled",
        status=Signal.Status.CANCELED,
        created_at=start + timedelta(minutes=10),
    )
    add_signal(
        owner,
        pattern,
        title="Merged",
        merged_into=survivor,
        created_at=start + timedelta(minutes=11),
    )

    result = get_analytics_pattern_detail(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )
    status_counts = {
        bucket.status: bucket.signal_count for bucket in result.status_distribution
    }

    assert result.metrics.signal_count == 4
    assert status_counts[Signal.Status.OPEN] == 1
    assert status_counts[Signal.Status.INTERESTING] == 1
    assert status_counts[Signal.Status.RESOLVED] == 1
    assert status_counts[Signal.Status.ARCHIVED] == 1
    assert status_counts[Signal.Status.CANCELED] == 0
    assert sum(status_counts.values()) == result.metrics.signal_count


def test_pattern_detail_zero_fills_recurrence_for_visible_old_pattern():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Old visible")
    end = timezone.now()
    start = end - timedelta(days=90)
    add_signal(
        owner,
        pattern,
        title="Old",
        created_at=end - timedelta(days=60),
    )

    result = get_analytics_pattern_detail(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert result.is_recurrent is False
    assert result.occurrence_count_30d == 0
    assert result.distinct_day_count_30d == 0


def test_pattern_detail_uses_explicit_establishment_timezone_for_trend_and_dst():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    owner.establishment.timezone = "Europe/Paris"
    owner.establishment.save(update_fields=["timezone"])
    pattern = create_pattern(owner, label="DST")
    start = datetime(2026, 3, 28, 0, tzinfo=dt_timezone.utc)
    end = datetime(2026, 3, 31, 0, tzinfo=dt_timezone.utc)
    add_signal(
        owner,
        pattern,
        title="Before DST",
        created_at=datetime(2026, 3, 28, 12, tzinfo=dt_timezone.utc),
    )
    add_signal(
        owner,
        pattern,
        title="After DST",
        created_at=datetime(2026, 3, 29, 23, tzinfo=dt_timezone.utc),
    )

    result = get_analytics_pattern_detail(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
        establishment_id=owner.establishment_id,
    )

    assert result.trend_timezone == "Europe/Paris"
    bucket_offsets = {
        bucket.bucket_date: bucket.bucket_start.utcoffset() for bucket in result.trend
    }
    assert bucket_offsets[datetime(2026, 3, 29).date()] == timedelta(hours=1)
    assert bucket_offsets[datetime(2026, 3, 30).date()] == timedelta(hours=2)
    assert sum(bucket.signal_count for bucket in result.trend) == 2


def test_pattern_detail_trend_buckets_are_clipped_to_non_midnight_period_bounds():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    owner.establishment.timezone = "Europe/Paris"
    owner.establishment.save(update_fields=["timezone"])
    pattern = create_pattern(owner, label="Clipped DST")
    trend_tz = ZoneInfo("Europe/Paris")
    start = datetime(2026, 3, 28, 10, 30, tzinfo=dt_timezone.utc)
    end = datetime(2026, 3, 30, 9, 15, tzinfo=dt_timezone.utc)
    add_signal(
        owner,
        pattern,
        title="Inside first partial day",
        created_at=datetime(2026, 3, 28, 12, tzinfo=dt_timezone.utc),
    )
    add_signal(
        owner,
        pattern,
        title="Inside DST day",
        created_at=datetime(2026, 3, 29, 12, tzinfo=dt_timezone.utc),
    )
    add_signal(
        owner,
        pattern,
        title="Outside before",
        created_at=start - timedelta(minutes=1),
    )
    add_signal(
        owner,
        pattern,
        title="Outside end",
        created_at=end,
    )

    result = get_analytics_pattern_detail(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
        establishment_id=owner.establishment_id,
    )

    assert result.trend_timezone == "Europe/Paris"
    assert result.trend[0].bucket_start == start.astimezone(trend_tz)
    assert result.trend[-1].bucket_end == end.astimezone(trend_tz)
    assert result.trend[1].bucket_start == datetime(
        2026,
        3,
        29,
        0,
        0,
        tzinfo=trend_tz,
    )
    assert result.trend[1].bucket_end == datetime(
        2026,
        3,
        30,
        0,
        0,
        tzinfo=trend_tz,
    )
    assert result.trend[1].bucket_start.utcoffset() == timedelta(hours=1)
    assert result.trend[1].bucket_end.utcoffset() == timedelta(hours=2)
    assert sum(bucket.signal_count for bucket in result.trend) == 2


def test_pattern_detail_multi_establishment_scope_uses_utc_independent_of_contributors():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    owner.establishment.timezone = "Europe/Paris"
    owner.establishment.save(update_fields=["timezone"])
    other_establishment = Establishment.objects.create(
        name="Tokyo",
        organization=owner.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="Asia/Tokyo",
    )
    create_membership(
        establishment=other_establishment,
        user=owner.user,
        role=EstablishmentMembership.Role.OWNER,
    )
    pattern = create_pattern(owner, label="Multi scope")
    start = datetime(2026, 1, 1, 0, tzinfo=dt_timezone.utc)
    end = datetime(2026, 1, 8, 0, tzinfo=dt_timezone.utc)
    add_signal(owner, pattern, title="Only contributor", created_at=start)

    result = get_analytics_pattern_detail(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert result.trend_timezone == TREND_TIMEZONE_UTC
    assert [bucket.bucket_date for bucket in result.trend][0] == start.date()


def test_pattern_detail_distribution_summaries_are_bounded_with_other_counts():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Distributions")
    start = timezone.now()
    end = start + timedelta(days=1)
    memberships = [owner]
    for index in range(MAX_PATTERN_DETAIL_ESTABLISHMENTS + 2):
        establishment = Establishment.objects.create(
            name=f"Site {index:02d}",
            organization=owner.establishment.organization,
            status=Establishment.Status.ACTIVE,
            timezone="UTC",
        )
        memberships.append(
            create_membership(
                establishment=establishment,
                user=owner.user,
                role=EstablishmentMembership.Role.OWNER,
            )
        )
    for index, membership in enumerate(memberships):
        business_unit = create_business_unit(
            establishment=membership.establishment,
            key=f"bu-{index}",
        )
        add_signal(
            membership,
            pattern,
            title=f"Signal {index}",
            created_at=start + timedelta(minutes=index),
            responsible_business_unit=business_unit,
        )
    add_signal(
        memberships[1],
        pattern,
        title="Extra for first",
        created_at=start + timedelta(hours=1),
        responsible_business_unit=None,
    )

    result = get_analytics_pattern_detail(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert result.establishment_bucket_count == len(memberships)
    assert len(result.establishments) == MAX_PATTERN_DETAIL_ESTABLISHMENTS
    assert result.establishment_other_signal_count > 0
    assert result.business_unit_bucket_count == len(memberships) + 1
    assert len(result.responsible_business_units) == MAX_PATTERN_DETAIL_BUSINESS_UNITS
    assert result.business_unit_other_signal_count > 0
    assert any(
        bucket.name == UNASSIGNED_BUSINESS_UNIT_LABEL
        for bucket in result.responsible_business_units
    ) or result.business_unit_other_signal_count > 0


def test_pattern_detail_previous_zero_comparison_is_undefined():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="No previous")
    start = timezone.now()
    end = start + timedelta(days=1)
    add_signal(owner, pattern, title="Current", created_at=start)

    result = get_analytics_pattern_detail(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert result.metrics.previous_signal_count == 0
    assert result.metrics.signal_count_comparison.relative_change is None
    assert (
        result.metrics.signal_count_comparison.relative_change_status
        == RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO
    )
