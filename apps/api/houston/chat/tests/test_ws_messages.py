from __future__ import annotations

import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from config.asgi import application
from django.db import close_old_connections
from houston.chat.models import ChatMessage
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    default_ws_headers,
    login,
    ws_chat_path,
    ws_ticket_url,
)
from houston.chat.tests.test_rest_api import create_dm

pytestmark = pytest.mark.django_db(transaction=True)


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


def test_ws_message_send_broadcasts_to_dm_participants(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_ws_sender")
    receiver = create_user(username="chat_ws_receiver")
    create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    token = login(api_client, user=sender)

    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    conversation_id = dm_response.json()["conversation"]["id"]
    client_message_id = uuid.uuid4()
    sender_ticket = get_ws_ticket(api_client, user=sender, establishment=establishment)
    receiver_ticket = get_ws_ticket(api_client, user=receiver, establishment=establishment)

    async def run():
        sender_comm = await _connect_authenticated(
            ticket=sender_ticket,
            establishment=establishment,
        )
        receiver_comm = await _connect_authenticated(
            ticket=receiver_ticket,
            establishment=establishment,
        )

        await sender_comm.send_json_to(
            {
                "type": "message.send",
                "conversation_id": conversation_id,
                "client_message_id": str(client_message_id),
                "body": "  hello ws  ",
            }
        )

        sender_event = await sender_comm.receive_json_from()
        receiver_event = await receiver_comm.receive_json_from()

        await sender_comm.disconnect()
        await receiver_comm.disconnect()
        return sender_event, receiver_event

    sender_event, receiver_event = async_to_sync(run)()
    close_old_connections()

    assert sender_event["type"] == "message.created"
    assert receiver_event["type"] == "message.created"
    assert sender_event["conversation_id"] == conversation_id
    assert sender_event["message"]["body"] == "hello ws"
    assert sender_event["message"]["client_message_id"] == str(client_message_id)
    assert sender_event["message"]["id"] == receiver_event["message"]["id"]
    assert ChatMessage.objects.filter(conversation_id=conversation_id).count() == 1


def test_ws_delivers_first_message_for_new_dm_without_reconnect(api_client):
    establishment = create_establishment()
    connected_user = create_user(username="chat_ws_connected")
    peer = create_user(username="chat_ws_peer")
    connected_membership = create_membership(user=connected_user, establishment=establishment)
    create_membership(user=peer, establishment=establishment)
    client_message_id = uuid.uuid4()

    connected_ticket = get_ws_ticket(
        api_client,
        user=connected_user,
        establishment=establishment,
    )
    peer_token = login(api_client, user=peer)
    dm_response = create_dm(
        api_client,
        token=peer_token,
        establishment_id=establishment.id,
        target_membership_id=connected_membership.id,
    )
    conversation_id = dm_response.json()["conversation"]["id"]
    peer_ticket = get_ws_ticket(api_client, user=peer, establishment=establishment)

    async def run():
        connected_comm = await _connect_authenticated(
            ticket=connected_ticket,
            establishment=establishment,
        )
        peer_comm = await _connect_authenticated(ticket=peer_ticket, establishment=establishment)
        await peer_comm.send_json_to(
            {
                "type": "message.send",
                "conversation_id": conversation_id,
                "client_message_id": str(client_message_id),
                "body": "first message on new dm",
            }
        )

        peer_event = await peer_comm.receive_json_from()
        connected_event = await connected_comm.receive_json_from()

        assert peer_event["type"] == "message.created"
        assert connected_event["type"] == "message.created"
        assert connected_event["message"]["body"] == "first message on new dm"

        await connected_comm.disconnect()
        await peer_comm.disconnect()
        return peer_event, connected_event

    peer_event, connected_event = async_to_sync(run)()
    close_old_connections()

    assert peer_event["type"] == "message.created"
    assert connected_event["type"] == "message.created"
    assert connected_event["message"]["body"] == "first message on new dm"


def test_ws_message_send_rejects_non_participant(api_client):
    establishment = create_establishment()
    first = create_user(username="chat_ws_participant_a")
    second = create_user(username="chat_ws_participant_b")
    outsider = create_user(username="chat_ws_outsider")
    create_membership(user=first, establishment=establishment)
    second_membership = create_membership(user=second, establishment=establishment)
    create_membership(user=outsider, establishment=establishment)
    token = login(api_client, user=first)

    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=second_membership.id,
    )
    conversation_id = dm_response.json()["conversation"]["id"]
    client_message_id = uuid.uuid4()

    outsider_ticket = get_ws_ticket(api_client, user=outsider, establishment=establishment)

    async def run():
        outsider_comm = await _connect_authenticated(
            ticket=outsider_ticket,
            establishment=establishment,
        )
        await outsider_comm.send_json_to(
            {
                "type": "message.send",
                "conversation_id": conversation_id,
                "client_message_id": str(client_message_id),
                "body": "should fail",
            }
        )
        response = await outsider_comm.receive_json_from()
        await outsider_comm.disconnect()
        return response

    response = async_to_sync(run)()
    close_old_connections()

    assert response["type"] == "message.rejected"
    assert response["code"] == "permission_denied"
    assert ChatMessage.objects.filter(conversation_id=conversation_id).count() == 0


def test_ws_message_send_rejects_empty_body(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_ws_empty_body")
    receiver = create_user(username="chat_ws_empty_body_peer")
    create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    token = login(api_client, user=sender)

    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    conversation_id = dm_response.json()["conversation"]["id"]
    client_message_id = uuid.uuid4()

    sender_ticket = get_ws_ticket(api_client, user=sender, establishment=establishment)

    async def run():
        sender_comm = await _connect_authenticated(
            ticket=sender_ticket,
            establishment=establishment,
        )
        await sender_comm.send_json_to(
            {
                "type": "message.send",
                "conversation_id": conversation_id,
                "client_message_id": str(client_message_id),
                "body": "   ",
            }
        )
        response = await sender_comm.receive_json_from()
        await sender_comm.disconnect()
        return response

    response = async_to_sync(run)()
    close_old_connections()

    assert response["type"] == "message.rejected"
    assert response["code"] == "validation_error"
    assert ChatMessage.objects.filter(conversation_id=conversation_id).count() == 0


def test_ws_message_send_is_idempotent_for_client_message_id(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_ws_idempotent")
    receiver = create_user(username="chat_ws_idempotent_peer")
    create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    token = login(api_client, user=sender)

    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    conversation_id = dm_response.json()["conversation"]["id"]
    client_message_id = uuid.uuid4()

    sender_ticket = get_ws_ticket(api_client, user=sender, establishment=establishment)
    receiver_ticket = get_ws_ticket(api_client, user=receiver, establishment=establishment)

    async def run():
        sender_comm = await _connect_authenticated(
            ticket=sender_ticket,
            establishment=establishment,
        )
        receiver_comm = await _connect_authenticated(
            ticket=receiver_ticket,
            establishment=establishment,
        )

        payload = {
            "type": "message.send",
            "conversation_id": conversation_id,
            "client_message_id": str(client_message_id),
            "body": "once",
        }
        await sender_comm.send_json_to(payload)
        first_sender_event = await sender_comm.receive_json_from()
        first_receiver_event = await receiver_comm.receive_json_from()
        assert first_sender_event["type"] == "message.created"
        assert first_receiver_event["type"] == "message.created"

        await sender_comm.send_json_to(payload)
        retry_event = await sender_comm.receive_json_from()

        await sender_comm.disconnect()
        await receiver_comm.disconnect()
        return first_sender_event, first_receiver_event, retry_event

    first_sender_event, first_receiver_event, retry_event = async_to_sync(run)()
    close_old_connections()

    assert first_sender_event["type"] == "message.created"
    assert first_receiver_event["type"] == "message.created"
    assert retry_event["type"] == "message.created"
    assert retry_event["message"]["id"] == first_sender_event["message"]["id"]
    assert ChatMessage.objects.filter(conversation_id=conversation_id).count() == 1


def test_ws_message_send_does_not_leak_across_conversations(api_client):
    establishment = create_establishment()
    hub = create_user(username="chat_ws_hub")
    peer_a = create_user(username="chat_ws_peer_a")
    peer_b = create_user(username="chat_ws_peer_b")
    create_membership(user=hub, establishment=establishment)
    create_membership(user=peer_a, establishment=establishment)
    peer_b_membership = create_membership(user=peer_b, establishment=establishment)
    hub_token = login(api_client, user=hub)

    dm_b = create_dm(
        api_client,
        token=hub_token,
        establishment_id=establishment.id,
        target_membership_id=peer_b_membership.id,
    )
    conversation_b = dm_b.json()["conversation"]["id"]
    client_message_id = uuid.uuid4()

    hub_ticket = get_ws_ticket(api_client, user=hub, establishment=establishment)
    peer_a_ticket = get_ws_ticket(api_client, user=peer_a, establishment=establishment)

    async def run():
        hub_comm = await _connect_authenticated(ticket=hub_ticket, establishment=establishment)
        peer_a_comm = await _connect_authenticated(
            ticket=peer_a_ticket,
            establishment=establishment,
        )

        await hub_comm.send_json_to(
            {
                "type": "message.send",
                "conversation_id": conversation_b,
                "client_message_id": str(client_message_id),
                "body": "for peer b only",
            }
        )
        await hub_comm.receive_json_from()

        leaked = False
        try:
            await peer_a_comm.receive_json_from(timeout=0.2)
            leaked = True
        except TimeoutError:
            leaked = False

            await hub_comm.disconnect()
            return leaked

    leaked = async_to_sync(run)()
    assert leaked is False
