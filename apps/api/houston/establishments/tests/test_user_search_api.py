from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def create_user(
    *,
    username: str,
    email: str | None = None,
    first_name: str = "",
    last_name: str = "",
    status: str = User.Status.ACTIVE,
) -> User:
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@example.com",
        password="secret",
        first_name=first_name,
        last_name=last_name,
        status=status,
    )


def create_membership(
    *,
    user: User,
    establishment: Establishment,
    role: str = EstablishmentMembership.Role.STAFF,
    status: str = EstablishmentMembership.Status.ACTIVE,
) -> EstablishmentMembership:
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=status,
    )


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return api_client.cookies["csrftoken"].value


def login(api_client: APIClient, *, identifier: str, password: str = "secret") -> str:
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(access_token: str) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}


@pytest.mark.parametrize(
    "actor_role",
    [
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    ],
)
def test_active_member_can_search_current_establishment_users_with_minimal_fields(
    api_client,
    actor_role,
):
    organization = Organization.objects.create(name=f"Nice Group {uuid.uuid4().hex[:6]}")
    establishment = Establishment.objects.create(
        name="Nice",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    actor = create_user(username=f"{actor_role}_actor")
    create_membership(
        user=actor,
        establishment=establishment,
        role=actor_role,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    name_match = create_membership(
        user=create_user(
            username="mario",
            email="mario@example.com",
            first_name="Mario",
            last_name="Rossi",
        ),
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    username_match = create_membership(
        user=create_user(
            username="marina_ops",
            email="ops@example.com",
        ),
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    email_match = create_membership(
        user=create_user(
            username="luca",
            email="marco@example.com",
        ),
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        f"/api/v1/establishments/{establishment.id}/users/search/?q=mar",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert {item["membership_id"] for item in body} == {
        str(name_match.id),
        str(username_match.id),
        str(email_match.id),
    }
    expected_keys = {
        "id",
        "display_name",
        "username",
        "email",
        "role",
        "membership_id",
    }
    assert all(set(item.keys()) == expected_keys for item in body)
    mario_row = next(item for item in body if item["membership_id"] == str(name_match.id))
    assert mario_row == {
        "id": str(name_match.user_id),
        "display_name": "Mario Rossi",
        "username": "mario",
        "email": "mario@example.com",
        "role": EstablishmentMembership.Role.STAFF,
        "membership_id": str(name_match.id),
    }


def test_search_returns_not_found_when_path_establishment_is_outside_current_context(
    api_client,
):
    primary_org = Organization.objects.create(name="Nice Group")
    primary_establishment = Establishment.objects.create(
        name="Nice",
        organization=primary_org,
        status=Establishment.Status.ACTIVE,
    )
    foreign_establishment = Establishment.objects.create(
        name="Cannes",
        organization=Organization.objects.create(name="Cannes Group"),
        status=Establishment.Status.ACTIVE,
    )
    actor = create_user(username="staff_actor")
    create_membership(
        user=actor,
        establishment=primary_establishment,
        role=EstablishmentMembership.Role.STAFF,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        f"/api/v1/establishments/{foreign_establishment.id}/users/search/?q=ca",
        **auth_headers(access_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}


def test_search_requires_minimum_query_length(api_client):
    organization = Organization.objects.create(name="Nice Group")
    establishment = Establishment.objects.create(
        name="Nice",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    actor = create_user(username="staff_actor")
    create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        f"/api/v1/establishments/{establishment.id}/users/search/?q=a",
        **auth_headers(access_token),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["detail"] == "Request validation failed."
    assert body["errors"]["q"] == ["Ensure this field has at least 2 characters."]


def test_search_excludes_inactive_and_foreign_memberships(api_client):
    organization = Organization.objects.create(name="Nice Group")
    establishment = Establishment.objects.create(
        name="Nice",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    foreign_establishment = Establishment.objects.create(
        name="Cannes",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    actor = create_user(username="staff_actor")
    create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    visible_membership = create_membership(
        user=create_user(username="caroline", first_name="Caroline"),
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        user=create_user(
            username="carter",
            first_name="Carter",
            status=User.Status.SUSPENDED,
        ),
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        user=create_user(username="carl", first_name="Carl"),
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.DEACTIVATED,
    )
    create_membership(
        user=create_user(username="carla", first_name="Carla"),
        establishment=foreign_establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        f"/api/v1/establishments/{establishment.id}/users/search/?q=car",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "id": str(visible_membership.user_id),
            "display_name": "Caroline",
            "username": "caroline",
            "email": "caroline@example.com",
            "role": EstablishmentMembership.Role.STAFF,
            "membership_id": str(visible_membership.id),
        }
    ]


def test_search_without_selected_establishment_context_returns_not_found(api_client):
    organization = Organization.objects.create(name="Nice Group")
    first_establishment = Establishment.objects.create(
        name="Nice",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    second_establishment = Establishment.objects.create(
        name="Cannes",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    actor = create_user(username="multi_actor")
    create_membership(user=actor, establishment=first_establishment)
    create_membership(user=actor, establishment=second_establishment)

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        f"/api/v1/establishments/{first_establishment.id}/users/search/?q=ni",
        **auth_headers(access_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
