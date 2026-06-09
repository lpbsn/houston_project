from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_membership,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return api_client.cookies["csrftoken"].value


def login(api_client: APIClient, *, membership) -> str:
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        "/api/v1/auth/login/",
        {
            "identifier": membership.user.email,
            "password": "SecurePass123!",
        },
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(access_token: str) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}


def test_user_search_with_business_unit_id_filters_to_covering_members(api_client):
    establishment = create_establishment(name="Filter Hotel")
    restaurant = create_business_unit(establishment=establishment, key="restaurant")
    bar = create_business_unit(establishment=establishment, key="bar")

    actor = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    director = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )

    scoped_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    scoped_staff.user.first_name = "Scoped"
    scoped_staff.user.username = "scoped_member"
    scoped_staff.user.save(update_fields=["first_name", "username"])
    create_membership_with_business_unit_scope(
        membership=scoped_staff,
        business_unit=restaurant,
    )

    out_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    out_staff.user.first_name = "Outside"
    out_staff.user.username = "outside_member"
    out_staff.user.save(update_fields=["first_name", "username"])
    create_membership_with_business_unit_scope(membership=out_staff, business_unit=bar)

    owner.user.first_name = "Owner"
    owner.user.username = "owner_member"
    owner.user.save(update_fields=["first_name", "username"])
    director.user.first_name = "Director"
    director.user.username = "director_member"
    director.user.save(update_fields=["first_name", "username"])

    access_token = login(api_client, membership=actor)
    response = api_client.get(
        f"/api/v1/establishments/{establishment.id}/users/search/"
        f"?q=member&business_unit_id={restaurant.id}",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    membership_ids = {item["membership_id"] for item in response.json()}
    assert str(owner.id) in membership_ids
    assert str(director.id) in membership_ids
    assert str(scoped_staff.id) in membership_ids
    assert str(out_staff.id) not in membership_ids


def test_user_search_without_business_unit_id_is_unchanged(api_client):
    establishment = create_establishment(name="Unfiltered Hotel")
    restaurant = create_business_unit(establishment=establishment, key="restaurant")

    actor = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )

    out_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    out_staff.user.first_name = "Outside"
    out_staff.user.save(update_fields=["first_name"])
    create_membership_with_business_unit_scope(membership=out_staff, business_unit=restaurant)

    access_token = login(api_client, membership=actor)
    response = api_client.get(
        f"/api/v1/establishments/{establishment.id}/users/search/?q=out",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["membership_id"] == str(out_staff.id)


def test_user_search_rejects_invalid_business_unit_id(api_client):
    establishment = create_establishment(name="Invalid BU Hotel")
    actor = create_membership(establishment=establishment)

    access_token = login(api_client, membership=actor)
    response = api_client.get(
        f"/api/v1/establishments/{establishment.id}/users/search/"
        f"?q=ac&business_unit_id={uuid.uuid4()}",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    assert response.json()["errors"]["business_unit_id"] == ["Invalid business unit."]
