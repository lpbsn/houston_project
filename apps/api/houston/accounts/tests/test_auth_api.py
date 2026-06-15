from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import SessionRefreshToken, User, UserSession
from houston.establishments.models import (
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.tests.taxonomy_helpers import create_business_unit
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
    business_unit_keys=None,
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

    for key in business_unit_keys or []:
        business_unit = create_business_unit(establishment=establishment, key=key)
        MembershipScope.objects.create(membership=membership, business_unit=business_unit)

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


def login(
    api_client: APIClient,
    csrf_token: str,
    *,
    identifier: str,
    password: str,
    **extra_headers,
):
    return api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": password},
        format="json",
        **auth_headers(csrf_token),
        **extra_headers,
    )


def switch_establishment(
    api_client: APIClient,
    *,
    access_token: str,
    establishment_id,
):
    return api_client.post(
        "/api/v1/auth/switch_establishment/",
        {"establishment_id": str(establishment_id)},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
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
    assert response.json() == {
        "code": "permission_denied",
        "detail": "CSRF validation failed.",
    }


def test_login_with_csrf_succeeds_for_valid_email(api_client, active_user):
    membership = create_membership(user=active_user, business_unit_keys=["housekeeping"])
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
    housekeeping_business_unit = BusinessUnit.objects.get(
        establishment=membership.establishment,
        key="housekeeping",
    )
    assert body["memberships"][0]["scopes"] == [
        {
            "scope_type": "business_unit",
            "scope_id": str(housekeeping_business_unit.id),
        }
    ]
    assert body["memberships"][0]["scope_summary"] == {"business_unit_count": 1}
    assert "module_count" not in body["memberships"][0]["scope_summary"]
    assert body["active_membership"]["establishment_name"] == "Demo Hotel"
    assert "access_token" in body
    assert settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME in response.cookies

    session = UserSession.objects.get(user=active_user)
    assert session.selected_establishment_id == membership.establishment_id


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


def test_login_with_trusted_browser_origin_succeeds_when_proxy_host_differs(
    api_client,
    active_user,
    settings,
):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "api"]
    settings.CSRF_TRUSTED_ORIGINS = ["http://localhost:5173"]

    response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
        HTTP_HOST="api:8000",
        HTTP_ORIGIN="http://localhost:5173",
    )

    assert response.status_code == 200
    assert response.json()["authenticated"] is True


def test_invalid_login_returns_generic_error(api_client, active_user):
    csrf_token = ensure_csrf(api_client)

    response = login(
        api_client,
        csrf_token,
        identifier=active_user.username,
        password="wrong-password",
    )

    assert response.status_code == 401
    assert response.json() == {
        "code": "not_authenticated",
        "detail": "Invalid credentials.",
    }


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
    assert response.json() == {
        "code": "not_authenticated",
        "detail": "Invalid credentials.",
    }


def test_bootstrap_with_valid_bearer_returns_authenticated_payload(api_client, active_user):
    membership = create_membership(user=active_user, business_unit_keys=["housekeeping"])
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
    housekeeping_business_unit = BusinessUnit.objects.get(
        establishment=membership.establishment,
        key="housekeeping",
    )
    assert body["memberships"][0]["scopes"] == [
        {
            "scope_type": "business_unit",
            "scope_id": str(housekeeping_business_unit.id),
        }
    ]


def test_bootstrap_without_bearer_returns_unauthorized(api_client):
    response = api_client.get("/api/v1/auth/bootstrap/")

    assert response.status_code == 401
    assert response.json() == {
        "code": "not_authenticated",
        "detail": "Authentication credentials were not provided.",
    }


def test_bootstrap_with_invalid_bearer_returns_unauthorized(api_client):
    response = api_client.get(
        "/api/v1/auth/bootstrap/",
        HTTP_AUTHORIZATION="Bearer invalid-access-token",
    )

    assert response.status_code == 401
    assert response.json() == {
        "code": "authentication_failed",
        "detail": "Invalid access token.",
    }


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

    session = UserSession.objects.get(user=active_user)
    assert session.selected_establishment_id is None


def test_switch_establishment_requires_bearer_auth(api_client, active_user):
    create_membership(user=active_user, name="Nice")
    create_membership(user=active_user, name="Cannes")

    response = api_client.post(
        "/api/v1/auth/switch_establishment/",
        {"establishment_id": str(uuid.uuid4())},
        format="json",
    )

    assert response.status_code == 401
    assert response.json() == {
        "code": "not_authenticated",
        "detail": "Authentication credentials were not provided.",
    }


def test_switch_establishment_selects_active_membership_for_session(api_client, active_user):
    first_membership = create_membership(user=active_user, name="Nice")
    second_membership = create_membership(user=active_user, name="Cannes")
    csrf_token = ensure_csrf(api_client)
    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )
    access_token = login_response.json()["access_token"]

    response = switch_establishment(
        api_client,
        access_token=access_token,
        establishment_id=second_membership.establishment_id,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["active_membership"]["establishment_name"] == second_membership.establishment.name
    assert body["memberships"][0]["establishment_name"] == second_membership.establishment.name

    session = UserSession.objects.get(user=active_user)
    assert session.selected_establishment_id == second_membership.establishment_id

    bootstrap_response = api_client.get(
        "/api/v1/auth/bootstrap/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert bootstrap_response.status_code == 200
    assert (
        bootstrap_response.json()["active_membership"]["establishment_name"]
        == second_membership.establishment.name
    )
    assert first_membership.establishment.name in {
        membership["establishment_name"] for membership in bootstrap_response.json()["memberships"]
    }


def test_switch_establishment_returns_not_found_for_foreign_or_inactive_targets(
    api_client,
    active_user,
):
    create_membership(user=active_user, name="Nice")
    foreign_user = User.objects.create_user(
        username="other_user",
        email="other@example.com",
        password="secret",
        status=User.Status.ACTIVE,
    )
    foreign_membership = create_membership(user=foreign_user, name="Foreign")
    inactive_membership = create_membership(
        user=active_user,
        name="Inactive",
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

    foreign_response = switch_establishment(
        api_client,
        access_token=access_token,
        establishment_id=foreign_membership.establishment_id,
    )
    inactive_response = switch_establishment(
        api_client,
        access_token=access_token,
        establishment_id=inactive_membership.establishment_id,
    )

    assert foreign_response.status_code == 404
    assert foreign_response.json() == {"detail": "Not found."}
    assert inactive_response.status_code == 404
    assert inactive_response.json() == {"detail": "Not found."}


def test_switch_establishment_with_invalid_uuid_returns_bad_request(api_client, active_user):
    create_membership(user=active_user, name="Nice")
    csrf_token = ensure_csrf(api_client)
    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )
    access_token = login_response.json()["access_token"]

    response = api_client.post(
        "/api/v1/auth/switch_establishment/",
        {"establishment_id": "not-a-uuid"},
        format="json",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["detail"] == "Request validation failed."
    assert "errors" in body


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
    assert response.json() == {
        "code": "permission_denied",
        "detail": "CSRF validation failed.",
    }


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


def test_bootstrap_clears_stale_selected_establishment_from_auth_session(api_client, active_user):
    create_membership(user=active_user, name="Nice")
    foreign_user = User.objects.create_user(
        username="foreign_01",
        email="foreign@example.com",
        password="secret",
        status=User.Status.ACTIVE,
    )
    foreign_membership = create_membership(user=foreign_user, name="Foreign")
    csrf_token = ensure_csrf(api_client)
    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )
    access_token = login_response.json()["access_token"]

    session = UserSession.objects.get(user=active_user)
    session.selected_establishment = foreign_membership.establishment
    session.save(update_fields=["selected_establishment", "updated_at"])

    response = api_client.get(
        "/api/v1/auth/bootstrap/",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )

    assert response.status_code == 200
    assert response.json()["active_membership"] is None

    session.refresh_from_db()
    assert session.selected_establishment_id is None


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


@pytest.mark.django_db(transaction=True)
def test_concurrent_refresh_only_one_succeeds(active_user):
    create_membership(user=active_user)
    login_client = APIClient(enforce_csrf_checks=True)
    login_csrf = ensure_csrf(login_client)
    login_response = login(
        login_client,
        login_csrf,
        identifier=active_user.email,
        password="secret",
    )
    assert login_response.status_code == 200
    raw_refresh_cookie = login_response.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME].value

    def try_refresh(_: int) -> tuple[int, dict | None]:
        close_old_connections()
        try:
            client = APIClient(enforce_csrf_checks=True)
            client.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME] = raw_refresh_cookie
            csrf_token = ensure_csrf(client)
            response = client.post("/api/v1/auth/refresh/", **auth_headers(csrf_token))
            body = response.json() if response.content else None
            return response.status_code, body
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(try_refresh, range(2)))

    statuses = [status for status, _ in results]
    assert 200 in statuses
    assert 401 in statuses
    assert 500 not in statuses

    failed_response = next(body for status, body in results if status == 401)
    assert failed_response == {
        "code": "not_authenticated",
        "detail": "Authentication failed.",
    }

    session = UserSession.objects.get(user=active_user)
    session.refresh_from_db()
    assert session.status == UserSession.Status.REVOKED


def test_unknown_refresh_token_returns_unauthorized(api_client, active_user):
    csrf_token = ensure_csrf(api_client)
    api_client.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME] = "unknown-refresh-token"

    response = api_client.post("/api/v1/auth/refresh/", **auth_headers(csrf_token))

    assert response.status_code == 401
    assert response.json() == {
        "code": "not_authenticated",
        "detail": "Authentication failed.",
    }


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
    assert response.json() == {
        "code": "not_authenticated",
        "detail": "Authentication failed.",
    }


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
    assert response.json() == {
        "code": "permission_denied",
        "detail": "CSRF validation failed.",
    }


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


def test_logout_with_csrf_and_refresh_cookie_only_revokes_session(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )

    response = api_client.post(
        "/api/v1/auth/logout/",
        **auth_headers(csrf_token),
    )

    assert response.status_code == 204
    assert response.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME].value == ""

    session = UserSession.objects.get(user=active_user)
    session.refresh_from_db()
    assert session.status == UserSession.Status.REVOKED


def test_logout_with_invalid_bearer_falls_back_to_refresh_cookie(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
    )

    response = api_client.post(
        "/api/v1/auth/logout/",
        **auth_headers(csrf_token, "invalid-access-token"),
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
