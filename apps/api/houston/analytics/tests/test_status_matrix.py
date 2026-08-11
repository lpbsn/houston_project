from __future__ import annotations

import uuid

import pytest
from django.utils import timezone

from houston.analytics.selectors import (
    analytics_actionable_signals_queryset,
    analytics_default_signals_queryset,
    analytics_recurrence_signals_queryset,
    analytics_resolution_time_signals_queryset,
)
from houston.analytics.status_matrix import (
    actionable_signal_q,
    default_analytics_signal_q,
    recurrence_signal_q,
    resolution_time_signal_q,
    signal_has_analytics_status_anomaly,
    signal_participates_in_actionable_queue,
    signal_participates_in_default_analytics,
    signal_participates_in_recurrence,
    signal_participates_in_resolution_time,
    status_anomaly_q,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.factories import build_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def create_signal(
    membership,
    *,
    status=Signal.Status.OPEN,
    routing_status=Signal.RoutingStatus.RESOLVED,
    title="Signal",
    resolved_at=None,
    merged_into=None,
    affected_business_unit=None,
    responsible_business_unit=None,
):
    suffix = uuid.uuid4().hex[:8]
    return Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        status=status,
        routing_status=routing_status,
        title=f"{title} {suffix}",
        structured_summary="Structured signal summary.",
        issue_focus=f"issue-{suffix}",
        resolved_at=resolved_at,
        merged_into=merged_into,
        last_activity_at=timezone.now(),
    )


def matches(query, signal) -> bool:
    return Signal.objects.filter(query, id=signal.id).exists()


@pytest.mark.parametrize(
    "status",
    [
        Signal.Status.OPEN,
        Signal.Status.IN_PROGRESS,
        Signal.Status.INTERESTING,
        Signal.Status.RESOLVED,
        Signal.Status.ARCHIVED,
    ],
)
def test_default_population_includes_every_non_merged_non_canceled_status(status):
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal(membership, status=status)

    assert signal_participates_in_default_analytics(signal)
    assert matches(default_analytics_signal_q(), signal)


def test_default_population_excludes_canceled_and_merged_sources():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    target = create_signal(membership, title="Target")
    canceled = create_signal(membership, status=Signal.Status.CANCELED)
    merged = create_signal(
        membership,
        status=Signal.Status.ARCHIVED,
        merged_into=target,
        title="Merged",
    )

    assert not signal_participates_in_default_analytics(canceled)
    assert not signal_participates_in_default_analytics(merged)
    assert not matches(default_analytics_signal_q(), canceled)
    assert not matches(default_analytics_signal_q(), merged)
    assert signal_participates_in_default_analytics(target)


def test_recurrence_is_alias_of_default_population_and_ignores_resolved_at():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    resolved_without_timestamp = create_signal(
        membership,
        status=Signal.Status.RESOLVED,
        resolved_at=None,
        title="Resolved without timestamp",
    )
    archived_without_timestamp = create_signal(
        membership,
        status=Signal.Status.ARCHIVED,
        resolved_at=None,
        title="Archived without timestamp",
    )
    canceled = create_signal(membership, status=Signal.Status.CANCELED)

    assert recurrence_signal_q() == default_analytics_signal_q()
    assert signal_participates_in_recurrence(resolved_without_timestamp)
    assert signal_participates_in_recurrence(archived_without_timestamp)
    assert not signal_participates_in_recurrence(canceled)
    assert matches(recurrence_signal_q(), resolved_without_timestamp)
    assert matches(recurrence_signal_q(), archived_without_timestamp)
    assert not matches(recurrence_signal_q(), canceled)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (Signal.Status.OPEN, True),
        (Signal.Status.IN_PROGRESS, True),
        (Signal.Status.INTERESTING, False),
        (Signal.Status.RESOLVED, False),
        (Signal.Status.ARCHIVED, False),
        (Signal.Status.CANCELED, False),
    ],
)
def test_actionable_queue_population(status, expected):
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_signal(membership, status=status)

    assert signal_participates_in_actionable_queue(signal) is expected
    assert matches(actionable_signal_q(), signal) is expected


def test_resolution_time_requires_resolved_at_for_resolved_or_archived():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    timestamp = timezone.now()
    resolved_with_timestamp = create_signal(
        membership,
        status=Signal.Status.RESOLVED,
        resolved_at=timestamp,
        title="Resolved with timestamp",
    )
    resolved_without_timestamp = create_signal(
        membership,
        status=Signal.Status.RESOLVED,
        resolved_at=None,
        title="Resolved without timestamp",
    )
    archived_with_timestamp = create_signal(
        membership,
        status=Signal.Status.ARCHIVED,
        resolved_at=timestamp,
        title="Archived with timestamp",
    )
    archived_without_timestamp = create_signal(
        membership,
        status=Signal.Status.ARCHIVED,
        resolved_at=None,
        title="Archived without timestamp",
    )

    assert signal_participates_in_resolution_time(resolved_with_timestamp)
    assert signal_participates_in_resolution_time(archived_with_timestamp)
    assert not signal_participates_in_resolution_time(resolved_without_timestamp)
    assert not signal_participates_in_resolution_time(archived_without_timestamp)
    assert matches(resolution_time_signal_q(), resolved_with_timestamp)
    assert matches(resolution_time_signal_q(), archived_with_timestamp)
    assert not matches(resolution_time_signal_q(), resolved_without_timestamp)
    assert not matches(resolution_time_signal_q(), archived_without_timestamp)


def test_status_anomaly_only_flags_resolved_without_resolved_at():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    resolved_without_timestamp = create_signal(
        membership,
        status=Signal.Status.RESOLVED,
        resolved_at=None,
        title="Resolved without timestamp",
    )
    archived_without_timestamp = create_signal(
        membership,
        status=Signal.Status.ARCHIVED,
        resolved_at=None,
        title="Archived without timestamp",
    )

    assert signal_has_analytics_status_anomaly(resolved_without_timestamp)
    assert not signal_has_analytics_status_anomaly(archived_without_timestamp)
    assert matches(status_anomaly_q(), resolved_without_timestamp)
    assert not matches(status_anomaly_q(), archived_without_timestamp)


def test_unassigned_routing_does_not_override_status_matrix():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    open_unassigned = create_signal(
        membership,
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title="Open unassigned",
    )
    canceled_unassigned = create_signal(
        membership,
        status=Signal.Status.CANCELED,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title="Canceled unassigned",
    )

    assert signal_participates_in_default_analytics(open_unassigned)
    assert not signal_participates_in_default_analytics(canceled_unassigned)
    assert matches(default_analytics_signal_q(), open_unassigned)
    assert not matches(default_analytics_signal_q(), canceled_unassigned)


def test_status_selectors_compose_matrix_with_manager_scope():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    in_scope_bu = create_business_unit(establishment=manager.establishment, key="bar")
    out_scope_bu = create_business_unit(establishment=manager.establishment, key="kitchen")
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=in_scope_bu,
    )
    scoped_open = create_signal(
        manager,
        title="Scoped open",
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    unassigned_out_of_scope = create_signal(
        manager,
        title="Unassigned out of scope",
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
    )
    resolved_out_of_scope = create_signal(
        manager,
        title="Resolved out of scope",
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    canceled_unassigned = create_signal(
        manager,
        title="Canceled unassigned",
        status=Signal.Status.CANCELED,
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
    )

    default_ids = set(
        analytics_default_signals_queryset(manager.user).values_list("id", flat=True)
    )
    actionable_ids = set(
        analytics_actionable_signals_queryset(manager.user).values_list("id", flat=True)
    )
    recurrence_ids = set(
        analytics_recurrence_signals_queryset(manager.user).values_list("id", flat=True)
    )

    assert default_ids == {scoped_open.id, unassigned_out_of_scope.id}
    assert actionable_ids == {scoped_open.id, unassigned_out_of_scope.id}
    assert recurrence_ids == default_ids
    assert resolved_out_of_scope.id not in default_ids
    assert canceled_unassigned.id not in default_ids


def test_resolution_time_selector_composes_with_scope():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    timestamp = timezone.now()
    visible = create_signal(
        owner,
        title="Visible resolved",
        status=Signal.Status.RESOLVED,
        resolved_at=timestamp,
    )
    other = build_membership(role=EstablishmentMembership.Role.OWNER)
    hidden = create_signal(
        other,
        title="Hidden resolved",
        status=Signal.Status.RESOLVED,
        resolved_at=timestamp,
    )

    assert list(analytics_resolution_time_signals_queryset(owner.user)) == [visible]
    assert hidden.id not in set(
        analytics_resolution_time_signals_queryset(owner.user).values_list("id", flat=True)
    )
