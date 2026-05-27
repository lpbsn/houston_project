from __future__ import annotations

from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import SessionRefreshToken, User, UserSession
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipDomain,
    OperationalDomain,
)
from houston.organizations.models import Organization

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


def create_membership(
    *,
    user,
    organization_status=Organization.Status.ACTIVE,
    establishment_status=Establishment.Status.ACTIVE,
    membership_status=EstablishmentMembership.Status.ACTIVE,
    role=EstablishmentMembership.Role.OWNER,
    name="Demo Hotel",
    domains=None,
):
    organization = Organization.objects.create(name=f"{name} Group", status=organization_status)
    establishment = Establishment.objects.create(
        name=name,
        organization=organization,
        status=establishment_status,
    )
    membership = EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        status=membership_status,
        role=role,
    )

    for domain_key in domains or []:
        domain = OperationalDomain.objects.create(
            establishment=establishment,
            key=domain_key,
            label=domain_key.replace("_", " ").title(),
        )
        MembershipDomain.objects.create(membership=membership, operational_domain=domain)

    return membership


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")

    assert response.status_code == 200
    assert "csrftoken" in api_client.cookies

    return api_client.cookies["csrftoken"].value


def auth_headers(csrf_token: str, access_token: str | None = None) -> dict:
    headers = {
        "HTTP_X_CSRFTOKEN": csrf_token,
    }

    if access_token is not None:
        headers["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"

    return headers


def login(api_client: APIClient, csrf_token: str, *, identifier: str, password: str):
    return api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": password},
        format="json",
        **auth_headers(csrf_token),
    )


def test_csrf_endpoint_sets_csrf_cookie(api_client):
    response = api_client.get("/api/v1/auth/csrf/")

    assert response.status_code == 200
    assert response.json() == {"detail": "CSRF cookie set."}
    assert "csrftoken" in api_client.cookies


def test_login_without_csrf_is_forbidden(api_client, active_user):
    ensure_csrf(api_client)

    response = api_client.post(
        "/api/v1/auth/login/",
        {"identifier": active_user.email, "password": "secret"},
        format="json",
    )

    assert response.status_code == 403


def test_login_with_csrf_succeeds_for_valid_email(api_client, active_user):
    create_membership(user=active_user, domains=["housekeeping"])
    csrf_token = ensure_csrf(api_client)

    response = login(
        api_client,
        csrf_token,
        identifier="MANAGER@example.com",
        password="secret",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["email"] == "manager@example.com"
    assert len(body["memberships"]) == 1
    assert body["memberships"][0]["operational_domains"] == ["housekeeping"]
    assert body["active_membership"]["establishment_name"] == "Demo Hotel"
    assert "access_token" in body
    assert settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME in response.cookies


def test_login_with_csrf_succeeds_for_valid_username(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)

    response = login(
        api_client,
        csrf_token,
        identifier=active_user.username,
        password="secret",
    )

    assert response.status_code == 200
    assert response.json()["user"]["username"] == active_user.username


def test_invalid_login_returns_generic_error(api_client, active_user):
    csrf_token = ensure_csrf(api_client)

    response = login(
        api_client,
        csrf_token,
        identifier=active_user.username,
        password="wrong-password",
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials."}


def test_inactive_user_login_returns_same_generic_error(api_client):
    user = User.objects.create_user(
        username="suspended_01",
        email="suspended@example.com",
        password="secret",
        status=User.Status.SUSPENDED,
    )
    csrf_token = ensure_csrf(api_client)

    response = login(
        api_client,
        csrf_token,
        identifier=user.email,
        password="secret",
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials."}


def test_bootstrap_with_valid_bearer_returns_authenticated_payload(api_client, active_user):
    create_membership(user=active_user, domains=["housekeeping"])
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
    body = response.json()
    assert body["authenticated"] is True
    assert "memberships" in body
    assert "active_memberships" not in body
    assert body["memberships"][0]["operational_domains"] == ["housekeeping"]


def test_bootstrap_without_bearer_returns_unauthorized(api_client):
    response = api_client.get("/api/v1/auth/bootstrap/")

    assert response.status_code == 401


def test_bootstrap_filters_inactive_memberships_establishments_and_organizations(
    api_client,
    active_user,
):
    create_membership(user=active_user, name="Active")
    create_membership(
        user=active_user,
        name="Inactive Membership",
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )
    create_membership(
        user=active_user,
        name="Inactive Establishment",
        establishment_status=Establishment.Status.DEACTIVATED,
    )
    create_membership(
        user=active_user,
        name="Inactive Organization",
        organization_status=Organization.Status.SUSPENDED,
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
    body = response.json()
    assert [membership["establishment_name"] for membership in body["memberships"]] == ["Active"]
    assert body["active_membership"]["establishment_name"] == "Active"


def test_active_membership_is_null_for_multiple_memberships(api_client, active_user):
    create_membership(user=active_user, name="Nice")
    create_membership(user=active_user, name="Cannes")
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


def test_refresh_without_csrf_is_forbidden(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )

    response = api_client.post("/api/v1/auth/refresh/")

    assert response.status_code == 403


def test_refresh_with_csrf_succeeds_and_rotates_refresh_token(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )
    first_refresh_cookie = login_response.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME].value
    first_access_token = login_response.json()["access_token"]

    response = api_client.post("/api/v1/auth/refresh/", **auth_headers(csrf_token))

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"] != first_access_token
    assert response.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME].value != first_refresh_cookie


def test_old_refresh_token_reuse_revokes_family(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )
    old_refresh_cookie = login_response.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME].value
    api_client.post("/api/v1/auth/refresh/", **auth_headers(csrf_token))

    reuse_client = APIClient(enforce_csrf_checks=True)
    reuse_csrf = ensure_csrf(reuse_client)
    reuse_client.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME] = old_refresh_cookie

    response = reuse_client.post("/api/v1/auth/refresh/", **auth_headers(reuse_csrf))

    assert response.status_code == 401
    assert response.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME].value == ""

    session = UserSession.objects.get(user=active_user)
    session.refresh_from_db()
    assert session.status == UserSession.Status.REVOKED


def test_unknown_refresh_token_returns_unauthorized(api_client, active_user):
    csrf_token = ensure_csrf(api_client)
    api_client.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME] = "unknown-refresh-token"

    response = api_client.post("/api/v1/auth/refresh/", **auth_headers(csrf_token))

    assert response.status_code == 401


def test_expired_refresh_token_returns_unauthorized(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )
    refresh_token = SessionRefreshToken.objects.get(session__user=active_user)
    refresh_token.expires_at = timezone.now() - timedelta(minutes=1)
    refresh_token.save(update_fields=["expires_at", "updated_at"])

    response = api_client.post("/api/v1/auth/refresh/", **auth_headers(csrf_token))

    assert response.status_code == 401


def test_logout_without_csrf_is_forbidden(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )
    access_token = login_response.json()["access_token"]

    response = api_client.post(
        "/api/v1/auth/logout/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 403


def test_logout_with_csrf_revokes_session_and_clears_cookie(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )
    access_token = login_response.json()["access_token"]

    response = api_client.post(
        "/api/v1/auth/logout/",
        **auth_headers(csrf_token, access_token),
    )

    assert response.status_code == 204
    assert response.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME].value == ""

    session = UserSession.objects.get(user=active_user)
    session.refresh_from_db()
    assert session.status == UserSession.Status.REVOKED


def test_auth_responses_do_not_expose_sensitive_fields(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )

    body = response.json()
    rendered_body = str(body)

    assert "password" not in rendered_body
    assert "token_digest" not in rendered_body
    assert "revoked_at" not in rendered_body


def test_email_is_normalized_before_login(api_client):
    user = User.objects.create_user(
        username="manager_01",
        email="  Manager@Example.com ",
        password="secret",
        status=User.Status.ACTIVE,
    )
    create_membership(user=user)
    csrf_token = ensure_csrf(api_client)

    response = login(
        api_client,
        csrf_token,
        identifier="MANAGER@example.com",
        password="secret",
    )

    assert response.status_code == 200
