from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from houston.accounts.models import User, UserSession
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db

REGISTRATION_PASSWORD = "SecurePass123!"


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def ensure_csrf(api_client: APIClient) -> str:
    response = api_client.get("/api/v1/auth/csrf/")

    assert response.status_code == 200
    assert "csrftoken" in api_client.cookies

    return api_client.cookies["csrftoken"].value


def registration_payload(**overrides):
    payload = {
        "invite_code": "valid-code",
        "first_name": "Alex",
        "last_name": "Owner",
        "email": "alex.owner@example.com",
        "password": REGISTRATION_PASSWORD,
        "password_confirmation": REGISTRATION_PASSWORD,
        "organization_name": "Northwind Group",
        "establishment_name": "Northwind Hotel",
    }
    payload.update(overrides)
    return payload


def post_register(api_client: APIClient, csrf_token: str, payload: dict):
    return api_client.post(
        "/api/v1/auth/register/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )


def owner_validate_payload(**overrides):
    payload = {
        "invite_code": "valid-code",
        "first_name": "Alex",
        "last_name": "Owner",
        "email": "alex.owner@example.com",
        "password": REGISTRATION_PASSWORD,
        "password_confirmation": REGISTRATION_PASSWORD,
    }
    payload.update(overrides)
    return payload


def post_validate_owner(api_client: APIClient, csrf_token: str, payload: dict):
    return api_client.post(
        "/api/v1/auth/register/validate-owner/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )


def post_login(api_client: APIClient, csrf_token: str, *, identifier: str, password: str):
    return api_client.post(
        "/api/v1/auth/login/",
        {"identifier": identifier, "password": password},
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
    )


def count_provisioned_entities() -> dict[str, int]:
    return {
        "organizations": Organization.objects.count(),
        "establishments": Establishment.objects.count(),
        "users": User.objects.count(),
        "memberships": EstablishmentMembership.objects.count(),
        "onboarding_sessions": OnboardingSession.objects.count(),
        "user_sessions": UserSession.objects.count(),
    }


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_valid_invite_code_provisions_tenant_owner_and_session(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()

    response = post_register(api_client, csrf_token, registration_payload())

    assert response.status_code == 201
    assert response.data["access_token"]
    assert response.data["establishment_id"]
    assert response.data["onboarding_session_id"]
    assert response.data["user"]["email"] == "alex.owner@example.com"
    assert settings_refresh_cookie_present(api_client)

    organization = Organization.objects.get(name="Northwind Group")
    establishment = Establishment.objects.get(name="Northwind Hotel")
    user = User.objects.get(email="alex.owner@example.com")
    membership = EstablishmentMembership.objects.get(user=user, establishment=establishment)
    onboarding_session = OnboardingSession.objects.get(id=response.data["onboarding_session_id"])

    assert organization.status == Organization.Status.ACTIVE
    assert establishment.status == Establishment.Status.DRAFT
    assert establishment.organization_id == organization.id
    assert user.first_name == "Alex"
    assert user.last_name == "Owner"
    assert user.status == User.Status.ACTIVE
    assert user.has_usable_password()
    assert user.check_password(REGISTRATION_PASSWORD)
    assert membership.role == EstablishmentMembership.Role.OWNER
    assert membership.status == EstablishmentMembership.Status.ACTIVE
    assert onboarding_session.establishment_id == establishment.id
    assert onboarding_session.started_by_id == user.id

    after = count_provisioned_entities()
    assert after["organizations"] == before["organizations"] + 1
    assert after["establishments"] == before["establishments"] + 1
    assert after["users"] == before["users"] + 1
    assert after["memberships"] == before["memberships"] + 1
    assert after["onboarding_sessions"] == before["onboarding_sessions"] + 1
    assert after["user_sessions"] == before["user_sessions"] + 1


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_registered_owner_can_log_in_with_email_and_password(api_client):
    csrf_token = ensure_csrf(api_client)
    register_response = post_register(
        api_client,
        csrf_token,
        registration_payload(email="login.owner@example.com"),
    )

    assert register_response.status_code == 201

    login_response = post_login(
        api_client,
        csrf_token,
        identifier="login.owner@example.com",
        password=REGISTRATION_PASSWORD,
    )

    assert login_response.status_code == 200
    assert login_response.data["access_token"]
    assert login_response.data["user"]["email"] == "login.owner@example.com"


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_invalid_invite_code_returns_400_and_creates_nothing(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()

    response = post_register(
        api_client,
        csrf_token,
        registration_payload(invite_code="wrong-code"),
    )

    assert response.status_code == 400
    assert response.data["detail"] == "Invalid invitation code."
    assert response.data["code"] == "invalid_invite_code"
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_missing_invite_code_returns_400_and_creates_nothing(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()
    payload = registration_payload()
    payload.pop("invite_code")

    response = post_register(api_client, csrf_token, payload)

    assert response.status_code == 400
    assert "invite_code" in response.data
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_password_mismatch_returns_400_and_creates_nothing(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()

    response = post_register(
        api_client,
        csrf_token,
        registration_payload(password_confirmation="DifferentPass123!"),
    )

    assert response.status_code == 400
    assert "password_confirmation" in response.data
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_duplicate_email_returns_400_and_creates_nothing(api_client):
    csrf_token = ensure_csrf(api_client)
    first_response = post_register(api_client, csrf_token, registration_payload())
    assert first_response.status_code == 201

    before = count_provisioned_entities()
    duplicate_response = post_register(
        api_client,
        csrf_token,
        registration_payload(email="alex.owner@example.com", organization_name="Other Org"),
    )

    assert duplicate_response.status_code == 400
    assert duplicate_response.data["detail"] == "An account with this email already exists."
    assert duplicate_response.data["code"] == "duplicate_email"
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=[])
def test_empty_invite_code_configuration_rejects_registration(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()

    response = post_register(api_client, csrf_token, registration_payload())

    assert response.status_code == 400
    assert response.data["code"] == "invalid_invite_code"
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_weak_password_returns_400_and_creates_nothing(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()

    response = post_register(
        api_client,
        csrf_token,
        registration_payload(password="123", password_confirmation="123"),
    )

    assert response.status_code == 400
    assert "password" in response.data
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_password_below_minimum_length_returns_400_and_creates_nothing(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()
    short_password = "a" * 11

    response = post_register(
        api_client,
        csrf_token,
        registration_payload(
            password=short_password,
            password_confirmation=short_password,
        ),
    )

    assert response.status_code == 400
    assert "password" in response.data
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_validate_owner_rejects_short_password(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()
    short_password = "a" * 11

    response = post_validate_owner(
        api_client,
        csrf_token,
        owner_validate_payload(
            password=short_password,
            password_confirmation=short_password,
        ),
    )

    assert response.status_code == 400
    assert "password" in response.data
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_validate_owner_rejects_common_password(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()
    common_password = "password12345"

    response = post_validate_owner(
        api_client,
        csrf_token,
        owner_validate_payload(
            password=common_password,
            password_confirmation=common_password,
        ),
    )

    assert response.status_code == 400
    assert "password" in response.data
    assert response.data["password"]
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_validate_owner_rejects_password_mismatch(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()

    response = post_validate_owner(
        api_client,
        csrf_token,
        owner_validate_payload(password_confirmation="DifferentPass123!"),
    )

    assert response.status_code == 400
    assert "password_confirmation" in response.data
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_validate_owner_rejects_invalid_invite_code(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()

    response = post_validate_owner(
        api_client,
        csrf_token,
        owner_validate_payload(invite_code="wrong-code"),
    )

    assert response.status_code == 400
    assert response.data["code"] == "invalid_invite_code"
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_validate_owner_rejects_duplicate_email(api_client):
    csrf_token = ensure_csrf(api_client)
    register_response = post_register(
        api_client,
        csrf_token,
        registration_payload(email="existing.owner@example.com"),
    )
    assert register_response.status_code == 201

    before = count_provisioned_entities()
    response = post_validate_owner(
        api_client,
        csrf_token,
        owner_validate_payload(email="existing.owner@example.com"),
    )

    assert response.status_code == 400
    assert response.data["code"] == "duplicate_email"
    assert count_provisioned_entities() == before


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_validate_owner_success_creates_nothing(api_client):
    csrf_token = ensure_csrf(api_client)
    before = count_provisioned_entities()

    response = post_validate_owner(
        api_client,
        csrf_token,
        owner_validate_payload(email="validate.owner@example.com"),
    )

    assert response.status_code == 204
    assert response.data is None
    assert count_provisioned_entities() == before


def settings_refresh_cookie_present(api_client: APIClient) -> bool:
    from django.conf import settings as django_settings

    return django_settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME in api_client.cookies
