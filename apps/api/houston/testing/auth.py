from __future__ import annotations

from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import EstablishmentMembership
from houston.testing.factories import TEST_PASSWORD, build_membership

__all__ = [
    "TEST_PASSWORD",
    "auth_headers",
    "build_api_membership",
    "ensure_csrf",
    "login",
]


def build_api_membership(**kwargs) -> EstablishmentMembership:
    membership = build_membership(**kwargs)
    membership.user.set_password(TEST_PASSWORD)
    membership.user.save(update_fields=["password"])
    return membership


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")
    assert response.status_code == 200
    return api_client.cookies["csrftoken"].value


def login(api_client: APIClient, *, user: User, password: str = TEST_PASSWORD) -> str:
    identifier = user.email if user.email else user.username
    csrf_token = ensure_csrf(api_client)
    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(access_token: str) -> dict[str, str]:
    return {"HTTP_AUTHORIZATION": f"Bearer {access_token}"}
