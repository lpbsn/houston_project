from __future__ import annotations

import pytest
from django.test import override_settings

from houston.notifications.tests.conftest import vapid_public_key_url

pytestmark = pytest.mark.django_db

TEST_PUBLIC_KEY = (
    "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U"
)
TEST_PRIVATE_KEY = "UUxI4O8-FbRouAevSmBQ6o18hgE4nSG3qwvJTfKc-ls"


@override_settings(
    HOUSTON_VAPID_PUBLIC_KEY=TEST_PUBLIC_KEY,
    HOUSTON_VAPID_PRIVATE_KEY=TEST_PRIVATE_KEY,
)
def test_vapid_public_key_returns_public_key_only(api_client):
    response = api_client.get(vapid_public_key_url())

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"public_key": TEST_PUBLIC_KEY}
    assert TEST_PRIVATE_KEY not in str(payload)


@override_settings(HOUSTON_VAPID_PUBLIC_KEY="")
def test_vapid_public_key_returns_service_unavailable_when_not_configured(api_client):
    response = api_client.get(vapid_public_key_url())

    assert response.status_code == 503


@override_settings(
    HOUSTON_VAPID_PUBLIC_KEY=TEST_PUBLIC_KEY,
    HOUSTON_VAPID_PRIVATE_KEY=TEST_PRIVATE_KEY,
)
def test_vapid_public_key_does_not_require_authentication(api_client):
    response = api_client.get(vapid_public_key_url())

    assert response.status_code == 200
