from __future__ import annotations

import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from config.asgi import application
from houston.realtime.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    default_ws_headers,
    login,
    ws_realtime_path,
    ws_realtime_ticket_url,
)

pytestmark = pytest.mark.django_db

REALTIME_WS_LOGGER = "houston.realtime.consumers"


async def _connect(path: str):
    communicator = WebsocketCommunicator(
        application,
        path,
        headers=default_ws_headers(),
    )
    connected, _ = await communicator.connect()
    assert connected
    return communicator


def test_realtime_ws_auth_success(api_client):
    establishment = create_establishment()
    user = create_user(username="realtime_ws_ok")
    membership = create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)

    ticket_response = api_client.post(
        ws_realtime_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    ticket = ticket_response.json()["ticket"]

    async def run():
        communicator = await _connect(ws_realtime_path(establishment.id))
        await communicator.send_json_to({"type": "auth", "ticket": ticket})
        response = await communicator.receive_json_from()
        assert response["type"] == "auth.ok"
        assert response["membership_id"] == str(membership.id)
        assert response["session_id"]
        await communicator.disconnect()

    async_to_sync(run)()


def test_realtime_ws_auth_rejects_invalid_ticket():
    establishment = create_establishment()

    async def run():
        communicator = await _connect(ws_realtime_path(establishment.id))
        await communicator.send_json_to({"type": "auth", "ticket": "invalid-ticket"})
        response = await communicator.receive_output()
        assert response["type"] == "websocket.close"
        assert response["code"] == 4001
        await communicator.disconnect()

    async_to_sync(run)()


def test_realtime_ws_receives_invalidation_event(api_client):
    from channels.layers import get_channel_layer
    from houston.realtime.groups import establishment_group_name
    from houston.realtime.ws_payloads import build_invalidate_payload

    establishment = create_establishment()
    user = create_user(username="realtime_invalidate")
    membership = create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)
    ticket = api_client.post(
        ws_realtime_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    ).json()["ticket"]
    signal_id = uuid.UUID("00000000-0000-4000-8000-000000000001")

    async def run():
        communicator = await _connect(ws_realtime_path(establishment.id))
        await communicator.send_json_to({"type": "auth", "ticket": ticket})
        auth_response = await communicator.receive_json_from()
        assert auth_response["type"] == "auth.ok"

        channel_layer = get_channel_layer()
        payload = build_invalidate_payload(
            subject_type="signal",
            reason="signal.updated",
            establishment_id=establishment.id,
            entity_id=signal_id,
        )
        await channel_layer.group_send(
            establishment_group_name(establishment_id=establishment.id),
            {"type": "realtime.invalidation", "payload": payload},
        )

        event = await communicator.receive_json_from()
        assert event["type"] == "invalidate"
        assert event["subject_type"] == "signal"
        assert event["reason"] == "signal.updated"
        assert event["entity_id"] == str(signal_id)
        assert event["establishment_id"] == str(establishment.id)
        assert "occurred_at" in event
        assert "body" not in event
        assert membership.id is not None
        await communicator.disconnect()

    async_to_sync(run)()


def test_realtime_ws_receives_access_event(api_client):
    from channels.layers import get_channel_layer
    from houston.realtime.groups import membership_group_name
    from houston.realtime.ws_payloads import build_access_payload

    establishment = create_establishment()
    user = create_user(username="realtime_access")
    membership = create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)
    ticket = api_client.post(
        ws_realtime_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    ).json()["ticket"]

    async def run():
        communicator = await _connect(ws_realtime_path(establishment.id))
        await communicator.send_json_to({"type": "auth", "ticket": ticket})
        auth_response = await communicator.receive_json_from()
        session_id = auth_response["session_id"]

        channel_layer = get_channel_layer()
        payload = build_access_payload(
            reason="membership.updated",
            establishment_id=establishment.id,
            membership_id=membership.id,
        )
        await channel_layer.group_send(
            membership_group_name(
                establishment_id=establishment.id,
                membership_id=membership.id,
            ),
            {"type": "realtime.access", "payload": payload},
        )

        event = await communicator.receive_json_from()
        assert event["type"] == "access"
        assert event["reason"] == "membership.updated"
        assert event["membership_id"] == str(membership.id)
        assert session_id
        await communicator.disconnect()

    async_to_sync(run)()


def test_realtime_ws_receives_membership_invalidation_event(api_client):
    from channels.layers import get_channel_layer
    from houston.realtime.groups import membership_group_name
    from houston.realtime.ws_payloads import build_invalidate_payload

    establishment = create_establishment()
    user = create_user(username="realtime_membership_invalidate")
    membership = create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)
    ticket = api_client.post(
        ws_realtime_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    ).json()["ticket"]
    notification_id = uuid.UUID("00000000-0000-4000-8000-000000000002")

    async def run():
        communicator = await _connect(ws_realtime_path(establishment.id))
        await communicator.send_json_to({"type": "auth", "ticket": ticket})
        auth_response = await communicator.receive_json_from()
        assert auth_response["type"] == "auth.ok"

        channel_layer = get_channel_layer()
        payload = build_invalidate_payload(
            subject_type="notification",
            reason="notification.created",
            establishment_id=establishment.id,
            entity_id=notification_id,
        )
        await channel_layer.group_send(
            membership_group_name(
                establishment_id=establishment.id,
                membership_id=membership.id,
            ),
            {"type": "realtime.invalidation", "payload": payload},
        )

        event = await communicator.receive_json_from()
        assert event["type"] == "invalidate"
        assert event["subject_type"] == "notification"
        assert event["reason"] == "notification.created"
        assert event["entity_id"] == str(notification_id)
        assert event["establishment_id"] == str(establishment.id)
        assert "occurred_at" in event
        assert "title" not in event
        assert "body" not in event
        await communicator.disconnect()

    async_to_sync(run)()


def test_notification_invalidation_isolated_to_target_membership(api_client):
    from channels.layers import get_channel_layer
    from houston.realtime.groups import membership_group_name
    from houston.realtime.ws_payloads import build_invalidate_payload

    establishment = create_establishment()
    user_a = create_user(username="realtime_notif_a")
    user_b = create_user(username="realtime_notif_b")
    membership_a = create_membership(user=user_a, establishment=establishment)
    create_membership(user=user_b, establishment=establishment)
    token_a = login(api_client, user=user_a)
    token_b = login(api_client, user=user_b)
    ticket_a = api_client.post(
        ws_realtime_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token_a}",
    ).json()["ticket"]
    ticket_b = api_client.post(
        ws_realtime_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token_b}",
    ).json()["ticket"]
    notification_id = uuid.UUID("00000000-0000-4000-8000-000000000003")

    async def run():
        communicator_a = await _connect(ws_realtime_path(establishment.id))
        communicator_b = await _connect(ws_realtime_path(establishment.id))

        await communicator_a.send_json_to({"type": "auth", "ticket": ticket_a})
        assert (await communicator_a.receive_json_from())["type"] == "auth.ok"

        await communicator_b.send_json_to({"type": "auth", "ticket": ticket_b})
        assert (await communicator_b.receive_json_from())["type"] == "auth.ok"

        channel_layer = get_channel_layer()
        payload = build_invalidate_payload(
            subject_type="notification",
            reason="notification.created",
            establishment_id=establishment.id,
            entity_id=notification_id,
        )
        await channel_layer.group_send(
            membership_group_name(
                establishment_id=establishment.id,
                membership_id=membership_a.id,
            ),
            {"type": "realtime.invalidation", "payload": payload},
        )

        event = await communicator_a.receive_json_from()
        assert event["type"] == "invalidate"
        assert event["subject_type"] == "notification"
        assert event["entity_id"] == str(notification_id)

        await communicator_b.receive_nothing(timeout=0.2)

        await communicator_a.disconnect()
        await communicator_b.disconnect()

    async_to_sync(run)()
