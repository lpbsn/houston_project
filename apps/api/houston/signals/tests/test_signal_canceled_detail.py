from __future__ import annotations

import pytest

from houston.actions.tests.conftest import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_restaurant_v3_taxonomy,
    login,
    signal_detail_url,
    signal_feed_url,
)
from houston.testing.auth import build_api_membership as build_other_establishment_membership
from houston.testing.taxonomy import create_signal_v3_for_membership

pytestmark = pytest.mark.django_db


def _canceled_signal_for_membership(
    membership: EstablishmentMembership,
    *,
    affected_key: str | None = None,
    responsible_key: str | None = None,
) -> Signal:
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    affected = taxonomy.restaurant
    responsible = taxonomy.maintenance
    if affected_key == "bar":
        affected = taxonomy.bar
    if responsible_key == "bar":
        responsible = taxonomy.bar
    return create_signal_v3_for_membership(
        membership,
        affected_business_unit=affected,
        responsible_business_unit=responsible,
        activity_subject=taxonomy.lighting_subject,
        status=Signal.Status.CANCELED,
        title="Sensitive canceled signal title",
    )


def test_detail_canceled_staff_scoped_on_responsible_returns_200(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    signal = _canceled_signal_for_membership(owner)
    token = login(api_client, user=staff.user)

    response = api_client.get(
        signal_detail_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == Signal.Status.CANCELED


def test_detail_canceled_staff_scoped_on_affected_only_returns_200(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assign_business_unit_scope(staff, taxonomy.restaurant)
    signal = _canceled_signal_for_membership(owner)
    token = login(api_client, user=staff.user)

    response = api_client.get(
        signal_detail_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == Signal.Status.CANCELED


def test_detail_canceled_staff_scoped_on_both_poles_returns_200(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(staff, taxonomy.maintenance)
    assign_business_unit_scope(staff, taxonomy.restaurant)
    signal = _canceled_signal_for_membership(owner)
    token = login(api_client, user=staff.user)

    response = api_client.get(
        signal_detail_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200


def test_detail_canceled_staff_out_of_scope_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assign_business_unit_scope(staff, taxonomy.bar)
    signal = _canceled_signal_for_membership(owner)
    token = login(api_client, user=staff.user)

    response = api_client.get(
        signal_detail_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_detail_canceled_owner_without_pole_scope_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _canceled_signal_for_membership(owner)
    token = login(api_client, user=owner.user)

    response = api_client.get(
        signal_detail_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_detail_canceled_director_without_pole_scope_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    signal = _canceled_signal_for_membership(owner)
    token = login(api_client, user=director.user)

    response = api_client.get(
        signal_detail_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_detail_canceled_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_other_establishment_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _canceled_signal_for_membership(owner)
    token = login(api_client, user=outsider.user)

    response = api_client.get(
        signal_detail_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code in {403, 404}


def test_detail_canceled_permission_hints_all_false(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(manager, taxonomy.maintenance)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        status=Signal.Status.CANCELED,
        title="Canceled pinned urgent",
    )
    signal.is_pinned = True
    signal.urgency = Signal.Urgency.HIGH
    signal.save(update_fields=["is_pinned", "urgency", "updated_at"])
    token = login(api_client, user=manager.user)

    response = api_client.get(
        signal_detail_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    hints = response.json()["permission_hints"]
    assert hints["can_pin"] is False
    assert hints["can_set_urgency"] is False
    assert hints["can_cancel"] is False
    assert hints["can_resolve"] is False
    assert hints["can_create_action"] is False


def test_feed_still_excludes_canceled_after_detail_access(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None
    assign_business_unit_scope(manager, taxonomy.maintenance)
    signal = _canceled_signal_for_membership(owner)
    token = login(api_client, user=manager.user)

    detail = api_client.get(
        signal_detail_url(owner.establishment_id, signal.id),
        **auth_headers(token),
    )
    feed = api_client.get(
        signal_feed_url(owner.establishment_id) + "?view_mode=personal",
        **auth_headers(token),
    )

    assert detail.status_code == 200
    assert feed.status_code == 200
    assert feed.json()["items"] == []
