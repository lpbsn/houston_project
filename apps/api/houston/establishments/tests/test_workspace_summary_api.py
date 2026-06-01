from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
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
        password=TEST_PASSWORD,
        first_name=first_name,
        last_name=last_name,
        status=status,
    )


def create_establishment(*, name: str = "Demo Hotel") -> Establishment:
    organization = Organization.objects.create(
        name=f"{name} Group {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name=name,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )


def create_membership(
    *,
    user: User,
    establishment: Establishment,
    role: str = EstablishmentMembership.Role.STAFF,
    membership_status: str = EstablishmentMembership.Status.ACTIVE,
) -> EstablishmentMembership:
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=membership_status,
    )


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return api_client.cookies["csrftoken"].value


def login(api_client: APIClient, *, identifier: str, password: str = TEST_PASSWORD) -> str:
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
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    ],
)
def test_active_members_can_read_workspace_summary(api_client, actor_role):
    establishment = create_establishment(name="Summary Hotel")

    owner = create_user(
        username="summary_owner",
        first_name="Summary",
        last_name="Owner",
    )
    create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    director_is_actor = actor_role == EstablishmentMembership.Role.DIRECTOR
    director = create_user(
        username="summary_director",
        first_name="Summary",
        last_name="Director",
    )
    create_membership(
        user=director,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        membership_status=(
            EstablishmentMembership.Status.ACTIVE
            if director_is_actor
            else EstablishmentMembership.Status.INVITED
        ),
    )
    if director_is_actor:
        actor = director
    else:
        actor = create_user(username=f"{actor_role}_summary_actor")
        create_membership(user=actor, establishment=establishment, role=actor_role)

    expected_active_count = 2
    expected_director_status = "active" if director_is_actor else "invited"

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        f"/api/v1/establishments/{establishment.id}/workspace-summary/",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["establishment"]["name"] == "Summary Hotel"
    assert body["owner"]["display_name"] == owner.get_full_name()
    assert body["director"]["display_name"] == director.get_full_name()
    assert body["director"]["status"] == expected_director_status
    assert body["active_membership_count"] == expected_active_count


def test_workspace_summary_returns_not_found_for_foreign_establishment(api_client):
    establishment = create_establishment(name="Nice")
    actor = create_user(username="summary_owner_actor")
    create_membership(
        user=actor,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    foreign_establishment = create_establishment(name="Cannes")

    access_token = login(api_client, identifier=actor.email)
    response = api_client.get(
        f"/api/v1/establishments/{foreign_establishment.id}/workspace-summary/",
        **auth_headers(access_token),
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Not found."}
