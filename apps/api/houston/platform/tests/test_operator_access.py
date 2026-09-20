from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.establishments.models import EstablishmentMembership
from houston.organizations.models import Organization
from houston.platform.exceptions import PlatformLifecycleDenied
from houston.platform.models import PlatformLifecycleEvent, PlatformOperatorAccess
from houston.platform.selectors import is_active_platform_operator
from houston.platform.services import (
    execute_platform_lifecycle,
    grant_platform_operator,
    revoke_platform_operator,
)
from houston.testing.auth import auth_headers, login
from houston.testing.factories import build_membership, create_user
from houston.testing.platform import grant_operator

pytestmark = pytest.mark.django_db

PLATFORM_SESSION = "/api/v1/platform/session/"


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _operator_user() -> User:
    return create_user(username=f"operator_{User.objects.count()}")


def test_grant_and_revoke_do_not_create_membership():
    user = _operator_user()
    grant_platform_operator(user=user)
    assert PlatformOperatorAccess.objects.filter(user=user, is_active=True).exists()
    assert EstablishmentMembership.objects.filter(user=user).count() == 0

    revoke_platform_operator(user=user)
    access = PlatformOperatorAccess.objects.get(user=user)
    assert access.is_active is False
    assert access.revoked_at is not None
    assert EstablishmentMembership.objects.filter(user=user).count() == 0
    assert is_active_platform_operator(user) is False


def test_management_grant_and_revoke_by_email():
    user = _operator_user()
    call_command("grant_platform_operator", user.email)
    assert is_active_platform_operator(user) is True
    call_command("revoke_platform_operator", user.email)
    assert is_active_platform_operator(user) is False


def test_management_grant_unknown_user_fails():
    with pytest.raises(CommandError, match="No user found"):
        call_command("grant_platform_operator", "missing@example.com")


def test_lifecycle_success_is_atomic_with_mutation():
    operator = _operator_user()
    grant_platform_operator(user=operator)

    def mutate():
        return Organization.objects.create(name="Tracked Org")

    org = execute_platform_lifecycle(
        operator=operator,
        action="test_create_org",
        resource_type="organization",
        resource_id=None,
        mutate=mutate,
    )
    event = PlatformLifecycleEvent.objects.get()
    assert event.result == PlatformLifecycleEvent.Result.OK
    assert event.operator_id == operator.pk
    assert Organization.objects.filter(pk=org.pk).exists()


def test_lifecycle_denied_rolls_back_mutation_and_keeps_event():
    operator = _operator_user()
    grant_platform_operator(user=operator)

    def mutate():
        Organization.objects.create(name="Rolled Back Org")
        raise PlatformLifecycleDenied("not_eligible")

    with pytest.raises(PlatformLifecycleDenied):
        execute_platform_lifecycle(
            operator=operator,
            action="test_denied",
            resource_type="organization",
            resource_id=None,
            mutate=mutate,
        )

    assert Organization.objects.filter(name="Rolled Back Org").count() == 0
    event = PlatformLifecycleEvent.objects.get()
    assert event.result == PlatformLifecycleEvent.Result.DENIED
    assert event.error_code == "not_eligible"


def test_lifecycle_failure_rolls_back_mutation_and_keeps_event():
    operator = _operator_user()
    grant_platform_operator(user=operator)

    def mutate():
        Organization.objects.create(name="Failed Org")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        execute_platform_lifecycle(
            operator=operator,
            action="test_failed",
            resource_type="organization",
            resource_id=None,
            mutate=mutate,
        )

    assert Organization.objects.filter(name="Failed Org").count() == 0
    event = PlatformLifecycleEvent.objects.get()
    assert event.result == PlatformLifecycleEvent.Result.FAILED
    assert event.error_code == "unexpected_error"


def test_platform_session_requires_operator_not_membership(api_client):
    operator = _operator_user()
    grant_operator(operator)
    token = login(api_client, user=operator)

    response = api_client.get(PLATFORM_SESSION, **auth_headers(token))
    assert response.status_code == 200
    assert response.json()["platform_operator_active"] is True
    assert response.json()["operator_id"] == str(operator.pk)
    assert EstablishmentMembership.objects.filter(user=operator).count() == 0


def test_authenticated_non_operator_gets_403_not_404(api_client):
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=membership.user)

    response = api_client.get(PLATFORM_SESSION, **auth_headers(token))
    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_anonymous_platform_session_is_401(api_client):
    response = api_client.get(PLATFORM_SESSION)
    assert response.status_code == 401


def test_revocation_takes_effect_on_next_request(api_client):
    operator = _operator_user()
    grant_operator(operator)
    token = login(api_client, user=operator)
    assert api_client.get(PLATFORM_SESSION, **auth_headers(token)).status_code == 200

    revoke_platform_operator(user=operator)
    denied = api_client.get(PLATFORM_SESSION, **auth_headers(token))
    assert denied.status_code == 403


def test_operator_without_membership_cannot_read_tenant_feed(api_client):
    build_membership(role=EstablishmentMembership.Role.OWNER)
    operator = _operator_user()
    grant_operator(operator)
    token = login(api_client, user=operator)

    assert api_client.get(PLATFORM_SESSION, **auth_headers(token)).status_code == 200
    feed = api_client.get("/api/v1/cross/signal-feed/", **auth_headers(token))
    assert feed.status_code == 403


def test_dual_context_keeps_tenant_rights_separate_from_platform(api_client):
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    grant_operator(membership.user)
    token = login(api_client, user=membership.user)

    assert api_client.get(PLATFORM_SESSION, **auth_headers(token)).status_code == 200
    feed = api_client.get("/api/v1/cross/signal-feed/", **auth_headers(token))
    assert feed.status_code == 200
