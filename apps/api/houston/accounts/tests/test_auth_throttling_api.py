from __future__ import annotations

import copy
import uuid

import pytest
import rest_framework.throttling as drf_throttling
from django.conf import settings
from django.core.cache import caches
from django.test import override_settings
from rest_framework.settings import api_settings as drf_api_settings
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.accounts.tests.test_auth_api import (
    create_membership,
    ensure_csrf,
    login,
)
from houston.accounts.tests.test_registration_api import (
    owner_validate_payload,
    registration_payload,
)

pytestmark = [pytest.mark.django_db, pytest.mark.auth_throttle]


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def active_user():
    return User.objects.create_user(
        username="throttle_manager",
        email="throttle.manager@example.com",
        password="secret",
        status=User.Status.ACTIVE,
    )


THROTTLE_TEST_RATES = {
    "auth_login": "2/minute",
    "auth_refresh": "3/minute",
    "auth_register": "2/hour",
    "auth_register_validate": "2/hour",
    "auth_invitation_accept": "2/hour",
}


def _clear_default_cache() -> None:
    caches["default"].clear()


@pytest.fixture(autouse=True)
def isolated_auth_throttle_settings(monkeypatch):
    rest_framework = copy.deepcopy(settings.REST_FRAMEWORK)
    rest_framework["DEFAULT_THROTTLE_RATES"] = dict(THROTTLE_TEST_RATES)
    rest_framework["NUM_PROXIES"] = 1
    throttle_caches = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": f"auth-throttle-tests-{uuid.uuid4()}",
        }
    }
    monkeypatch.setattr(
        drf_throttling.SimpleRateThrottle,
        "THROTTLE_RATES",
        dict(THROTTLE_TEST_RATES),
    )
    with override_settings(
        CACHES=throttle_caches,
        REST_FRAMEWORK=rest_framework,
        HOUSTON_AUTH_THROTTLE_ENABLED=True,
    ):
        drf_api_settings.reload()
        _clear_default_cache()
        assert drf_api_settings.DEFAULT_THROTTLE_RATES["auth_login"] == "2/minute"
        yield
        _clear_default_cache()


def assert_throttled_response(response) -> None:
    assert response.status_code == 429
    body = response.json()
    assert body["code"] == "throttled"
    assert body["detail"].startswith("Request was throttled")


def _client_ip_headers(ip: str) -> dict:
    return {"HTTP_X_FORWARDED_FOR": ip}


def test_login_under_limit_returns_200(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)

    response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
        **_client_ip_headers("203.0.113.10"),
    )

    assert response.status_code == 200
    assert response.json()["authenticated"] is True


def test_login_over_limit_returns_429(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    ip_headers = _client_ip_headers("203.0.113.11")

    for _ in range(2):
        response = login(
            api_client,
            csrf_token,
            identifier=active_user.email,
            password="secret",
            **ip_headers,
        )
        assert response.status_code == 200

    response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
        **ip_headers,
    )
    assert_throttled_response(response)


def test_login_throttled_unknown_identifier_same_shape(api_client, active_user):
    csrf_token = ensure_csrf(api_client)
    ip_headers = _client_ip_headers("203.0.113.12")

    for _ in range(2):
        login(
            api_client,
            csrf_token,
            identifier="nobody@example.com",
            password="wrong-password",
            **ip_headers,
        )

    unknown_response = login(
        api_client,
        csrf_token,
        identifier="nobody@example.com",
        password="wrong-password",
        **ip_headers,
    )
    assert_throttled_response(unknown_response)

    create_membership(user=active_user)
    known_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
        **ip_headers,
    )
    assert_throttled_response(known_response)
    assert unknown_response.json()["code"] == known_response.json()["code"]
    assert unknown_response.json()["detail"].startswith(known_response.json()["detail"][:26])


def test_refresh_under_limit_returns_200(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    ip_headers = _client_ip_headers("203.0.113.20")

    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
        **ip_headers,
    )
    assert login_response.status_code == 200

    refresh_response = api_client.post(
        "/api/v1/auth/refresh/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **ip_headers,
    )
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]


def test_refresh_over_limit_returns_429(api_client, active_user):
    create_membership(user=active_user)
    csrf_token = ensure_csrf(api_client)
    ip_headers = _client_ip_headers("203.0.113.21")

    login_response = login(
        api_client,
        csrf_token,
        identifier=active_user.email,
        password="secret",
        **ip_headers,
    )
    assert login_response.status_code == 200

    for _ in range(3):
        response = api_client.post(
            "/api/v1/auth/refresh/",
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
            **ip_headers,
        )
        assert response.status_code == 200

    response = api_client.post(
        "/api/v1/auth/refresh/",
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **ip_headers,
    )
    assert_throttled_response(response)


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_register_over_limit_returns_429(api_client):
    csrf_token = ensure_csrf(api_client)
    ip_headers = _client_ip_headers("203.0.113.30")
    payload = registration_payload(email="throttle.register@example.com")

    for index in range(2):
        response = api_client.post(
            "/api/v1/auth/register/",
            registration_payload(email=f"throttle.register.{index}@example.com"),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
            **ip_headers,
        )
        assert response.status_code == 201

    response = api_client.post(
        "/api/v1/auth/register/",
        payload,
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **ip_headers,
    )
    assert_throttled_response(response)


@override_settings(HOUSTON_REGISTRATION_INVITE_CODES=["valid-code"])
def test_validate_owner_over_limit_returns_429(api_client):
    csrf_token = ensure_csrf(api_client)
    ip_headers = _client_ip_headers("203.0.113.31")

    for index in range(2):
        response = api_client.post(
            "/api/v1/auth/register/validate-owner/",
            owner_validate_payload(email=f"validate.owner.{index}@example.com"),
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
            **ip_headers,
        )
        assert response.status_code == 204

    response = api_client.post(
        "/api/v1/auth/register/validate-owner/",
        owner_validate_payload(email="validate.owner.limit@example.com"),
        format="json",
        HTTP_X_CSRFTOKEN=csrf_token,
        **ip_headers,
    )
    assert_throttled_response(response)
