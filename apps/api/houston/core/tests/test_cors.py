from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from config.settings import HOUSTON_NATIVE_WEBVIEW_ORIGINS

pytestmark = pytest.mark.django_db

_ALLOWED_ORIGIN = "http://localhost:5173"
_UNKNOWN_ORIGIN = "http://evil.example"


@pytest.fixture
def api_client():
    return APIClient()


def test_cors_allows_configured_client_origin(api_client):
    response = api_client.get("/api/v1/auth/csrf/", HTTP_ORIGIN=_ALLOWED_ORIGIN)

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"


def test_cors_does_not_echo_unknown_origin(api_client):
    response = api_client.get("/api/v1/auth/csrf/", HTTP_ORIGIN=_UNKNOWN_ORIGIN)

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_allows_native_webview_origins(api_client, settings):
    native_origins = sorted(HOUSTON_NATIVE_WEBVIEW_ORIGINS)
    settings.HOUSTON_CLIENT_ORIGINS = native_origins
    settings.CORS_ALLOWED_ORIGINS = native_origins

    for origin in native_origins:
        response = api_client.get("/api/v1/auth/csrf/", HTTP_ORIGIN=origin)

        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == origin


def test_cors_preflight_allows_authorization_from_native_webview_origin(api_client, settings):
    native_origin = sorted(HOUSTON_NATIVE_WEBVIEW_ORIGINS)[0]
    settings.HOUSTON_CLIENT_ORIGINS = [native_origin]
    settings.CORS_ALLOWED_ORIGINS = [native_origin]

    response = api_client.options(
        "/api/v1/auth/login/",
        HTTP_ORIGIN=native_origin,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization",
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == native_origin


def test_cors_preflight_allows_application_headers_for_configured_origin(api_client):
    response = api_client.options(
        "/api/v1/auth/login/",
        HTTP_ORIGIN=_ALLOWED_ORIGIN,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization, x-csrftoken",
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == _ALLOWED_ORIGIN
    assert response.headers["Access-Control-Allow-Credentials"] == "true"

    allowed_methods = {
        method.strip().upper()
        for method in response.headers["Access-Control-Allow-Methods"].split(",")
    }
    assert "POST" in allowed_methods

    allowed_headers = {
        header.strip().lower()
        for header in response.headers["Access-Control-Allow-Headers"].split(",")
    }
    assert {"authorization", "x-csrftoken"} <= allowed_headers
