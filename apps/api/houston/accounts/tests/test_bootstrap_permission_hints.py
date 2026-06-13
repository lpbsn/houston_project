from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.chat.permissions import can_access_chat
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.permissions import (
    can_create_action,
    can_invite_memberships,
    can_manage_runtime_context,
)
from houston.organizations.models import Organization

from .test_auth_api import create_membership, ensure_csrf, login

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def active_user():
    return User.objects.create_user(
        username="manager_01",
        email="manager@example.com",
        password="secret",
        status=User.Status.ACTIVE,
    )


def fetch_bootstrap_hints(
    api_client: APIClient,
    *,
    active_user,
) -> dict:
    csrf_token = ensure_csrf(api_client)
    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )
    access_token = login_response.json()["access_token"]

    response = api_client.get(
        "/api/v1/auth/bootstrap/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )
    assert response.status_code == 200
    return response.json()["permission_hints"]


@pytest.mark.parametrize(
    ("role", "expected_can_create_action", "expected_can_invite", "expected_can_manage_runtime_config"),
    [
        (EstablishmentMembership.Role.OWNER, True, True, True),
        (EstablishmentMembership.Role.DIRECTOR, True, True, True),
        (EstablishmentMembership.Role.MANAGER, True, True, False),
        (EstablishmentMembership.Role.STAFF, False, False, False),
    ],
)
def test_bootstrap_permission_hints_match_rbac_helpers_for_active_membership(
    api_client,
    active_user,
    role,
    expected_can_create_action,
    expected_can_invite,
    expected_can_manage_runtime_config,
):
    membership = create_membership(user=active_user, role=role)
    membership.establishment.chat_enabled = True
    membership.establishment.save(update_fields=["chat_enabled"])

    hints = fetch_bootstrap_hints(api_client, active_user=active_user)

    assert hints == {
        "chat_available": can_access_chat(membership),
        "can_create_action": expected_can_create_action,
        "can_invite": expected_can_invite,
        "can_manage_runtime_config": expected_can_manage_runtime_config,
    }
    assert hints["can_create_action"] is can_create_action(membership)
    assert hints["can_invite"] is can_invite_memberships(membership)
    assert hints["can_manage_runtime_config"] is can_manage_runtime_context(membership)


def test_bootstrap_permission_hints_chat_available_requires_chat_enabled(
    api_client,
    active_user,
):
    membership = create_membership(user=active_user, role=EstablishmentMembership.Role.OWNER)
    membership.establishment.chat_enabled = False
    membership.establishment.save(update_fields=["chat_enabled"])

    hints = fetch_bootstrap_hints(api_client, active_user=active_user)

    assert hints["chat_available"] is False
    assert hints["can_invite"] is True
    assert hints["can_manage_runtime_config"] is True


def test_bootstrap_permission_hints_are_false_without_active_membership(
    api_client,
    active_user,
):
    create_membership(user=active_user, name="Nice")
    create_membership(user=active_user, name="Cannes")

    hints = fetch_bootstrap_hints(api_client, active_user=active_user)

    assert hints == {
        "chat_available": False,
        "can_create_action": False,
        "can_invite": False,
        "can_manage_runtime_config": False,
    }


def test_bootstrap_permission_hints_fail_closed_for_inactive_establishment(
    api_client,
    active_user,
):
    membership = create_membership(
        user=active_user,
        establishment_status=Establishment.Status.DEACTIVATED,
    )

    csrf_token = ensure_csrf(api_client)
    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )
    access_token = login_response.json()["access_token"]

    response = api_client.get(
        "/api/v1/auth/bootstrap/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 200
    assert response.json()["active_membership"] is None
    assert response.json()["permission_hints"] == {
        "chat_available": False,
        "can_create_action": False,
        "can_invite": False,
        "can_manage_runtime_config": False,
    }
    assert membership.establishment_id not in {
        item["establishment_id"] for item in response.json()["memberships"]
    }


def test_bootstrap_permission_hints_fail_closed_for_inactive_organization(
    api_client,
    active_user,
):
    create_membership(
        user=active_user,
        organization_status=Organization.Status.SUSPENDED,
    )

    hints = fetch_bootstrap_hints(api_client, active_user=active_user)

    assert hints == {
        "chat_available": False,
        "can_create_action": False,
        "can_invite": False,
        "can_manage_runtime_config": False,
    }
