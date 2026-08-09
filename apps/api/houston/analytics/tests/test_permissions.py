from __future__ import annotations

import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.permissions import (
    analytics_accessible_establishment_ids_for_user,
    analytics_signal_scope_q_for_membership,
    can_govern_operational_patterns,
    can_read_analytics,
)
from houston.analytics.selectors import (
    analytics_readable_assignments_queryset,
    analytics_readable_patterns_queryset,
    analytics_readable_signals_queryset,
)
from houston.analytics.services import create_operational_pattern
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization
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
    affected_business_unit=None,
    responsible_business_unit=None,
    routing_status=Signal.RoutingStatus.RESOLVED,
    status=Signal.Status.OPEN,
    issue_focus=None,
):
    return Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        routing_status=routing_status,
        status=status,
        title=title,
        structured_summary="Structured signal summary.",
        issue_focus=issue_focus or title.lower().replace(" ", "-"),
        last_activity_at=timezone.now(),
    )


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


def test_staff_cannot_read_or_govern_even_with_business_unit_scope():
    staff = build_membership(role=EstablishmentMembership.Role.STAFF)
    business_unit = create_business_unit(establishment=staff.establishment, key="bar")
    create_membership_with_business_unit_scope(
        membership=staff,
        business_unit=business_unit,
    )
    signal = create_signal(
        staff,
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
    )
    pattern = create_pattern(staff)

    assert not can_read_analytics(staff)
    assert not can_govern_operational_patterns(
        staff,
        organization=staff.establishment.organization,
    )
    assert not Signal.objects.filter(
        analytics_signal_scope_q_for_membership(staff),
        id=signal.id,
    ).exists()
    assert not analytics_readable_signals_queryset(staff.user).exists()
    assert not analytics_readable_patterns_queryset(staff.user).filter(id=pattern.id).exists()


def test_empty_scope_is_not_neutral_when_combined_with_allowed_membership():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_membership(role=EstablishmentMembership.Role.STAFF)
    accessible = create_signal(owner, title="Accessible")
    outsider_membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    hidden = create_signal(outsider_membership, title="Hidden")

    combined_scope = (
        analytics_signal_scope_q_for_membership(staff)
        | analytics_signal_scope_q_for_membership(owner)
    )

    assert list(
        Signal.objects.filter(combined_scope).order_by("title").values_list(
            "title",
            flat=True,
        )
    ) == [accessible.title]
    assert hidden.title not in set(
        Signal.objects.filter(combined_scope).values_list("title", flat=True)
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"membership_status": EstablishmentMembership.Status.DEACTIVATED},
        {"user_status": User.Status.SUSPENDED},
        {"establishment_status": Establishment.Status.DEACTIVATED},
        {"organization_status": Organization.Status.SUSPENDED},
    ],
)
def test_invalid_actor_produces_empty_scope_without_prechecking_can_read(kwargs):
    membership = build_membership(
        role=EstablishmentMembership.Role.MANAGER,
        **kwargs,
    )
    signal = create_signal(membership)

    assert not can_read_analytics(membership)
    assert not Signal.objects.filter(
        analytics_signal_scope_q_for_membership(membership),
        id=signal.id,
    ).exists()


def test_owner_and_director_read_only_their_active_establishments():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_membership(role=EstablishmentMembership.Role.DIRECTOR)
    owner_signal = create_signal(owner, title="Owner signal")
    director_signal = create_signal(director, title="Director signal")

    assert list(analytics_readable_signals_queryset(owner.user)) == [owner_signal]
    assert list(analytics_readable_signals_queryset(director.user)) == [director_signal]


def test_manager_scope_uses_business_units_and_unassigned_visibility():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    in_scope_bu = create_business_unit(establishment=manager.establishment, key="bar")
    out_scope_bu = create_business_unit(establishment=manager.establishment, key="kitchen")
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=in_scope_bu,
    )
    in_scope = create_signal(
        manager,
        title="In scope",
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    out_of_scope = create_signal(
        manager,
        title="Out of scope",
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    unassigned = create_signal(
        manager,
        title="Unassigned",
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
    )

    readable_titles = set(
        analytics_readable_signals_queryset(manager.user).values_list("title", flat=True)
    )

    assert readable_titles == {in_scope.title, unassigned.title}
    assert out_of_scope.title not in readable_titles


def test_manager_without_scope_reads_unassigned_but_not_resolved_business_unit_signal():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    business_unit = create_business_unit(establishment=manager.establishment, key="bar")
    resolved = create_signal(
        manager,
        title="Resolved",
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
    )
    unassigned = create_signal(
        manager,
        title="Unassigned",
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
    )

    readable_titles = set(
        analytics_readable_signals_queryset(manager.user).values_list("title", flat=True)
    )

    assert readable_titles == {unassigned.title}
    assert resolved.title not in readable_titles


def test_multi_memberships_union_keeps_manager_business_unit_constraints():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    second_establishment = Establishment.objects.create(
        name="Second establishment",
        organization=manager.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    director = create_membership(
        establishment=second_establishment,
        user=manager.user,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    in_scope_bu = create_business_unit(establishment=manager.establishment, key="bar")
    out_scope_bu = create_business_unit(establishment=manager.establishment, key="kitchen")
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=in_scope_bu,
    )
    manager_signal = create_signal(
        manager,
        title="Manager scoped",
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    hidden_manager_signal = create_signal(
        manager,
        title="Manager hidden",
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    director_signal = create_signal(director, title="Director scoped")

    readable_titles = set(
        analytics_readable_signals_queryset(manager.user).values_list("title", flat=True)
    )

    assert readable_titles == {manager_signal.title, director_signal.title}
    assert hidden_manager_signal.title not in readable_titles


def test_active_owner_can_govern_patterns_and_director_manager_cannot():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    director = create_membership(
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    manager = create_membership(
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )

    assert can_govern_operational_patterns(
        owner,
        organization=owner.establishment.organization,
    )
    assert not can_govern_operational_patterns(
        director,
        organization=owner.establishment.organization,
    )
    assert not can_govern_operational_patterns(
        manager,
        organization=owner.establishment.organization,
    )


def test_pattern_visibility_depends_on_readable_assignments_only():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    second_establishment = Establishment.objects.create(
        name="Second establishment",
        organization=owner.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    other_establishment_owner = create_membership(
        establishment=second_establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    pattern = create_pattern(owner, label="Shared pattern")
    accessible_signal = create_signal(owner, title="Accessible")
    hidden_signal = create_signal(other_establishment_owner, title="Hidden")
    accessible_assignment = assign_signal(accessible_signal, pattern)
    assign_signal(hidden_signal, pattern)

    readable_patterns = list(analytics_readable_patterns_queryset(owner.user))
    readable_assignments = list(analytics_readable_assignments_queryset(owner.user))

    assert readable_patterns == [pattern]
    assert readable_assignments == [accessible_assignment]


def test_pattern_queryset_deduplicates_patterns_with_multiple_readable_assignments():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Shared pattern")
    first_signal = create_signal(owner, title="First")
    second_signal = create_signal(owner, title="Second")
    assign_signal(first_signal, pattern)
    assign_signal(second_signal, pattern)

    assert list(analytics_readable_patterns_queryset(owner.user)) == [pattern]


def test_pattern_without_readable_assignment_is_hidden():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Hidden pattern")

    assert not analytics_readable_patterns_queryset(owner.user).filter(id=pattern.id).exists()


def test_accessible_establishment_ids_are_active_secondary_helper_only():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    staff_establishment = Establishment.objects.create(
        name="Staff establishment",
        organization=owner.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    create_membership(
        establishment=staff_establishment,
        user=owner.user,
        role=EstablishmentMembership.Role.STAFF,
    )
    inactive_establishment = Establishment.objects.create(
        name="Inactive establishment",
        organization=owner.establishment.organization,
        status=Establishment.Status.DEACTIVATED,
        timezone="UTC",
    )
    create_membership(
        establishment=inactive_establishment,
        user=owner.user,
        role=EstablishmentMembership.Role.OWNER,
    )

    assert analytics_accessible_establishment_ids_for_user(owner.user) == [
        owner.establishment_id
    ]
