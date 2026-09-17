from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from houston.accounts.models import PasswordResetRequest, User, UserSession
from houston.accounts.password_services import PASSWORD_RESET_REQUEST_DETAIL
from houston.accounts.tokens import digest_token
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.membership_api_helpers import (
    auth_headers,
    create_membership,
    create_user,
    login,
)
from houston.testing.factories import TEST_PASSWORD

pytestmark = pytest.mark.django_db

NEW_PASSWORD = "AnotherSecurePass456!"


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def test_password_change_keeps_current_session(api_client):
    user = create_user(username="pw_change_user", email="live@example.com")
    create_membership(user=user, role=EstablishmentMembership.Role.STAFF)
    access_token = login(api_client, identifier=user.email)
    other_client = APIClient(enforce_csrf_checks=True)
    other_token = login(other_client, identifier=user.email)

    response = api_client.post(
        "/api/v1/auth/password-change/",
        {
            "current_password": TEST_PASSWORD,
            "password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        },
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 204
    bootstrap = api_client.get("/api/v1/auth/bootstrap/", **auth_headers(access_token))
    assert bootstrap.status_code == 200

    stale = other_client.get("/api/v1/auth/bootstrap/", **auth_headers(other_token))
    assert stale.status_code == 401

    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert (
        UserSession.objects.filter(user=user, status=UserSession.Status.ACTIVE).count() == 1
    )


def test_password_change_wrong_password_is_403(api_client):
    user = create_user(username="pw_change_bad", email="bad@example.com")
    create_membership(user=user)
    access_token = login(api_client, identifier=user.email)

    response = api_client.post(
        "/api/v1/auth/password-change/",
        {
            "current_password": "not-the-password",
            "password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        },
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "invalid_credentials"
    user.refresh_from_db()
    assert user.check_password(TEST_PASSWORD)


@override_settings(RESEND_API_KEY="re_test_key")
def test_password_reset_request_is_opaque(api_client, monkeypatch):
    create_user(username="reset_user", email="live@example.com")
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        lambda *args, **kwargs: None,
    )

    known = api_client.post(
        "/api/v1/auth/password-reset/",
        {"email": "live@example.com"},
        format="json",
    )
    unknown = api_client.post(
        "/api/v1/auth/password-reset/",
        {"email": "missing@example.com"},
        format="json",
    )

    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json() == {"detail": PASSWORD_RESET_REQUEST_DETAIL}
    assert "token" not in known.json()
    assert "expires_at" not in known.json()


@override_settings(RESEND_API_KEY="")
def test_password_reset_request_without_resend_is_503(api_client):
    response = api_client.post(
        "/api/v1/auth/password-reset/",
        {"email": "anyone@example.com"},
        format="json",
    )
    assert response.status_code == 503
    assert response.json()["code"] == "password_reset_unavailable"
    assert PasswordResetRequest.objects.count() == 0


@override_settings(RESEND_API_KEY="re_test_key")
def test_password_reset_confirm_is_public_and_does_not_issue_session(api_client, monkeypatch):
    user = create_user(username="reset_confirm", email="live@example.com")
    create_membership(user=user)
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "public-reset")
    monkeypatch.setattr(
        "houston.accounts.password_services._enqueue_password_reset_email",
        lambda *args, **kwargs: None,
    )
    start = api_client.post(
        "/api/v1/auth/password-reset/",
        {"email": user.email},
        format="json",
    )
    assert start.status_code == 200

    confirm = api_client.post(
        "/api/v1/auth/password-reset/confirm/",
        {
            "token": "public-reset",
            "password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        },
        format="json",
    )
    assert confirm.status_code == 200
    assert "access_token" not in confirm.json()
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)

    stale = api_client.post(
        "/api/v1/auth/password-reset/confirm/",
        {
            "token": "public-reset",
            "password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        },
        format="json",
    )
    assert stale.status_code == 400
    assert stale.json()["code"] == "password_reset_invalid"


def test_password_reset_confirm_unknown_token_is_generic(api_client):
    response = api_client.post(
        "/api/v1/auth/password-reset/confirm/",
        {
            "token": "no-such-token",
            "password": NEW_PASSWORD,
            "password_confirmation": NEW_PASSWORD,
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "password_reset_invalid"
    assert User.objects.filter(email="no-such-token").count() == 0
