from __future__ import annotations

import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from config.asgi import application
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    default_ws_headers,
    login,
    ws_chat_path,
    ws_ticket_url,
)
from houston.chat.ws_ticket import issue_ws_ticket

pytestmark = pytest.mark.django_db


async def _connect(path: str):
    communicator = WebsocketCommunicator(
        application,
        path,
        headers=default_ws_headers(),
    )
    connected, _ = await communicator.connect()
    assert connected
    return communicator


def test_ws_auth_success(api_client):
    establishment = create_establishment()
    user = create_user(username="chat_ws_ok")
    membership = create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)

    ticket_response = api_client.post(
        ws_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    ticket = ticket_response.json()["ticket"]

    async def run():
        communicator = await _connect(ws_chat_path(establishment.id))
        await communicator.send_json_to({"type": "auth", "ticket": ticket})
        response = await communicator.receive_json_from()
        assert response["type"] == "auth.ok"
        assert response["user_id"] == str(user.id)
        assert response["membership_id"] == str(membership.id)
        assert response["session_id"]
        await communicator.disconnect()

    async_to_sync(run)()


def test_ws_auth_rejects_invalid_ticket():
    establishment = create_establishment()

    async def run():
        communicator = await _connect(ws_chat_path(establishment.id))
        await communicator.send_json_to({"type": "auth", "ticket": "invalid-ticket"})
        response = await communicator.receive_output()
        assert response["type"] == "websocket.close"
        assert response["code"] == 4001
        await communicator.disconnect()

    async_to_sync(run)()


def test_ws_auth_rejects_replayed_ticket():
    establishment = create_establishment()
    user = create_user(username="chat_ws_replay")
    membership = create_membership(user=user, establishment=establishment)
    session_id = uuid.uuid4()
    ticket, _ = issue_ws_ticket(membership=membership, session_id=session_id)

    async def first_auth():
        communicator = await _connect(ws_chat_path(establishment.id))
        await communicator.send_json_to({"type": "auth", "ticket": ticket})
        response = await communicator.receive_json_from()
        assert response["type"] == "auth.ok"
        await communicator.disconnect()

    async_to_sync(first_auth)()

    async def replay():
        communicator = await _connect(ws_chat_path(establishment.id))
        await communicator.send_json_to({"type": "auth", "ticket": ticket})
        response = await communicator.receive_output()
        assert response["type"] == "websocket.close"
        assert response["code"] == 4001
        await communicator.disconnect()

    async_to_sync(replay)()


def test_ws_auth_timeout(settings):
    settings.HOUSTON_CHAT_WS_AUTH_TIMEOUT_SECONDS = 1
    establishment = create_establishment()

    async def run():
        communicator = await _connect(ws_chat_path(establishment.id))
        response = await communicator.receive_output(timeout=2)
        assert response["type"] == "websocket.close"
        assert response["code"] == 4408
        await communicator.disconnect()

    async_to_sync(run)()


def test_ws_rejects_invalid_origin():
    establishment = create_establishment()

    async def run():
        communicator = WebsocketCommunicator(
            application,
            ws_chat_path(establishment.id),
            headers=[
                (b"host", b"localhost"),
                (b"origin", b"http://evil.example"),
            ],
        )
        connected, _ = await communicator.connect()
        assert not connected
        await communicator.disconnect()

    async_to_sync(run)()


def test_ws_wrong_establishment_ticket(api_client):
    first = create_establishment()
    second = create_establishment()
    user = create_user(username="chat_ws_wrong_est")
    create_membership(user=user, establishment=first)
    token = login(api_client, user=user)

    ticket_response = api_client.post(
        ws_ticket_url(first.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    ticket = ticket_response.json()["ticket"]

    async def run():
        communicator = await _connect(ws_chat_path(second.id))
        await communicator.send_json_to({"type": "auth", "ticket": ticket})
        response = await communicator.receive_output()
        assert response["type"] == "websocket.close"
        assert response["code"] == 4001
        await communicator.disconnect()

    async_to_sync(run)()
