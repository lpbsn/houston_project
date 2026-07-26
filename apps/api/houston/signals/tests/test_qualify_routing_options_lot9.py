from __future__ import annotations

import uuid

import pytest

from houston.accounts.models import User
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_membership_with_business_unit_scope,
)
from houston.signals.tests.conftest import auth_headers, build_api_membership, login
from houston.testing.factories import TEST_PASSWORD, create_establishment
from houston.testing.taxonomy import create_business_unit, create_restaurant_v3_taxonomy

pytestmark = pytest.mark.django_db


def _options_url(establishment_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/signals/qualify-routing-options/"
    )


def test_owner_sees_establishment_wide_active_tree_including_spa_without_subjects(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    spa = create_business_unit(
        establishment=membership.establishment,
        key="spa",
        label="Spa",
    )
    inactive = create_business_unit(
        establishment=membership.establishment,
        key="closed_wing",
        label="Closed Wing",
    )
    inactive.active = False
    inactive.save(update_fields=["active", "updated_at"])
    token = login(api_client, user=membership.user)

    response = api_client.get(
        _options_url(membership.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["establishment_id"] == str(membership.establishment_id)
    units = {item["id"]: item for item in body["business_units"]}
    assert str(spa.id) in units
    assert units[str(spa.id)]["activity_subjects"] == []
    assert str(taxonomy.restaurant.id) in units
    assert str(taxonomy.bar.id) in units
    assert str(taxonomy.maintenance.id) in units
    assert units[str(taxonomy.maintenance.id)]["activity_subjects"]
    assert str(inactive.id) not in units
    for item in body["business_units"]:
        assert item["active"] is True
        assert "routing_key" not in item
        for subject in item["activity_subjects"]:
            assert subject["active"] is True
            assert "routing_key" not in subject


def test_manager_sees_units_outside_membership_scope(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    spa = create_business_unit(
        establishment=owner.establishment,
        key="spa",
        label="Spa",
    )
    manager_user = User.objects.create_user(
        username=f"mgr_opts_{uuid.uuid4().hex[:6]}",
        email=f"mgr_opts_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    manager = EstablishmentMembership.objects.create(
        user=manager_user,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=taxonomy.restaurant,
    )
    token = login(api_client, user=manager.user)

    response = api_client.get(
        _options_url(manager.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["business_units"]}
    assert str(taxonomy.restaurant.id) in ids
    assert str(taxonomy.bar.id) in ids
    assert str(spa.id) in ids
    assert str(taxonomy.maintenance.id) in ids


def test_staff_receives_permission_denied(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    create_restaurant_v3_taxonomy(membership.establishment)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        _options_url(membership.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "permission_denied"
    assert body["detail"] == "Permission denied."
    assert "business_units" not in body


def test_unauthenticated_returns_401(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)

    response = api_client.get(_options_url(membership.establishment_id))

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_no_active_membership_returns_403(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    membership.status = EstablishmentMembership.Status.DEACTIVATED
    membership.save(update_fields=["status", "updated_at"])
    token = login(api_client, user=membership.user)

    response = api_client.get(
        _options_url(membership.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "permission_denied"
    assert "active establishment membership" in body["detail"].lower()


def test_active_only_on_other_establishment_returns_403(api_client):
    home = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = create_establishment(name="Foreign Qualify Options Est")
    token = login(api_client, user=home.user)

    response = api_client.get(
        _options_url(foreign.id),
        **auth_headers(token),
    )

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "permission_denied"
    assert "signal feed" in body["detail"].lower()


def test_unknown_establishment_id_returns_403(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        _options_url(uuid.uuid4()),
        **auth_headers(token),
    )

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "permission_denied"
    assert "signal feed" in body["detail"].lower()


def test_inactive_on_path_with_active_elsewhere_returns_403(api_client):
    active = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    inactive_est = create_establishment(name="Inactive Path Qualify Options")
    inactive_membership = EstablishmentMembership.objects.create(
        user=active.user,
        establishment=inactive_est,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.DEACTIVATED,
    )
    token = login(api_client, user=active.user)
    # Session stays on active establishment; request inactive path.
    assert inactive_membership.status == EstablishmentMembership.Status.DEACTIVATED

    response = api_client.get(
        _options_url(inactive_est.id),
        **auth_headers(token),
    )

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "permission_denied"
    assert "signal feed" in body["detail"].lower()


def test_director_receives_200(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    create_restaurant_v3_taxonomy(membership.establishment)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        _options_url(membership.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["business_units"]


def test_options_do_not_leak_other_establishment_units(api_client):
    home = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    create_restaurant_v3_taxonomy(home.establishment)
    foreign = create_establishment(name="Other Est Units")
    foreign_unit = create_business_unit(
        establishment=foreign,
        key="restaurant",
        label="Foreign Restaurant",
    )
    token = login(api_client, user=home.user)

    response = api_client.get(
        _options_url(home.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["business_units"]}
    assert str(foreign_unit.id) not in ids
