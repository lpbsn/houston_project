from __future__ import annotations

import logging

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

pytestmark = pytest.mark.django_db

CHAT_WS_LOGGER = "houston.chat.consumers"


def _assert_chat_ws_auth_failed_log(
    caplog: pytest.LogCaptureFixture,
    *,
    establishment_id,
    reason: str,
    close_code: int,
    distinctive_secret: str | None = None,
) -> None:
    records = [record for record in caplog.records if record.getMessage() == "chat_ws_auth_failed"]
    assert records, "expected chat_ws_auth_failed log record"
    record = records[-1]
    assert getattr(record, "ws_auth_failure_reason", None) == reason
    assert getattr(record, "establishment_id", None) == str(establishment_id)
    assert getattr(record, "ws_close_code", None) == close_code
    assert "session_id" not in record.__dict__
    assert "token" not in record.__dict__
    if distinctive_secret is not None:
        serialized = str(record.__dict__)
        assert distinctive_secret not in serialized
        assert distinctive_secret not in record.getMessage()


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


def test_ws_auth_invalid_ticket_logs_safe_context_without_ticket_value(caplog):
    establishment = create_establishment()
    distinctive_ticket = "DISTINCTIVE-FAKE-TICKET-phase-f-abc123xyz"

    with caplog.at_level(logging.WARNING, logger=CHAT_WS_LOGGER):

        async def run():
            communicator = await _connect(ws_chat_path(establishment.id))
            await communicator.send_json_to({"type": "auth", "ticket": distinctive_ticket})
            response = await communicator.receive_output()
            assert response["type"] == "websocket.close"
            assert response["code"] == 4001
            await communicator.disconnect()

        async_to_sync(run)()

    _assert_chat_ws_auth_failed_log(
        caplog,
        establishment_id=establishment.id,
        reason="invalid_ticket",
        close_code=4001,
        distinctive_secret=distinctive_ticket,
    )


def test_ws_auth_missing_ticket_logs_safe_context(caplog):
    establishment = create_establishment()

    with caplog.at_level(logging.WARNING, logger=CHAT_WS_LOGGER):

        async def run():
            communicator = await _connect(ws_chat_path(establishment.id))
            await communicator.send_json_to({"type": "auth", "ticket": ""})
            response = await communicator.receive_output()
            assert response["type"] == "websocket.close"
            assert response["code"] == 4001
            await communicator.disconnect()

        async_to_sync(run)()

    _assert_chat_ws_auth_failed_log(
        caplog,
        establishment_id=establishment.id,
        reason="missing_ticket",
        close_code=4001,
    )


def test_ws_auth_rejects_replayed_ticket(api_client):
    establishment = create_establishment()
    user = create_user(username="chat_ws_replay")
    create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)

    ticket_response = api_client.post(
        ws_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    ticket = ticket_response.json()["ticket"]

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
