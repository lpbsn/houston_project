from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import WebPushSubscription
from houston.notifications.tests.conftest import (
    web_push_subscription_revoke_url,
    web_push_subscriptions_url,
)
from houston.testing.auth import auth_headers, build_api_membership, login

pytestmark = pytest.mark.django_db

SUBSCRIPTION_PAYLOAD = {
    "endpoint": "https://push.example.com/device/abc123",
    "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8uFXiq1",
    "auth": "tBHItJI5svbpez7KI4CCXg",
    "user_agent": "pytest",
}


def test_upsert_web_push_subscription_creates_subscription(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=recipient.user)

    response = api_client.post(
        web_push_subscriptions_url(),
        SUBSCRIPTION_PAYLOAD,
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["endpoint"] == SUBSCRIPTION_PAYLOAD["endpoint"]
    assert "p256dh" not in payload
    assert "auth" not in payload
    assert WebPushSubscription.objects.filter(user=recipient.user).count() == 1


def test_upsert_web_push_subscription_is_idempotent_for_same_endpoint(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=recipient.user)

    first = api_client.post(
        web_push_subscriptions_url(),
        SUBSCRIPTION_PAYLOAD,
        format="json",
        **auth_headers(token),
    )
    updated_payload = {
        **SUBSCRIPTION_PAYLOAD,
        "p256dh": "updated-p256dh-key",
        "auth": "updated-auth-key",
    }
    second = api_client.post(
        web_push_subscriptions_url(),
        updated_payload,
        format="json",
        **auth_headers(token),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    endpoint = SUBSCRIPTION_PAYLOAD["endpoint"]
    assert WebPushSubscription.objects.filter(endpoint=endpoint).count() == 1

    subscription = WebPushSubscription.objects.get(endpoint=endpoint)
    assert subscription.p256dh == "updated-p256dh-key"
    assert subscription.auth == "updated-auth-key"
    assert subscription.revoked_at is None


def test_upsert_web_push_subscription_rejects_other_user_endpoint(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    owner_token = login(api_client, user=owner.user)
    outsider_token = login(api_client, user=outsider.user)

    first = api_client.post(
        web_push_subscriptions_url(),
        SUBSCRIPTION_PAYLOAD,
        format="json",
        **auth_headers(owner_token),
    )
    assert first.status_code == 200

    second = api_client.post(
        web_push_subscriptions_url(),
        SUBSCRIPTION_PAYLOAD,
        format="json",
        **auth_headers(outsider_token),
    )

    assert second.status_code == 400


def test_revoke_web_push_subscription_soft_revokes(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=recipient.user)

    create_response = api_client.post(
        web_push_subscriptions_url(),
        SUBSCRIPTION_PAYLOAD,
        format="json",
        **auth_headers(token),
    )
    subscription_id = create_response.json()["id"]

    revoke_response = api_client.delete(
        web_push_subscription_revoke_url(subscription_id),
        **auth_headers(token),
    )

    assert revoke_response.status_code == 204
    subscription = WebPushSubscription.objects.get(pk=subscription_id)
    assert subscription.revoked_at is not None


def test_subscription_endpoints_require_authentication(api_client):
    create_response = api_client.post(
        web_push_subscriptions_url(),
        SUBSCRIPTION_PAYLOAD,
        format="json",
    )
    assert create_response.status_code == 401


def test_user_cannot_revoke_other_users_subscription(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    owner_token = login(api_client, user=owner.user)
    outsider_token = login(api_client, user=outsider.user)

    create_response = api_client.post(
        web_push_subscriptions_url(),
        SUBSCRIPTION_PAYLOAD,
        format="json",
        **auth_headers(owner_token),
    )
    subscription_id = create_response.json()["id"]

    response = api_client.delete(
        web_push_subscription_revoke_url(subscription_id),
        **auth_headers(outsider_token),
    )

    assert response.status_code == 404
