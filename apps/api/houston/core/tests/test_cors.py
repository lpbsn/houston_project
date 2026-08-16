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
