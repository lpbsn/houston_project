from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import PushDevice
from houston.notifications.tests.conftest import push_device_revoke_url, push_devices_url
from houston.testing.auth import auth_headers, build_api_membership, login

pytestmark = pytest.mark.django_db

DEVICE_PAYLOAD = {
    "token": "fcm-token-abc123",
    "platform": "ios",
}


def test_upsert_push_device_creates_device(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=recipient.user)

    response = api_client.post(
        push_devices_url(),
        DEVICE_PAYLOAD,
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["platform"] == "ios"
    assert "token" not in payload
    assert PushDevice.objects.filter(user=recipient.user).count() == 1


def test_upsert_push_device_is_idempotent_for_same_token(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=recipient.user)

    first = api_client.post(
        push_devices_url(),
        DEVICE_PAYLOAD,
        format="json",
        **auth_headers(token),
    )
    second = api_client.post(
        push_devices_url(),
        {**DEVICE_PAYLOAD, "platform": "android"},
        format="json",
        **auth_headers(token),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert PushDevice.objects.filter(token=DEVICE_PAYLOAD["token"]).count() == 1

    device = PushDevice.objects.get(token=DEVICE_PAYLOAD["token"])
    assert device.platform == "android"
    assert device.revoked_at is None


def test_upsert_push_device_transfers_ownership_from_other_user(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    owner_token = login(api_client, user=owner.user)
    outsider_token = login(api_client, user=outsider.user)

    first = api_client.post(
        push_devices_url(),
        DEVICE_PAYLOAD,
        format="json",
        **auth_headers(owner_token),
    )
    assert first.status_code == 200

    second = api_client.post(
        push_devices_url(),
        DEVICE_PAYLOAD,
        format="json",
        **auth_headers(outsider_token),
    )

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    device = PushDevice.objects.get(token=DEVICE_PAYLOAD["token"])
    assert device.user_id == outsider.user_id
    assert (
        PushDevice.objects.filter(
            token=DEVICE_PAYLOAD["token"],
            revoked_at__isnull=True,
        ).count()
        == 1
    )


def test_revoke_push_device_soft_revokes(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=recipient.user)

    create_response = api_client.post(
        push_devices_url(),
        DEVICE_PAYLOAD,
        format="json",
        **auth_headers(token),
    )
    device_id = create_response.json()["id"]

    revoke_response = api_client.delete(
        push_device_revoke_url(device_id),
        **auth_headers(token),
    )

    assert revoke_response.status_code == 204
    device = PushDevice.objects.get(pk=device_id)
    assert device.revoked_at is not None


def test_device_endpoints_require_authentication(api_client):
    create_response = api_client.post(
        push_devices_url(),
        DEVICE_PAYLOAD,
        format="json",
    )
    assert create_response.status_code == 401


def test_user_cannot_revoke_other_users_device(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    owner_token = login(api_client, user=owner.user)
    outsider_token = login(api_client, user=outsider.user)

    create_response = api_client.post(
        push_devices_url(),
        DEVICE_PAYLOAD,
        format="json",
        **auth_headers(owner_token),
    )
    device_id = create_response.json()["id"]

    response = api_client.delete(
        push_device_revoke_url(device_id),
        **auth_headers(outsider_token),
    )

    assert response.status_code == 404
