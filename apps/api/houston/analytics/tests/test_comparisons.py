from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from houston.analytics.comparisons import (
    RELATIVE_CHANGE_COMPUTED,
    RELATIVE_CHANGE_NOT_APPLICABLE,
    RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO,
    get_analytics_kpi_comparison,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
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
    affected_business_unit=None,
    responsible_business_unit=None,
):
    moment = created_at or timezone.now()
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
        last_activity_at=moment,
    )
    if created_at is not None:
        Signal.objects.filter(pk=signal.pk).update(created_at=created_at)
        signal.refresh_from_db()
    return signal


def set_signal_times(signal, *, created_at=None, resolved_at=None):
    updates = {}
    if created_at is not None:
        updates["created_at"] = created_at
    if resolved_at is not None:
        updates["resolved_at"] = resolved_at
    Signal.objects.filter(pk=signal.pk).update(**updates)
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


def create_resolved_signal_with_duration(
    membership,
    *,
    resolved_at,
    duration,
    title,
):
    signal = create_signal(
        membership,
        status=Signal.Status.RESOLVED,
        title=title,
    )
    return set_signal_times(
        signal,
        created_at=resolved_at - duration,
        resolved_at=resolved_at,
    )


def test_previous_period_is_adjacent_same_duration_without_boundary_double_counting():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    period_start = timezone.now()
    period_end = period_start + timedelta(days=7)
    previous_start = period_start - timedelta(days=7)

    create_signal(owner, title="Previous start", created_at=previous_start)
    create_signal(owner, title="Current start", created_at=period_start)
    create_signal(owner, title="Current end", created_at=period_end)

    result = get_analytics_kpi_comparison(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )

    assert result.previous_period.period_start == previous_start
    assert result.previous_period.period_end == period_start
    assert result.current_period.period_start == period_start
    assert result.current_period.period_end == period_end
    assert result.previous_kpis.actionable_signals_count == 1
    assert result.current_kpis.actionable_signals_count == 1
    assert result.actionable_signals_count.current_value == 1
    assert result.actionable_signals_count.previous_value == 1


def test_comparison_uses_created_at_for_volumes_and_resolved_at_for_resolution():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    period_start = timezone.now()
    period_end = period_start + timedelta(days=7)
    previous_resolution = period_start - timedelta(days=1)
    current_resolution = period_start + timedelta(days=1)

    create_signal(
        owner,
        title="Created current unresolved",
        created_at=period_start + timedelta(hours=2),
    )
    create_resolved_signal_with_duration(
        owner,
        resolved_at=previous_resolution,
        duration=timedelta(hours=2),
        title="Resolved previous",
    )
    create_resolved_signal_with_duration(
        owner,
        resolved_at=current_resolution,
        duration=timedelta(hours=4),
        title="Resolved current",
    )

    result = get_analytics_kpi_comparison(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )

    assert result.current_kpis.analytics_signal_population_count == 2
    assert result.previous_kpis.analytics_signal_population_count == 1
    assert result.current_kpis.median_resolution_seconds == 14400
    assert result.previous_kpis.median_resolution_seconds == 7200


def test_comparison_recalculates_periods_from_current_assignments_not_snapshots():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner)
    period_start = timezone.now()
    period_end = period_start + timedelta(days=7)
    historical_signal = create_signal(
        owner,
        title="Historical signal",
        created_at=period_start - timedelta(days=1),
    )

    before_assignment = get_analytics_kpi_comparison(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )
    assign_signal(historical_signal, pattern)
    after_assignment = get_analytics_kpi_comparison(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )

    assert before_assignment.previous_kpis.signals_analyzed_count == 0
    assert after_assignment.previous_kpis.signals_analyzed_count == 1
    assert after_assignment.previous_kpis.operational_patterns_count == 1


def test_relative_change_is_ratio_and_previous_zero_is_undefined():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner)
    period_start = timezone.now()
    period_end = period_start + timedelta(days=7)
    first_current = create_signal(
        owner,
        title="Current one",
        created_at=period_start + timedelta(hours=1),
    )
    second_current = create_signal(
        owner,
        title="Current two",
        created_at=period_start + timedelta(hours=2),
    )

    assign_signal(first_current, pattern)
    assign_signal(second_current, pattern)

    result = get_analytics_kpi_comparison(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )

    assert result.signals_analyzed_count.current_value == 2
    assert result.signals_analyzed_count.previous_value == 0
    assert result.signals_analyzed_count.absolute_delta == 2
    assert result.signals_analyzed_count.relative_change is None
    assert (
        result.signals_analyzed_count.relative_change_status
        == RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO
    )

    previous_signal = create_signal(
        owner,
        title="Previous analyzed",
        created_at=period_start - timedelta(days=1),
    )
    assign_signal(previous_signal, pattern)

    recomputed = get_analytics_kpi_comparison(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )

    assert recomputed.signals_analyzed_count.previous_value == 1
    assert recomputed.signals_analyzed_count.absolute_delta == 1
    assert recomputed.signals_analyzed_count.relative_change == 1
    assert (
        recomputed.signals_analyzed_count.relative_change_status
        == RELATIVE_CHANGE_COMPUTED
    )


def test_none_metric_values_are_not_applicable_and_recurrence_is_neutral():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    period_start = timezone.now()
    period_end = period_start + timedelta(days=7)

    result = get_analytics_kpi_comparison(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )

    assert result.median_resolution_seconds.current_value is None
    assert result.median_resolution_seconds.previous_value is None
    assert result.median_resolution_seconds.absolute_delta is None
    assert result.median_resolution_seconds.relative_change is None
    assert (
        result.median_resolution_seconds.relative_change_status
        == RELATIVE_CHANGE_NOT_APPLICABLE
    )
    assert result.recurring_patterns_count.current_value is None
    assert result.recurring_patterns_count.previous_value is None
    assert (
        result.recurring_patterns_count.relative_change_status
        == RELATIVE_CHANGE_NOT_APPLICABLE
    )
    assert result.recurrence_status == "not_computed_until_ticket_16"


def test_current_and_previous_resolution_medians_support_even_and_odd_counts():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    period_start = timezone.now()
    period_end = period_start + timedelta(days=7)
    previous_resolution = period_start - timedelta(days=1)
    current_resolution = period_start + timedelta(days=1)

    create_resolved_signal_with_duration(
        owner,
        resolved_at=previous_resolution,
        duration=timedelta(hours=1),
        title="Previous one",
    )
    create_resolved_signal_with_duration(
        owner,
        resolved_at=previous_resolution,
        duration=timedelta(hours=5),
        title="Previous five",
    )
    create_resolved_signal_with_duration(
        owner,
        resolved_at=current_resolution,
        duration=timedelta(hours=1),
        title="Current one",
    )
    create_resolved_signal_with_duration(
        owner,
        resolved_at=current_resolution,
        duration=timedelta(hours=3),
        title="Current three",
    )
    create_resolved_signal_with_duration(
        owner,
        resolved_at=current_resolution,
        duration=timedelta(hours=5),
        title="Current five",
    )

    result = get_analytics_kpi_comparison(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )

    assert result.previous_kpis.median_resolution_seconds == 10800
    assert result.current_kpis.median_resolution_seconds == 10800
    assert result.median_resolution_seconds.absolute_delta == 0
    assert result.median_resolution_seconds.relative_change == 0


def test_comparison_respects_organization_establishment_and_manager_scope():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    in_scope_bu = create_business_unit(establishment=manager.establishment, key="bar")
    out_scope_bu = create_business_unit(
        establishment=manager.establishment,
        key="kitchen",
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=in_scope_bu,
    )
    hidden_establishment = Establishment.objects.create(
        name="Hidden",
        organization=manager.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    hidden_membership = create_membership(
        establishment=hidden_establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    period_start = timezone.now()
    period_end = period_start + timedelta(days=7)

    create_signal(
        manager,
        title="In scope",
        created_at=period_start + timedelta(hours=1),
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    create_signal(
        manager,
        title="Out scope",
        created_at=period_start + timedelta(hours=2),
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    create_signal(
        manager,
        title="Unassigned",
        created_at=period_start + timedelta(hours=3),
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
    )
    create_signal(
        hidden_membership,
        title="Hidden establishment",
        created_at=period_start + timedelta(hours=4),
    )

    result = get_analytics_kpi_comparison(
        manager.user,
        period_start=period_start,
        period_end=period_end,
        organization_id=manager.establishment.organization_id,
        establishment_id=manager.establishment_id,
    )

    assert result.current_kpis.analytics_signal_population_count == 2
    assert result.current_kpis.actionable_signals_count == 2


def test_patterns_are_compared_only_through_signals_readable_in_each_period():
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
    visible_pattern = create_pattern(owner, label="Visible")
    hidden_pattern = create_pattern(owner, label="Hidden")
    period_start = timezone.now()
    period_end = period_start + timedelta(days=7)

    visible_signal = create_signal(
        owner,
        title="Visible current",
        created_at=period_start + timedelta(hours=1),
    )
    hidden_signal = create_signal(
        hidden_membership,
        title="Hidden current",
        created_at=period_start + timedelta(hours=2),
    )
    assign_signal(visible_signal, visible_pattern)
    assign_signal(hidden_signal, hidden_pattern)

    result = get_analytics_kpi_comparison(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )

    assert result.current_kpis.signals_analyzed_count == 1
    assert result.current_kpis.operational_patterns_count == 1
    assert result.operational_patterns_count.current_value == 1


@pytest.mark.parametrize("days", [7, 30, 90])
def test_comparison_supports_product_period_lengths_as_closed_intervals(days):
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    period_end = timezone.now()
    period_start = period_end - timedelta(days=days)

    result = get_analytics_kpi_comparison(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )

    assert result.current_period.period_start == period_start
    assert result.current_period.period_end == period_end
    assert result.previous_period.period_start == period_start - timedelta(days=days)
    assert result.previous_period.period_end == period_start


@pytest.mark.parametrize(
    ("period_start", "period_end", "expected_code"),
    [
        (None, "end", "analytics_comparison_period_required"),
        ("start", None, "analytics_comparison_period_required"),
        (datetime(2026, 1, 1), "end", "analytics_period_start_naive"),
        ("same", "same", "analytics_period_invalid"),
        ("end", "start", "analytics_period_invalid"),
    ],
)
def test_comparison_rejects_open_naive_empty_or_inverted_periods(
    period_start,
    period_end,
    expected_code,
):
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    start = timezone.now()
    end = start + timedelta(days=7)
    values = {
        "start": start,
        "end": end,
        "same": start,
        None: None,
    }

    with pytest.raises(AnalyticsValidationError) as exc_info:
        get_analytics_kpi_comparison(
            owner.user,
            period_start=values.get(period_start, period_start),
            period_end=values.get(period_end, period_end),
        )

    assert exc_info.value.code == expected_code
