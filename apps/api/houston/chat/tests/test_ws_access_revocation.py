from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from config.asgi import application
from django.conf import settings
from django.db import close_old_connections, transaction
from django.utils import timezone
from houston.accounts.models import UserSession
from houston.accounts.services import revoke_session, switch_selected_establishment
from houston.chat.groups import membership_group_name, session_group_name
from houston.chat.models import ChatMessage
from houston.chat.services import update_establishment_chat_enabled
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    default_ws_headers,
    get_ws_ticket,
    login,
    ws_chat_path,
    ws_ticket_url,
)
from houston.chat.tests.helpers import create_dm
from houston.chat.tests.ws_helpers import _connect_authenticated
from houston.chat.ws_notify import notify_session_access_revoked
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.testing.auth import ensure_csrf


async def _connect_authenticated_local(*, ticket: str, establishment):
    communicator = WebsocketCommunicator(
        application,
        ws_chat_path(establishment.id),
        headers=default_ws_headers(),
    )
    connected, _ = await communicator.connect()
    assert connected
    await communicator.send_json_to({"type": "auth", "ticket": ticket})
    auth_event = await communicator.receive_json_from()
    assert auth_event["type"] == "auth.ok"
    return communicator


@pytest.mark.django_db(transaction=True)
def test_ws_receives_access_revoked_when_session_revoked_after_auth(api_client):
    establishment = create_establishment()
    user = create_user(username="chat_ws_session_revoke")
    create_membership(user=user, establishment=establishment)
    ticket = get_ws_ticket(api_client, user=user, establishment=establishment)
    session = UserSession.objects.get(user=user)

    async def run():
        communicator = await _connect_authenticated_local(
            ticket=ticket,
            establishment=establishment,
        )

        def revoke() -> None:
            with transaction.atomic():
                revoke_session(session=session)

        await database_sync_to_async(revoke)()
        event = await communicator.receive_json_from()
        close_event = await communicator.receive_output()
        await communicator.disconnect()
        return event, close_event

    event, close_event = async_to_sync(run)()
    close_old_connections()

    assert event["type"] == "access.revoked"
    assert event["reason"] == "session_revoked"
    assert close_event["type"] == "websocket.close"
    assert close_event["code"] == 4002


@pytest.mark.django_db(transaction=True)
def test_ws_message_send_after_session_revoked_creates_no_chat_message(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_ws_send_after_revoke")
    receiver = create_user(username="chat_ws_send_after_revoke_peer")
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
    ticket = get_ws_ticket(api_client, user=sender, establishment=establishment)
    session = UserSession.objects.filter(user=sender).order_by("-created_at").first()
    assert session is not None

    async def run():
        communicator = await _connect_authenticated_local(
            ticket=ticket,
            establishment=establishment,
        )

        def revoke_in_db() -> None:
            session.refresh_from_db()
            session.revoked_at = session.updated_at
            session.status = UserSession.Status.REVOKED
            session.save(update_fields=["revoked_at", "status", "updated_at"])

        await database_sync_to_async(revoke_in_db)()

        await communicator.send_json_to(
            {
                "type": "message.send",
                "conversation_id": conversation_id,
                "client_message_id": str(client_message_id),
                "body": "should not persist",
            }
        )
        event = await communicator.receive_json_from()
        close_event = await communicator.receive_output()
        await communicator.disconnect()
        return event, close_event

    event, close_event = async_to_sync(run)()
    close_old_connections()

    assert event["type"] == "access.revoked"
    assert event["reason"] == "session_revoked"
    assert close_event["type"] == "websocket.close"
    assert close_event["code"] == 4002
    assert ChatMessage.objects.filter(client_message_id=client_message_id).count() == 0


@pytest.mark.django_db(transaction=True)
def test_ws_switch_establishment_revokes_only_current_session(api_client):
    establishment_a = create_establishment()
    establishment_b = Establishment.objects.create(
        name="Switch Site B",
        organization=establishment_a.organization,
        status=Establishment.Status.ACTIVE,
        chat_enabled=True,
    )
    user = create_user(username="chat_ws_switch_session")
    create_membership(user=user, establishment=establishment_a)
    create_membership(user=user, establishment=establishment_b)

    token_a = login(api_client, user=user)
    session_a = UserSession.objects.filter(user=user).order_by("-created_at").first()
    assert session_a is not None
    session_a.selected_establishment = establishment_a
    session_a.save(update_fields=["selected_establishment", "updated_at"])
    ticket_a_response = api_client.post(
        ws_ticket_url(establishment_a.id),
        HTTP_AUTHORIZATION=f"Bearer {token_a}",
    )
    assert ticket_a_response.status_code == 200
    ticket_a = ticket_a_response.json()["ticket"]

    token_b = login(api_client, user=user)
    session_b = UserSession.objects.filter(user=user).order_by("-created_at").first()
    assert session_b is not None
    assert session_a.id != session_b.id
    session_b.selected_establishment = establishment_b
    session_b.save(update_fields=["selected_establishment", "updated_at"])
    ticket_b_response = api_client.post(
        ws_ticket_url(establishment_b.id),
        HTTP_AUTHORIZATION=f"Bearer {token_b}",
    )
    assert ticket_b_response.status_code == 200
    ticket_b = ticket_b_response.json()["ticket"]

    async def run():
        comm_a = await _connect_authenticated(
            ticket=ticket_a,
            establishment=establishment_a,
        )
        comm_b = await _connect_authenticated(
            ticket=ticket_b,
            establishment=establishment_b,
        )

        def switch() -> None:
            with transaction.atomic():
                switch_selected_establishment(
                    session=session_a,
                    establishment_id=establishment_b.id,
                )

        await database_sync_to_async(switch)()

        event = await comm_a.receive_json_from()
        close_event = await comm_a.receive_output()
        await comm_a.disconnect()
        await comm_b.disconnect()
        return event, close_event

    event, close_event = async_to_sync(run)()
    close_old_connections()

    assert event["type"] == "access.revoked"
    assert event["reason"] == "establishment_switched"
    assert close_event["type"] == "websocket.close"
    assert close_event["code"] == 4002


@pytest.mark.django_db(transaction=True)
def test_ws_receives_access_revoked_when_chat_disabled(api_client):
    establishment = create_establishment()
    owner = create_user(username="chat_ws_disable_owner")
    member = create_user(username="chat_ws_disable_member")
    owner_membership = create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    create_membership(user=member, establishment=establishment)
    member_ticket = get_ws_ticket(api_client, user=member, establishment=establishment)

    async def run():
        communicator = await _connect_authenticated_local(
            ticket=member_ticket,
            establishment=establishment,
        )

        def disable_chat() -> None:
            update_establishment_chat_enabled(
                actor_membership=owner_membership,
                chat_enabled=False,
            )

        await database_sync_to_async(disable_chat)()
        event = await communicator.receive_json_from()
        close_event = await communicator.receive_output()
        await communicator.disconnect()
        return event, close_event

    event, close_event = async_to_sync(run)()
    close_old_connections()

    assert event["type"] == "access.revoked"
    assert event["reason"] == "chat_disabled"
    assert close_event["type"] == "websocket.close"
    assert close_event["code"] == 4002


@pytest.mark.django_db(transaction=True)
def test_ws_conversation_access_revoked_does_not_close_global_socket(api_client):
    establishment = create_establishment()
    admin = create_user(username="chat_ws_conv_revoke_admin")
    target = create_user(username="chat_ws_conv_revoke_target")
    admin_membership = create_membership(
        user=admin,
        establishment=establishment,
        role="manager",
    )
    target_membership = create_membership(user=target, establishment=establishment)

    from houston.chat.services import create_group_conversation, remove_group_participant

    conversation = create_group_conversation(
        actor_membership=admin_membership,
        title="Stay connected",
        membership_ids=[target_membership.id],
    )
    target_ticket = get_ws_ticket(api_client, user=target, establishment=establishment)

    async def run():
        communicator = await _connect_authenticated_local(
            ticket=target_ticket,
            establishment=establishment,
        )

        await database_sync_to_async(remove_group_participant)(
            actor_membership=admin_membership,
            conversation_id=conversation.id,
            target_membership_id=target_membership.id,
        )
        event = await communicator.receive_json_from()
        await communicator.disconnect()
        return event

    event = async_to_sync(run)()
    close_old_connections()

    assert event["type"] == "conversation.access_revoked"
    assert event["conversation_id"] == str(conversation.id)


@pytest.mark.django_db(transaction=True)
def test_session_group_name_is_accepted_by_channel_layer(api_client):
    establishment = create_establishment()
    user = create_user(username="chat_ws_session_group")
    create_membership(user=user, establishment=establishment)
    ticket = get_ws_ticket(api_client, user=user, establishment=establishment)
    session = UserSession.objects.get(user=user)

    async def run():
        communicator = await _connect_authenticated_local(
            ticket=ticket,
            establishment=establishment,
        )
        group_name = session_group_name(session_id=session.id)
        assert group_name == f"chat_session_{session.id}"

        await database_sync_to_async(notify_session_access_revoked)(
            session_id=session.id,
            reason="session_revoked",
        )
        event = await communicator.receive_json_from()
        close_event = await communicator.receive_output()
        await communicator.disconnect()
        return event, close_event

    event, close_event = async_to_sync(run)()
    close_old_connections()

    assert event["type"] == "access.revoked"
    assert event["reason"] == "session_revoked"
    assert close_event["type"] == "websocket.close"
    assert close_event["code"] == 4002


@pytest.mark.django_db(transaction=True)
def test_ws_refresh_reuse_revokes_chat_without_client_frame(api_client):
    establishment = create_establishment()
    user = create_user(username="chat_ws_refresh_reuse")
    membership = create_membership(user=user, establishment=establishment)
    token = login(api_client, user=user)
    session = UserSession.objects.filter(user=user).order_by("-created_at").first()
    assert session is not None
    old_refresh = api_client.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME].value
    ticket_response = api_client.post(
        ws_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert ticket_response.status_code == 200
    ticket = ticket_response.json()["ticket"]
    discarded_groups: list[str] = []

    async def run():
        layer = get_channel_layer()
        original_discard = layer.group_discard

        async def spy_discard(group, channel):
            discarded_groups.append(group)
            return await original_discard(group, channel)

        layer.group_discard = spy_discard
        try:
            communicator = await _connect_authenticated_local(
                ticket=ticket,
                establishment=establishment,
            )

            def rotate_then_reuse() -> None:
                csrf = ensure_csrf(api_client)
                rotate = api_client.post(
                    "/api/v1/auth/refresh/",
                    {"refresh_token_transport": "cookie"},
                    format="json",
                    HTTP_X_CSRFTOKEN=csrf,
                )
                assert rotate.status_code == 200
                api_client.cookies[settings.HOUSTON_AUTH_REFRESH_COOKIE_NAME] = old_refresh
                reuse = api_client.post(
                    "/api/v1/auth/refresh/",
                    {"refresh_token_transport": "cookie"},
                    format="json",
                    HTTP_X_CSRFTOKEN=csrf,
                )
                assert reuse.status_code == 401

            await database_sync_to_async(rotate_then_reuse)()
            event = await communicator.receive_json_from()
            close_event = await communicator.receive_output()
            await communicator.disconnect()
            return event, close_event
        finally:
            layer.group_discard = original_discard

    event, close_event = async_to_sync(run)()
    close_old_connections()

    assert event["type"] == "access.revoked"
    assert event["reason"] == "session_revoked"
    assert close_event["type"] == "websocket.close"
    assert close_event["code"] == 4002
    assert (
        membership_group_name(
            establishment_id=establishment.id,
            membership_id=membership.id,
        )
        in discarded_groups
    )
    assert session_group_name(session_id=session.id) in discarded_groups


@pytest.mark.django_db(transaction=True)
def test_ws_injected_message_created_after_silent_revoke_drops_body(api_client):
    establishment = create_establishment()
    user = create_user(username="chat_ws_silent_revoke")
    membership = create_membership(user=user, establishment=establishment)
    ticket = get_ws_ticket(api_client, user=user, establishment=establishment)
    session = UserSession.objects.filter(user=user).order_by("-created_at").first()
    assert session is not None

    async def run():
        communicator = await _connect_authenticated_local(
            ticket=ticket,
            establishment=establishment,
        )

        def revoke_in_db() -> None:
            session.refresh_from_db()
            session.revoked_at = timezone.now()
            session.status = UserSession.Status.REVOKED
            session.save(update_fields=["revoked_at", "status", "updated_at"])

        await database_sync_to_async(revoke_in_db)()
        await get_channel_layer().group_send(
            membership_group_name(
                establishment_id=establishment.id,
                membership_id=membership.id,
            ),
            {
                "type": "chat.message.created",
                "payload": {
                    "type": "message.created",
                    "conversation_id": str(uuid.uuid4()),
                    "message": {"id": str(uuid.uuid4())},
                },
            },
        )
        first = await communicator.receive_output()
        await communicator.disconnect()
        return first

    first = async_to_sync(run)()
    close_old_connections()

    if first["type"] == "websocket.send":
        import json

        payload = json.loads(first["text"])
        assert payload["type"] == "access.revoked"
        assert payload.get("message") is None
    else:
        assert first["type"] == "websocket.close"


@pytest.mark.django_db(transaction=True)
def test_ws_expired_session_timestamps_block_send(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_ws_expired_send")
    receiver = create_user(username="chat_ws_expired_peer")
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
    ticket_response = api_client.post(
        ws_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    ticket = ticket_response.json()["ticket"]
    session = UserSession.objects.filter(user=sender).order_by("-created_at").first()
    assert session is not None

    async def run():
        communicator = await _connect_authenticated_local(
            ticket=ticket,
            establishment=establishment,
        )

        def expire() -> None:
            session.refresh_from_db()
            session.refresh_expires_at = timezone.now() - timedelta(seconds=1)
            session.save(update_fields=["refresh_expires_at", "updated_at"])

        await database_sync_to_async(expire)()
        await communicator.send_json_to(
            {
                "type": "message.send",
                "conversation_id": conversation_id,
                "client_message_id": str(client_message_id),
                "body": "should not persist",
            }
        )
        event = await communicator.receive_json_from()
        close_event = await communicator.receive_output()
        await communicator.disconnect()
        return event, close_event

    event, close_event = async_to_sync(run)()
    close_old_connections()

    assert event["type"] == "access.revoked"
    assert event["reason"] == "session_revoked"
    assert close_event["type"] == "websocket.close"
    assert close_event["code"] == 4002
    assert ChatMessage.objects.filter(client_message_id=client_message_id).count() == 0


@pytest.mark.django_db(transaction=True)
def test_ws_switch_without_notify_blocks_send_and_receive(api_client):
    establishment_a = create_establishment()
    establishment_b = Establishment.objects.create(
        name="Silent Switch B",
        organization=establishment_a.organization,
        status=Establishment.Status.ACTIVE,
        chat_enabled=True,
    )
    sender = create_user(username="chat_ws_silent_switch")
    receiver = create_user(username="chat_ws_silent_switch_peer")
    create_membership(user=sender, establishment=establishment_a)
    create_membership(user=sender, establishment=establishment_b)
    receiver_membership = create_membership(user=receiver, establishment=establishment_a)
    token = login(api_client, user=sender)
    session = UserSession.objects.filter(user=sender).order_by("-created_at").first()
    assert session is not None
    session.selected_establishment = establishment_a
    session.save(update_fields=["selected_establishment", "updated_at"])
    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment_a.id,
        target_membership_id=receiver_membership.id,
    )
    conversation_id = dm_response.json()["conversation"]["id"]
    client_message_id = uuid.uuid4()
    ticket_response = api_client.post(
        ws_ticket_url(establishment_a.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    ticket = ticket_response.json()["ticket"]

    async def run():
        communicator = await _connect_authenticated_local(
            ticket=ticket,
            establishment=establishment_a,
        )

        def switch_silently() -> None:
            with patch("houston.chat.ws_notify.notify_session_access_revoked"):
                switch_selected_establishment(
                    session=session,
                    establishment_id=establishment_b.id,
                )

        await database_sync_to_async(switch_silently)()
        await communicator.send_json_to(
            {
                "type": "message.send",
                "conversation_id": conversation_id,
                "client_message_id": str(client_message_id),
                "body": "should not persist",
            }
        )
        inbound = await communicator.receive_json_from()
        close_event = await communicator.receive_output()
        await communicator.disconnect()
        return inbound, close_event

    inbound, close_event = async_to_sync(run)()
    close_old_connections()

    assert inbound["type"] == "access.revoked"
    assert inbound["reason"] == "establishment_switched"
    assert inbound.get("message") is None
    assert close_event["type"] == "websocket.close"
    assert close_event["code"] == 4002
    assert ChatMessage.objects.filter(client_message_id=client_message_id).count() == 0
