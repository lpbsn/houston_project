from __future__ import annotations

from channels.testing import WebsocketCommunicator
from config.asgi import application
from houston.chat.tests.conftest import default_ws_headers, login, ws_chat_path, ws_ticket_url


async def _connect(path: str) -> WebsocketCommunicator:
    communicator = WebsocketCommunicator(
        application,
        path,
        headers=default_ws_headers(),
    )
    connected, _ = await communicator.connect()
    assert connected
    return communicator


def get_ws_ticket(api_client, *, user, establishment) -> str:
    token = login(api_client, user=user)
    ticket_response = api_client.post(
        ws_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert ticket_response.status_code == 200
    return ticket_response.json()["ticket"]


async def _connect_authenticated(*, ticket: str, establishment):
    communicator = await _connect(ws_chat_path(establishment.id))
    await communicator.send_json_to({"type": "auth", "ticket": ticket})
    auth_response = await communicator.receive_json_from()
    assert auth_response["type"] == "auth.ok"
    return communicator
