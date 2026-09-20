from __future__ import annotations

import uuid

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.db import close_old_connections
from houston.chat.groups import membership_group_name
from houston.chat.models import ChatMessage
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    login,
)
from houston.chat.tests.helpers import create_dm, send_message
from houston.chat.tests.ws_helpers import _connect_authenticated, get_ws_ticket

pytestmark = pytest.mark.django_db(transaction=True)


def test_ws_rejects_message_send_without_persist(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_ws_protocol_sender")
    receiver = create_user(username="chat_ws_protocol_receiver")
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
                "client_message_id": str(uuid.uuid4()),
                "body": "should not persist",
            }
        )
        error = await sender_comm.receive_json_from()
        close_event = await sender_comm.receive_output()
        await sender_comm.disconnect()
        return error, close_event

    error, close_event = async_to_sync(run)()
    close_old_connections()

    assert error["type"] == "error"
    assert error["code"] == "protocol_error"
    assert close_event["type"] == "websocket.close"
    assert close_event["code"] == 4400
    assert ChatMessage.objects.filter(conversation_id=conversation_id).count() == 0


def test_http_send_broadcasts_message_created_to_ws(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_ws_http_sender")
    receiver = create_user(username="chat_ws_http_receiver")
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
        await database_sync_to_async(send_message)(
            api_client,
            token=token,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            body="  hello ws  ",
            client_message_id=client_message_id,
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


def test_ws_delivers_first_http_message_for_new_dm_without_reconnect(api_client):
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
        await database_sync_to_async(send_message)(
            api_client,
            token=peer_token,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            body="first message on new dm",
            client_message_id=client_message_id,
        )
        peer_event = await peer_comm.receive_json_from()
        connected_event = await connected_comm.receive_json_from()
        await connected_comm.disconnect()
        await peer_comm.disconnect()
        return peer_event, connected_event

    peer_event, connected_event = async_to_sync(run)()
    close_old_connections()

    assert peer_event["type"] == "message.created"
    assert connected_event["type"] == "message.created"
    assert connected_event["message"]["body"] == "first message on new dm"


def test_http_send_does_not_leak_across_conversations(api_client):
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
        await database_sync_to_async(send_message)(
            api_client,
            token=hub_token,
            establishment_id=establishment.id,
            conversation_id=conversation_b,
            body="for peer b only",
            client_message_id=client_message_id,
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
        await hub_comm.disconnect()
        await peer_a_comm.disconnect()
        return leaked

    leaked = async_to_sync(run)()
    assert leaked is False


def test_ws_message_created_dropped_after_conversation_leave(api_client):
    establishment = create_establishment()
    admin = create_user(username="chat_ws_drop_admin")
    target = create_user(username="chat_ws_drop_target")
    admin_membership = create_membership(
        user=admin,
        establishment=establishment,
        role="manager",
    )
    target_membership = create_membership(user=target, establishment=establishment)
    from houston.chat.services import create_group_conversation, remove_group_participant

    conversation = create_group_conversation(
        actor_membership=admin_membership,
        title="Drop after leave",
        membership_ids=[target_membership.id],
    )
    target_ticket = get_ws_ticket(api_client, user=target, establishment=establishment)

    async def run():
        communicator = await _connect_authenticated(
            ticket=target_ticket,
            establishment=establishment,
        )
        await database_sync_to_async(remove_group_participant)(
            actor_membership=admin_membership,
            conversation_id=conversation.id,
            target_membership_id=target_membership.id,
        )
        revoked = await communicator.receive_json_from()
        assert revoked["type"] == "conversation.access_revoked"

        await get_channel_layer().group_send(
            membership_group_name(
                establishment_id=establishment.id,
                membership_id=target_membership.id,
            ),
            {
                "type": "chat.message.created",
                "payload": {
                    "type": "message.created",
                    "conversation_id": str(conversation.id),
                    "message": {"id": str(uuid.uuid4())},
                },
            },
        )
        try:
            leaked_event = await communicator.receive_output(timeout=0.4)
        except TimeoutError:
            return None
        return leaked_event

    leaked_event = async_to_sync(run)()
    close_old_connections()
    assert leaked_event is None


def test_ws_conversation_updated_dropped_after_conversation_leave(api_client):
    establishment = create_establishment()
    admin = create_user(username="chat_ws_updated_admin")
    target = create_user(username="chat_ws_updated_target")
    admin_membership = create_membership(
        user=admin,
        establishment=establishment,
        role="manager",
    )
    target_membership = create_membership(user=target, establishment=establishment)
    from houston.chat.services import create_group_conversation, remove_group_participant

    conversation = create_group_conversation(
        actor_membership=admin_membership,
        title="Updated after leave",
        membership_ids=[target_membership.id],
    )
    target_ticket = get_ws_ticket(api_client, user=target, establishment=establishment)

    async def run():
        communicator = await _connect_authenticated(
            ticket=target_ticket,
            establishment=establishment,
        )
        await database_sync_to_async(remove_group_participant)(
            actor_membership=admin_membership,
            conversation_id=conversation.id,
            target_membership_id=target_membership.id,
        )
        revoked = await communicator.receive_json_from()
        assert revoked["type"] == "conversation.access_revoked"

        await get_channel_layer().group_send(
            membership_group_name(
                establishment_id=establishment.id,
                membership_id=target_membership.id,
            ),
            {
                "type": "chat.conversation.updated",
                "payload": {
                    "type": "conversation.updated",
                    "conversation_id": str(conversation.id),
                },
            },
        )
        try:
            leaked_event = await communicator.receive_output(timeout=0.4)
        except TimeoutError:
            return None
        return leaked_event

    leaked_event = async_to_sync(run)()
    close_old_connections()
    assert leaked_event is None
