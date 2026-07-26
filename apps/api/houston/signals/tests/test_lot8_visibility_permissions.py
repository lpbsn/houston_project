"""Lot 8 H5/H6 — visibility, qualify, lifecycle, needs_qualification filter.

Product-validated matrix: Managers triage all unassigned establishment-wide;
Staff never sees total unclassified; author grants no Signal rights;
pin/cancel/resolve never mutate routing_status.
"""

from __future__ import annotations

import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.action_plans.permissions import can_create_linked_action_plan
from houston.establishments.models import EstablishmentMembership
from houston.signals.feed_filters import SignalFeedFilters, apply_feed_filters
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.permissions import (
    can_cancel_signal,
    can_pin_signal,
    can_qualify_routing,
    can_resolve_signal,
    can_view_signal_detail,
    is_total_unclassified,
)
from houston.signals.selectors import get_signal_for_detail, signal_feed_queryset
from houston.signals.services import (
    cancel_signal,
    pin_signal,
    record_source_observation_link,
    resolve_signal,
)
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_observation,
    create_restaurant_v3_taxonomy,
    create_v3_signal,
    login,
    signal_detail_url,
    signal_feed_url,
)
from houston.testing.auth import (
    TEST_PASSWORD,
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
from houston.testing.taxonomy import create_membership_with_business_unit_scope

pytestmark = pytest.mark.django_db


def _total_unclassified(membership, *, title: str = "Total unclassified") -> Signal:
    return Signal.objects.create(
        establishment=membership.establishment,
        title=title,
        structured_summary="Needs triage.",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        issue_focus="",
        last_activity_at=timezone.now(),
    )


def _partial_affected(membership, *, affected) -> Signal:
    return Signal.objects.create(
        establishment=membership.establishment,
        title="Partial affected",
        structured_summary="Partial routing.",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        affected_business_unit=affected,
        responsible_business_unit=None,
        activity_subject=None,
        issue_focus="",
        last_activity_at=timezone.now(),
    )


def _partial_responsible(membership, *, responsible) -> Signal:
    return Signal.objects.create(
        establishment=membership.establishment,
        title="Partial responsible",
        structured_summary="Partial routing.",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        affected_business_unit=None,
        responsible_business_unit=responsible,
        activity_subject=None,
        issue_focus="",
        last_activity_at=timezone.now(),
    )


def _resolved_signal(membership, taxonomy) -> Signal:
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    return create_v3_signal(
        membership.establishment,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title="Resolved routing",
    )


def _feed_ids(api_client, membership, *, view_mode: str) -> set[str]:
    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_feed_url(membership.establishment_id) + f"?view_mode={view_mode}",
        **auth_headers(token),
    )
    assert response.status_code == 200
    return {item["id"] for item in response.json()["items"]}


def _detail_status(api_client, membership, signal_id) -> int:
    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal_id),
        **auth_headers(token),
    )
    return response.status_code


def test_is_total_unclassified_helper():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _total_unclassified(owner)
    assert is_total_unclassified(signal) is True
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    partial = _partial_affected(owner, affected=taxonomy.restaurant)
    assert is_total_unclassified(partial) is False


@pytest.mark.parametrize("role", [
    EstablishmentMembership.Role.OWNER,
    EstablishmentMembership.Role.DIRECTOR,
    EstablishmentMembership.Role.MANAGER,
])
def test_triage_roles_see_total_unclassified_everywhere(api_client, role):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    membership = (
        owner
        if role == EstablishmentMembership.Role.OWNER
        else build_api_membership_on_establishment(owner, role=role)
    )
    if role == EstablishmentMembership.Role.MANAGER:
        taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
        create_membership_with_business_unit_scope(
            membership=membership,
            business_unit=taxonomy.bar,
        )
    signal = _total_unclassified(owner)

    assert can_view_signal_detail(membership, signal) is True
    assert get_signal_for_detail(membership=membership, signal_id=signal.id) is not None
    assert str(signal.id) in _feed_ids(api_client, membership, view_mode="personal")
    assert str(signal.id) in _feed_ids(api_client, membership, view_mode="general")
    assert _detail_status(api_client, membership, signal.id) == 200


def test_staff_does_not_see_total_unclassified(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assign_business_unit_scope(staff, taxonomy.restaurant)
    signal = _total_unclassified(owner)

    assert can_view_signal_detail(staff, signal) is False
    assert get_signal_for_detail(membership=staff, signal_id=signal.id) is None
    assert str(signal.id) not in _feed_ids(api_client, staff, view_mode="personal")
    assert str(signal.id) not in _feed_ids(api_client, staff, view_mode="general")
    assert _detail_status(api_client, staff, signal.id) == 404


def test_staff_sees_partial_when_pole_in_scope(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assign_business_unit_scope(staff, taxonomy.restaurant)
    in_scope = _partial_affected(owner, affected=taxonomy.restaurant)
    out_of_scope = _partial_responsible(owner, responsible=taxonomy.bar)

    assert can_view_signal_detail(staff, in_scope) is True
    assert str(in_scope.id) in _feed_ids(api_client, staff, view_mode="personal")
    assert str(out_of_scope.id) not in _feed_ids(api_client, staff, view_mode="personal")
    # General feed: Staff sees partial with identifiable pole establishment-wide.
    assert str(out_of_scope.id) in _feed_ids(api_client, staff, view_mode="general")


def test_manager_sees_all_unassigned_in_personal_feed(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=taxonomy.bar,
    )
    total = _total_unclassified(owner)
    partial = _partial_affected(owner, affected=taxonomy.restaurant)
    resolved = _resolved_signal(owner, taxonomy)

    personal_ids = _feed_ids(api_client, manager, view_mode="personal")
    assert str(total.id) in personal_ids
    assert str(partial.id) in personal_ids
    # Resolved outside Ma vue scope stays out of personal feed.
    assert str(resolved.id) not in personal_ids


@pytest.mark.parametrize("role", [
    EstablishmentMembership.Role.OWNER,
    EstablishmentMembership.Role.DIRECTOR,
    EstablishmentMembership.Role.MANAGER,
])
def test_triage_can_qualify_total_unclassified(role):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    membership = (
        owner
        if role == EstablishmentMembership.Role.OWNER
        else build_api_membership_on_establishment(owner, role=role)
    )
    signal = _total_unclassified(owner)
    assert can_qualify_routing(membership, signal) is True


def test_staff_cannot_qualify_unassigned():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    signal = _total_unclassified(owner)
    assert can_qualify_routing(staff, signal) is False


@pytest.mark.parametrize("role", [
    EstablishmentMembership.Role.OWNER,
    EstablishmentMembership.Role.DIRECTOR,
    EstablishmentMembership.Role.MANAGER,
])
def test_triage_lifecycle_on_total_unassigned_does_not_alter_routing_status(role):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    membership = (
        owner
        if role == EstablishmentMembership.Role.OWNER
        else build_api_membership_on_establishment(owner, role=role)
    )
    signal = _total_unclassified(owner)
    assert can_pin_signal(membership, signal) is True
    assert can_cancel_signal(membership, signal) is True
    assert can_resolve_signal(membership, signal) is True

    pin_signal(signal=signal, membership=membership)
    signal.refresh_from_db()
    assert signal.is_pinned is True
    assert signal.routing_status == Signal.RoutingStatus.UNASSIGNED

    resolve_signal(signal=signal, actor_membership=membership)
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
    assert signal.routing_status == Signal.RoutingStatus.UNASSIGNED


def test_manager_lifecycle_on_partial_without_responsible():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    signal = _partial_affected(owner, affected=taxonomy.restaurant)
    assert can_cancel_signal(manager, signal) is True
    cancel_signal(signal=signal, actor_membership=manager)
    signal.refresh_from_db()
    assert signal.status == Signal.Status.CANCELED
    assert signal.routing_status == Signal.RoutingStatus.UNASSIGNED


def test_staff_lifecycle_forbidden_on_unassigned():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    signal = _total_unclassified(owner)
    assert can_pin_signal(staff, signal) is False
    assert can_cancel_signal(staff, signal) is False
    assert can_resolve_signal(staff, signal) is False


def test_needs_qualification_filter_for_manager(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    unassigned = _total_unclassified(owner)
    resolved_routing = _resolved_signal(owner, taxonomy)
    token = login(api_client, user=manager.user)

    response = api_client.get(
        signal_feed_url(manager.establishment_id)
        + "?view_mode=general&needs_qualification=true",
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    ids = {item["id"] for item in body["items"]}
    assert str(unassigned.id) in ids
    assert str(resolved_routing.id) not in ids
    assert body["applied_filters"]["needs_qualification"] is True


def test_needs_qualification_excludes_resolved_canceled_and_archived(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    active = _total_unclassified(owner, title="Active unassigned")
    lifecycle_resolved = _total_unclassified(owner, title="Resolved unassigned")
    resolve_signal(signal=lifecycle_resolved, actor_membership=owner)
    lifecycle_canceled = _total_unclassified(owner, title="Canceled unassigned")
    cancel_signal(signal=lifecycle_canceled, actor_membership=owner)
    archived = _total_unclassified(owner, title="Archived unassigned")
    archived.status = Signal.Status.ARCHIVED
    archived.save(update_fields=["status", "updated_at"])

    token = login(api_client, user=manager.user)
    response = api_client.get(
        signal_feed_url(manager.establishment_id)
        + "?view_mode=general&needs_qualification=true",
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert str(active.id) in ids
    assert str(lifecycle_resolved.id) not in ids
    assert str(lifecycle_canceled.id) not in ids
    assert str(archived.id) not in ids

    # Feed base queryset already omits archived; filter itself must still exclude it.
    filtered_ids = set(
        apply_feed_filters(
            Signal.objects.filter(establishment_id=owner.establishment_id),
            filters=SignalFeedFilters(needs_qualification=True),
        ).values_list("id", flat=True)
    )
    assert active.id in filtered_ids
    assert lifecycle_resolved.id not in filtered_ids
    assert lifecycle_canceled.id not in filtered_ids
    assert archived.id not in filtered_ids


def test_needs_qualification_filter_forbidden_for_staff(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=staff.user)

    response = api_client.get(
        signal_feed_url(staff.establishment_id)
        + "?view_mode=general&needs_qualification=true",
        **auth_headers(token),
    )
    assert response.status_code == 403


def test_author_staff_does_not_gain_visibility_on_total_unclassified(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assign_business_unit_scope(staff, taxonomy.bar)
    signal = _total_unclassified(owner)
    observation = create_observation(membership=staff)
    record_source_observation_link(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    assert can_view_signal_detail(staff, signal) is False
    assert can_qualify_routing(staff, signal) is False
    assert str(signal.id) not in _feed_ids(api_client, staff, view_mode="general")


def test_cross_establishment_isolation_detail_and_feed(api_client):
    owner_a = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    owner_b = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal_a = _total_unclassified(owner_a)
    manager_b = build_api_membership_on_establishment(
        owner_b,
        role=EstablishmentMembership.Role.MANAGER,
    )

    assert get_signal_for_detail(membership=manager_b, signal_id=signal_a.id) is None
    assert str(signal_a.id) not in _feed_ids(api_client, manager_b, view_mode="general")
    assert _detail_status(api_client, manager_b, signal_a.id) == 404
    assert can_qualify_routing(manager_b, signal_a) is False
    assert can_pin_signal(manager_b, signal_a) is False


def test_permission_hints_on_total_unclassified_for_manager(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    signal = _total_unclassified(owner)
    assert can_qualify_routing(manager, signal) is True
    assert can_pin_signal(manager, signal) is True
    assert can_cancel_signal(manager, signal) is True
    assert can_resolve_signal(manager, signal) is True
    assert can_create_linked_action_plan(manager, signal=signal) is False

    token = login(api_client, user=manager.user)
    response = api_client.get(
        signal_detail_url(manager.establishment_id, signal.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    hints = response.json()["permission_hints"]
    assert hints["can_qualify_routing"] is True
    assert hints["can_pin"] is True
    assert hints["can_cancel"] is True
    assert hints["can_resolve"] is True
    assert hints["can_create_linked_action_plan"] is False


def test_selector_personal_manager_without_scope_sees_only_unassigned():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager_user = User.objects.create_user(
        username=f"mgr_noscope_{timezone.now().timestamp()}",
        email=f"mgr_noscope_{timezone.now().timestamp()}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    manager = EstablishmentMembership.objects.create(
        user=manager_user,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    unassigned = _total_unclassified(owner)
    resolved = _resolved_signal(owner, taxonomy)

    ids = set(
        signal_feed_queryset(membership=manager, view_mode="personal").values_list(
            "id",
            flat=True,
        )
    )
    assert unassigned.id in ids
    assert resolved.id not in ids

