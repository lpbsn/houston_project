from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from django.utils import timezone

from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.kpis import (
    RECURRENCE_STATUS_NOT_COMPUTED,
    get_analytics_kpis,
)
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
    affected_business_unit=None,
    responsible_business_unit=None,
    created_at=None,
    resolved_at=None,
    merged_into=None,
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
    updates = {}
    if created_at is not None:
        updates["created_at"] = created_at
    if updates:
        Signal.objects.filter(pk=signal.pk).update(**updates)
        signal.refresh_from_db()
    return signal


def create_pattern(membership, *, label="Pattern"):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
    )


def assign_signal(
    signal,
    pattern=None,
    *,
    status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
    source=SignalPatternAssignment.AssignmentSource.CLASSIFIER,
):
    has_pattern = pattern is not None
    return SignalPatternAssignment.objects.create(
        signal=signal,
        pattern=pattern,
        classification_status=status,
        assigned_signature=f"sig-{signal.id}" if has_pattern else "",
        assigned_classifier_version="classifier-v1" if has_pattern else "",
        assigned_at=timezone.now() if has_pattern else None,
        assignment_source=source,
        owner_correction_signature=f"owner-{signal.id}"
        if source == SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
        else "",
    )


def set_signal_times(signal, *, created_at=None, resolved_at=None):
    updates = {}
    if created_at is not None:
        updates["created_at"] = created_at
    if resolved_at is not None:
        updates["resolved_at"] = resolved_at
    Signal.objects.filter(pk=signal.pk).update(**updates)
    signal.refresh_from_db()
    return signal


def test_kpi_population_coverage_and_technical_breakdown_share_denominator():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Water leak")
    other_pattern = create_pattern(owner, label="Lighting")
    succeeded = create_signal(owner, title="Succeeded")
    temporary_failed_with_pattern = create_signal(owner, title="Temporary failed")
    processing_with_pattern = create_signal(owner, title="Processing")
    create_signal(owner, title="Missing")
    not_started = create_signal(owner, title="Not started")
    canceled = create_signal(owner, status=Signal.Status.CANCELED, title="Canceled")
    merged = create_signal(owner, title="Merged", merged_into=succeeded)

    assign_signal(succeeded, pattern)
    assign_signal(
        temporary_failed_with_pattern,
        pattern,
        status=SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED,
    )
    assign_signal(
        processing_with_pattern,
        other_pattern,
        status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
    )
    assign_signal(
        not_started,
        None,
        status=SignalPatternAssignment.ClassificationStatus.NOT_STARTED,
    )
    assign_signal(canceled, pattern)
    assign_signal(merged, pattern)

    result = get_analytics_kpis(owner.user)
    breakdown = result.technical_classification_state.technical_state_breakdown

    assert result.analytics_signal_population_count == 5
    assert result.signals_analyzed_count == 3
    assert result.business_assignment_coverage.total_count == 5
    assert result.business_assignment_coverage.with_pattern_count == 3
    assert result.business_assignment_coverage.without_pattern_count == 2
    assert result.business_assignment_coverage.coverage_rate == 3 / 5
    assert sum(breakdown.values()) == result.analytics_signal_population_count
    assert breakdown["missing_assignment"] == 1
    assert breakdown[SignalPatternAssignment.ClassificationStatus.NOT_STARTED] == 1
    assert breakdown[SignalPatternAssignment.ClassificationStatus.PROCESSING] == 1
    assert breakdown[SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED] == 1
    assert breakdown[SignalPatternAssignment.ClassificationStatus.SUCCEEDED] == 1
    assert result.technical_classification_state.technical_terminal_success_count == 1
    assert result.technical_classification_state.technical_pending_or_error_count == 4
    assert result.operational_patterns_count == 2


def test_business_coverage_is_separate_from_technical_success():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner)
    processing = create_signal(owner, title="Processing with last success")
    failed = create_signal(owner, title="Failed with last success")

    assign_signal(
        processing,
        pattern,
        status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
    )
    assign_signal(
        failed,
        pattern,
        status=SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED,
        source=SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION,
    )

    result = get_analytics_kpis(owner.user)

    assert result.analytics_signal_population_count == 2
    assert result.signals_analyzed_count == 2
    assert result.business_assignment_coverage.with_pattern_count == 2
    assert result.technical_classification_state.technical_terminal_success_count == 0
    assert result.technical_classification_state.technical_pending_or_error_count == 2


def test_actionable_counts_open_and_in_progress_but_not_interesting():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    create_signal(owner, status=Signal.Status.OPEN, title="Open")
    create_signal(owner, status=Signal.Status.IN_PROGRESS, title="In progress")
    create_signal(owner, status=Signal.Status.INTERESTING, title="Interesting")

    result = get_analytics_kpis(owner.user)

    assert result.analytics_signal_population_count == 3
    assert result.actionable_signals_count == 2


def test_patterns_are_counted_only_through_readable_default_population():
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
    shared_pattern = create_pattern(owner, label="Shared")
    hidden_only_pattern = create_pattern(owner, label="Hidden only")
    visible = create_signal(owner, title="Visible")
    hidden_same_pattern = create_signal(hidden_membership, title="Hidden same pattern")
    hidden_other_pattern = create_signal(hidden_membership, title="Hidden other pattern")

    assign_signal(visible, shared_pattern)
    assign_signal(hidden_same_pattern, shared_pattern)
    assign_signal(hidden_other_pattern, hidden_only_pattern)

    result = get_analytics_kpis(owner.user)

    assert result.analytics_signal_population_count == 1
    assert result.signals_analyzed_count == 1
    assert result.operational_patterns_count == 1


def test_manager_scope_preserves_business_unit_and_unassigned_visibility():
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
    create_signal(
        manager,
        title="In scope",
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    create_signal(
        manager,
        title="Out scope",
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    create_signal(
        manager,
        title="Unassigned",
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
    )

    result = get_analytics_kpis(manager.user)

    assert result.analytics_signal_population_count == 2
    assert result.actionable_signals_count == 2


def test_resolution_median_counts_only_valid_durations_and_reports_invalids():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    one_hour = create_signal(owner, status=Signal.Status.RESOLVED, title="One hour")
    three_hours = create_signal(owner, status=Signal.Status.ARCHIVED, title="Three hours")
    invalid = create_signal(owner, status=Signal.Status.RESOLVED, title="Invalid")
    unresolved = create_signal(owner, status=Signal.Status.RESOLVED, title="Unresolved")

    set_signal_times(
        one_hour,
        created_at=now - timedelta(hours=2),
        resolved_at=now - timedelta(hours=1),
    )
    set_signal_times(
        three_hours,
        created_at=now - timedelta(hours=4),
        resolved_at=now - timedelta(hours=1),
    )
    set_signal_times(
        invalid,
        created_at=now,
        resolved_at=now - timedelta(minutes=1),
    )

    result = get_analytics_kpis(owner.user)

    assert result.resolution_time_signal_count == 2
    assert result.invalid_resolution_duration_count == 1
    assert result.median_resolution_seconds == 7200
    assert unresolved.resolved_at is None


def test_resolution_median_with_odd_valid_duration_count_returns_middle_value():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()
    one_hour = create_signal(owner, status=Signal.Status.RESOLVED, title="One hour")
    three_hours = create_signal(owner, status=Signal.Status.RESOLVED, title="Three hours")
    five_hours = create_signal(owner, status=Signal.Status.RESOLVED, title="Five hours")

    set_signal_times(
        one_hour,
        created_at=now - timedelta(hours=2),
        resolved_at=now - timedelta(hours=1),
    )
    set_signal_times(
        three_hours,
        created_at=now - timedelta(hours=4),
        resolved_at=now - timedelta(hours=1),
    )
    set_signal_times(
        five_hours,
        created_at=now - timedelta(hours=6),
        resolved_at=now - timedelta(hours=1),
    )

    result = get_analytics_kpis(owner.user)

    assert result.resolution_time_signal_count == 3
    assert result.invalid_resolution_duration_count == 0
    assert result.median_resolution_seconds == 10800


def test_resolution_median_is_none_without_valid_duration():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal(owner, status=Signal.Status.RESOLVED, title="Invalid")
    now = timezone.now()
    set_signal_times(signal, created_at=now, resolved_at=now - timedelta(minutes=1))

    result = get_analytics_kpis(owner.user)

    assert result.resolution_time_signal_count == 0
    assert result.invalid_resolution_duration_count == 1
    assert result.median_resolution_seconds is None


def test_period_filters_volumes_by_created_at_and_resolution_by_resolved_at():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    start = timezone.now()
    end = start + timedelta(days=1)
    before = start - timedelta(hours=1)
    inside = start + timedelta(hours=1)
    boundary = end

    create_signal(owner, title="Created before", created_at=before)
    create_signal(owner, title="Created inside", created_at=inside)
    create_signal(owner, title="Created boundary", created_at=boundary)
    resolved_created_before = create_signal(
        owner,
        status=Signal.Status.RESOLVED,
        title="Resolved inside",
    )
    resolved_after = create_signal(
        owner,
        status=Signal.Status.RESOLVED,
        title="Resolved after",
    )
    set_signal_times(
        resolved_created_before,
        created_at=before,
        resolved_at=inside,
    )
    set_signal_times(
        resolved_after,
        created_at=inside,
        resolved_at=end + timedelta(seconds=1),
    )

    result = get_analytics_kpis(owner.user, period_start=start, period_end=end)

    assert result.analytics_signal_population_count == 2
    assert result.actionable_signals_count == 1
    assert result.resolution_time_signal_count == 1
    assert result.median_resolution_seconds == 7200


@pytest.mark.parametrize(
    ("period_kwargs", "expected_count"),
    [
        ({"period_start": "start"}, 4),
        ({"period_end": "end"}, 3),
    ],
)
def test_single_period_bound_filters_created_and_resolved_timestamps(
    period_kwargs,
    expected_count,
):
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    start = timezone.now()
    end = start + timedelta(days=1)
    moments = (
        start - timedelta(hours=1),
        start,
        start + timedelta(hours=1),
        end,
        end + timedelta(hours=1),
    )
    for index, moment in enumerate(moments):
        signal = create_signal(
            owner,
            status=Signal.Status.RESOLVED,
            title=f"Period signal {index}",
        )
        set_signal_times(
            signal,
            created_at=moment,
            resolved_at=moment,
        )

    resolved_kwargs = {
        key: start if value == "start" else end
        for key, value in period_kwargs.items()
    }
    result = get_analytics_kpis(owner.user, **resolved_kwargs)

    assert result.analytics_signal_population_count == expected_count
    assert result.resolution_time_signal_count == expected_count


def test_period_validation_rejects_naive_and_empty_intervals():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    now = timezone.now()

    with pytest.raises(AnalyticsValidationError) as naive_exc:
        get_analytics_kpis(owner.user, period_start=datetime(2026, 1, 1))
    assert naive_exc.value.code == "analytics_period_start_naive"

    with pytest.raises(AnalyticsValidationError) as invalid_exc:
        get_analytics_kpis(owner.user, period_start=now, period_end=now)
    assert invalid_exc.value.code == "analytics_period_invalid"


def test_recurring_patterns_kpi_is_explicitly_not_computed_until_ticket_16():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)

    result = get_analytics_kpis(owner.user)

    assert result.recurring_patterns_count is None
    assert result.recurrence_status == RECURRENCE_STATUS_NOT_COMPUTED
