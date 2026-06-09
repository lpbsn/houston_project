from __future__ import annotations

import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from config.asgi import application
from django.db import close_old_connections
from houston.chat.services import remove_group_participant
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    default_ws_headers,
    get_ws_ticket,
    login,
)
from houston.chat.tests.test_rest_api import create_group


async def _connect_authenticated(*, ticket: str, establishment):
    communicator = WebsocketCommunicator(
        application,
        f"/ws/v1/establishments/{establishment.id}/chat/",
        headers=default_ws_headers(),
    )
    connected, _ = await communicator.connect()
    assert connected
    await communicator.send_json_to({"type": "auth", "ticket": ticket})
    auth_event = await communicator.receive_json_from()
    assert auth_event["type"] == "auth.ok"
    return communicator


@pytest.mark.django_db(transaction=True)
def test_ws_emits_access_revoked_when_participant_is_removed(api_client):
    establishment = create_establishment()
    admin = create_user(username="chat_ws_revoke_admin")
    target = create_user(username="chat_ws_revoke_target")
    admin_membership = create_membership(
        user=admin,
        establishment=establishment,
        role="manager",
    )
    target_membership = create_membership(user=target, establishment=establishment)
    admin_token = login(api_client, user=admin)

    group_response = create_group(
        api_client,
        token=admin_token,
        establishment_id=establishment.id,
        title="Revoke me",
        membership_ids=[target_membership.id],
    )
    conversation_id = group_response.json()["conversation"]["id"]
    target_ticket = get_ws_ticket(api_client, user=target, establishment=establishment)

    async def run():
        target_comm = await _connect_authenticated(
            ticket=target_ticket,
            establishment=establishment,
        )
        await database_sync_to_async(remove_group_participant)(
            actor_membership=admin_membership,
            conversation_id=uuid.UUID(conversation_id),
            target_membership_id=target_membership.id,
        )
        event = await target_comm.receive_json_from()
        await target_comm.disconnect()
        return event

    event = async_to_sync(run)()
    close_old_connections()

    assert event["type"] == "conversation.access_revoked"
    assert event["conversation_id"] == conversation_id
    assert event["reason"] == "participant_removed"


@pytest.mark.django_db(transaction=True)
def test_ws_smoke_supports_multiple_authenticated_connections(api_client):
    establishment = create_establishment()
    users = [create_user(username=f"chat_ws_smoke_{index}") for index in range(5)]
    memberships = [create_membership(user=user, establishment=establishment) for user in users]
    tickets = [get_ws_ticket(api_client, user=user, establishment=establishment) for user in users]

    async def run():
        communicators = []
        for ticket in tickets:
            communicator = await _connect_authenticated(ticket=ticket, establishment=establishment)
            communicators.append(communicator)
        assert len(communicators) == len(memberships)
        for communicator in communicators:
            await communicator.disconnect()

    async_to_sync(run)()
    close_old_connections()
