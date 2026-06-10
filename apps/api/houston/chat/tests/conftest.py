from __future__ import annotations

import pytest
from houston.testing.auth import login
from houston.testing.factories import (
    TEST_PASSWORD,
    create_establishment,
    create_membership,
    create_user,
)
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

__all__ = [
    "TEST_PASSWORD",
    "api_client",
    "create_establishment",
    "create_membership",
    "create_user",
    "default_ws_headers",
    "get_ws_ticket",
    "login",
    "ws_chat_path",
    "ws_ticket_url",
]


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def ws_ticket_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/chat/ws-ticket/"


def ws_chat_path(establishment_id) -> str:
    return f"/ws/v1/establishments/{establishment_id}/chat/"


def get_ws_ticket(api_client, *, user, establishment) -> str:
    token = login(api_client, user=user)
    response = api_client.post(
        ws_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 200
    return response.json()["ticket"]


def default_ws_headers() -> list[tuple[bytes, bytes]]:
    return [
        (b"host", b"localhost"),
        (b"origin", b"http://localhost"),
    ]
