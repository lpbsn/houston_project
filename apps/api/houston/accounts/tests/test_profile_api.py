from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.test_membership_api import (
    auth_headers,
    create_membership,
    create_user,
    ensure_csrf,
    login,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def test_user_can_patch_own_profile(api_client):
    user = create_user(username="profile_user", email="profile@example.com")
    membership = create_membership(user=user, role=EstablishmentMembership.Role.STAFF)

    access_token = login(api_client, identifier=user.email)
    response = api_client.patch(
        "/api/v1/auth/me/",
        {
            "first_name": "Jean",
            "last_name": "Dupont",
            "email": "jean.dupont@example.com",
        },
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["first_name"] == "Jean"
    assert body["user"]["last_name"] == "Dupont"
    assert body["user"]["email"] == "jean.dupont@example.com"
    assert body["active_membership"]["id"] == str(membership.id)

    user.refresh_from_db()
    assert user.first_name == "Jean"
    assert user.last_name == "Dupont"
    assert user.email == "jean.dupont@example.com"


def test_user_profile_patch_requires_authentication(api_client):
    csrf_token = ensure_csrf(api_client)
    response = api_client.patch(
        "/api/v1/auth/me/",
        {"first_name": "Jean"},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert response.status_code == 401
