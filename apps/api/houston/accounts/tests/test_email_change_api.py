from __future__ import annotations

from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from houston.accounts.models import EmailChangeRequest, User
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


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


@override_settings(RESEND_API_KEY="re_test_key")
def test_initiate_returns_pending_without_token(api_client, monkeypatch):
    user = create_user(username="email_change_user", email="live@example.com")
    create_membership(user=user, role=EstablishmentMembership.Role.STAFF)
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "secret-token")
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        lambda *args, **kwargs: None,
    )

    access_token = login(api_client, identifier=user.email)
    response = api_client.post(
        "/api/v1/auth/email-change/",
        {"password": TEST_PASSWORD, "new_email": "next@example.com"},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pending_email"] == "next@example.com"
    assert body["expires_at"]
    assert "token" not in body
    assert "secret-token" not in str(body)

    user.refresh_from_db()
    assert user.email == "live@example.com"
    assert EmailChangeRequest.objects.filter(token_digest=digest_token("secret-token")).exists()

    bootstrap = api_client.get("/api/v1/auth/bootstrap/", **auth_headers(access_token))
    assert bootstrap.status_code == 200
    assert bootstrap.json()["user"]["pending_email"] == "next@example.com"
    assert bootstrap.json()["user"]["email"] == "live@example.com"


@override_settings(RESEND_API_KEY="re_test_key")
def test_initiate_wrong_password_is_403(api_client, monkeypatch):
    user = create_user(username="email_change_bad_pw", email="live@example.com")
    create_membership(user=user)
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        lambda *args, **kwargs: None,
    )
    access_token = login(api_client, identifier=user.email)

    response = api_client.post(
        "/api/v1/auth/email-change/",
        {"password": "not-the-password", "new_email": "next@example.com"},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "invalid_credentials"
    assert EmailChangeRequest.objects.count() == 0


@override_settings(RESEND_API_KEY="re_test_key")
def test_initiate_duplicate_is_409(api_client, monkeypatch):
    create_user(username="taken_email", email="taken@example.com")
    user = create_user(username="email_change_dup", email="live@example.com")
    create_membership(user=user)
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        lambda *args, **kwargs: None,
    )
    access_token = login(api_client, identifier=user.email)

    response = api_client.post(
        "/api/v1/auth/email-change/",
        {"password": TEST_PASSWORD, "new_email": "taken@example.com"},
        format="json",
        **auth_headers(access_token),
    )

    assert response.status_code == 409
    assert response.json()["code"] == "email_change_duplicate"


@override_settings(RESEND_API_KEY="re_test_key")
def test_confirm_is_public_and_does_not_issue_session(api_client, monkeypatch):
    user = create_user(username="email_change_confirm", email="live@example.com")
    create_membership(user=user)
    monkeypatch.setattr("houston.accounts.tokens.generate_raw_token", lambda: "public-token")
    monkeypatch.setattr(
        "houston.accounts.email_change_services._enqueue_email_change_email",
        lambda *args, **kwargs: None,
    )
    access_token = login(api_client, identifier=user.email)
    start = api_client.post(
        "/api/v1/auth/email-change/",
        {"password": TEST_PASSWORD, "new_email": "next@example.com"},
        format="json",
        **auth_headers(access_token),
    )
    assert start.status_code == 200

    confirm = api_client.post(
        "/api/v1/auth/email-change/confirm/",
        {"token": "public-token"},
        format="json",
    )
    assert confirm.status_code == 200
    assert confirm.json() == {"email": "next@example.com"}
    assert "access_token" not in confirm.json()

    user.refresh_from_db()
    assert user.email == "next@example.com"

    stale = api_client.post(
        "/api/v1/auth/email-change/confirm/",
        {"token": "public-token"},
        format="json",
    )
    assert stale.status_code == 400
    assert stale.json()["code"] == "email_change_invalid"


def test_confirm_unknown_token_is_generic(api_client):
    response = api_client.post(
        "/api/v1/auth/email-change/confirm/",
        {"token": "no-such-token"},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "email_change_invalid"
    assert User.objects.filter(email="no-such-token").count() == 0
