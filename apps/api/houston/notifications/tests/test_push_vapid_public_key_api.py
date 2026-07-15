from __future__ import annotations

import pytest
from django.test import override_settings

from houston.notifications.tests.conftest import vapid_public_key_url
from houston.notifications.tests.vapid_constants import TEST_PRIVATE_KEY, TEST_PUBLIC_KEY

pytestmark = pytest.mark.django_db


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
