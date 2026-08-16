from __future__ import annotations

import pytest
from rest_framework.test import APIClient

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
