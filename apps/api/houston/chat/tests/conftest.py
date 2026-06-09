from __future__ import annotations

import uuid

import pytest
from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.organizations.models import Organization
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def create_user(*, username: str, status: str = User.Status.ACTIVE) -> User:
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password=TEST_PASSWORD,
        status=status,
    )


def create_establishment(
    *,
    status: str = Establishment.Status.ACTIVE,
    chat_enabled: bool = True,
) -> Establishment:
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name="Chat Hotel",
        organization=organization,
        status=status,
        chat_enabled=chat_enabled,
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


def login(api_client: APIClient, *, user: User) -> str:
    csrf = api_client.get("/api/v1/auth/csrf/").cookies["csrftoken"].value
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": user.email, "password": TEST_PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=csrf,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def ws_ticket_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/chat/ws-ticket/"


def ws_chat_path(establishment_id) -> str:
    return f"/ws/v1/establishments/{establishment_id}/chat/"


def get_ws_ticket(api_client, *, user, establishment) -> str:
    token = login(api_client, user=user)
    response = api_client.post(
        ws_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 200
    return response.json()["ticket"]


def default_ws_headers() -> list[tuple[bytes, bytes]]:
    return [
        (b"host", b"localhost"),
        (b"origin", b"http://localhost"),
    ]
