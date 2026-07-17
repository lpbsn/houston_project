from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone
from houston.chat.models import ChatMessage, ChatParticipant
from houston.chat.services import (
    create_message,
    hide_dm_conversation,
    leave_group_conversation,
    mark_conversation_seen,
    pin_conversation,
)
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    login,
)
from houston.chat.tests.helpers import chat_url, create_dm, create_group
from houston.notifications.models import Notification
from houston.notifications.services import create_in_app_notification
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_pin_unpin_orders_conversation_list(api_client):
    establishment = create_establishment()
    actor = create_user(username="pin_actor")
    peer = create_user(username="pin_peer")
    actor_membership = create_membership(user=actor, establishment=establishment)
    peer_membership = create_membership(user=peer, establishment=establishment)
    token = login(api_client, user=actor)

    dm = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=peer_membership.id,
    )
    dm_id = dm.json()["conversation"]["id"]
    group = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="Pinned Group",
        membership_ids=[actor_membership.id, peer_membership.id],
    )
    group_id = group.json()["conversation"]["id"]

    create_message(
        author_membership=peer_membership,
        establishment_id=establishment.id,
        conversation_id=uuid.UUID(dm_id),
        client_message_id=uuid.uuid4(),
        body="newer dm",
    )

    pin_response = api_client.post(
        chat_url(establishment.id, f"conversations/{group_id}/pin/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert pin_response.status_code == 204

    listing = api_client.get(
        chat_url(establishment.id, "conversations/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert items[0]["id"] == group_id
    assert items[0]["pinned"] is True
    assert items[1]["id"] == dm_id
    assert items[1]["pinned"] is False

    unpin_response = api_client.delete(
        chat_url(establishment.id, f"conversations/{group_id}/pin/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert unpin_response.status_code == 204


def test_hide_dm_is_personal_and_cutoff_applies(api_client):
    establishment = create_establishment()
    alice = create_user(username="hide_alice")
    bob = create_user(username="hide_bob")
    alice_membership = create_membership(user=alice, establishment=establishment)
    bob_membership = create_membership(user=bob, establishment=establishment)

    alice_client = APIClient()
    bob_client = APIClient()
    alice_token = login(alice_client, user=alice)
    bob_token = login(bob_client, user=bob)

    dm = create_dm(
        alice_client,
        token=alice_token,
        establishment_id=establishment.id,
        target_membership_id=bob_membership.id,
    )
    conversation_id = uuid.UUID(dm.json()["conversation"]["id"])

    old_message = create_message(
        author_membership=bob_membership,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        client_message_id=uuid.uuid4(),
        body="old secret",
    ).message

    created = create_in_app_notification(
        establishment_id=establishment.id,
        recipient_membership=alice_membership,
        event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
        subject_type=Notification.SubjectType.CHAT_CONVERSATION,
        subject_id=conversation_id,
        priority=Notification.Priority.INFO,
        actor_membership=bob_membership,
    )
    assert created is not None

    hide_response = alice_client.post(
        chat_url(establishment.id, f"conversations/{conversation_id}/hide/"),
        HTTP_AUTHORIZATION=f"Bearer {alice_token}",
    )
    assert hide_response.status_code == 204

    alice_list = alice_client.get(
        chat_url(establishment.id, "conversations/"),
        HTTP_AUTHORIZATION=f"Bearer {alice_token}",
    )
    assert alice_list.status_code == 200
    assert alice_list.json()["items"] == []

    bob_list = bob_client.get(
        chat_url(establishment.id, "conversations/"),
        HTTP_AUTHORIZATION=f"Bearer {bob_token}",
    )
    assert bob_list.status_code == 200
    assert len(bob_list.json()["items"]) == 1
    assert bob_list.json()["items"][0]["last_message_preview"]["body"] == "old secret"

    assert (
        Notification.objects.filter(
            recipient_membership=alice_membership,
            subject_id=conversation_id,
            status=Notification.Status.UNREAD,
        ).count()
        == 0
    )

    alice_messages = alice_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        HTTP_AUTHORIZATION=f"Bearer {alice_token}",
    )
    assert alice_messages.status_code == 200
    assert alice_messages.json()["items"] == []
    assert ChatMessage.objects.filter(id=old_message.id).exists()

    create_message(
        author_membership=bob_membership,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        client_message_id=uuid.uuid4(),
        body="after hide",
    )

    alice_list_after = alice_client.get(
        chat_url(establishment.id, "conversations/"),
        HTTP_AUTHORIZATION=f"Bearer {alice_token}",
    )
    assert len(alice_list_after.json()["items"]) == 1
    assert alice_list_after.json()["items"][0]["last_message_preview"]["body"] == "after hide"
    assert alice_list_after.json()["items"][0]["pinned"] is False

    alice_messages_after = alice_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        HTTP_AUTHORIZATION=f"Bearer {alice_token}",
    )
    bodies = [item["body"] for item in alice_messages_after.json()["items"]]
    assert bodies == ["after hide"]


def test_hide_dm_race_keeps_list_hidden_when_message_is_not_after_hide():
    establishment = create_establishment()
    alice = create_user(username="race_alice")
    bob = create_user(username="race_bob")
    alice_membership = create_membership(user=alice, establishment=establishment)
    bob_membership = create_membership(user=bob, establishment=establishment)
    api_client = APIClient()
    token = login(api_client, user=alice)
    dm = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=bob_membership.id,
    )
    conversation_id = uuid.UUID(dm.json()["conversation"]["id"])

    hide_at = timezone.now()
    participant = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=alice_membership,
    )
    participant.list_hidden_at = hide_at
    participant.history_cutoff_at = hide_at
    participant.save(update_fields=["list_hidden_at", "history_cutoff_at", "updated_at"])

    past_message = ChatMessage.objects.create(
        conversation_id=conversation_id,
        author_membership=bob_membership,
        body="past race",
        client_message_id=uuid.uuid4(),
    )
    ChatMessage.objects.filter(id=past_message.id).update(
        created_at=hide_at - timedelta(seconds=1)
    )
    past_message.refresh_from_db()

    # Same clear condition as create_message
    ChatParticipant.objects.filter(
        conversation_id=conversation_id,
        left_at__isnull=True,
        list_hidden_at__isnull=False,
        list_hidden_at__lt=past_message.created_at,
    ).update(list_hidden_at=None, updated_at=timezone.now())

    participant.refresh_from_db()
    assert participant.list_hidden_at == hide_at


def test_reopen_hidden_dm_shows_empty_thread(api_client):
    establishment = create_establishment()
    alice = create_user(username="reopen_alice")
    bob = create_user(username="reopen_bob")
    create_membership(user=alice, establishment=establishment)
    bob_membership = create_membership(user=bob, establishment=establishment)
    token = login(api_client, user=alice)
    dm = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=bob_membership.id,
    )
    conversation_id = uuid.UUID(dm.json()["conversation"]["id"])
    create_message(
        author_membership=bob_membership,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        client_message_id=uuid.uuid4(),
        body="hidden later",
    )
    assert (
        api_client.post(
            chat_url(establishment.id, f"conversations/{conversation_id}/hide/"),
            HTTP_AUTHORIZATION=f"Bearer {token}",
        ).status_code
        == 204
    )

    reopen = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=bob_membership.id,
    )
    assert reopen.status_code == 200
    assert reopen.json()["created"] is False
    assert reopen.json()["conversation"]["id"] == str(conversation_id)

    listing = api_client.get(
        chat_url(establishment.id, "conversations/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert len(listing.json()["items"]) == 1
    assert listing.json()["items"][0]["last_message_preview"] is None

    messages = api_client.get(
        chat_url(establishment.id, f"conversations/{conversation_id}/messages/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert messages.json()["items"] == []


def test_hide_rejects_groups(api_client):
    establishment = create_establishment()
    actor = create_user(username="hide_group_actor")
    peer = create_user(username="hide_group_peer")
    actor_membership = create_membership(user=actor, establishment=establishment)
    peer_membership = create_membership(user=peer, establishment=establishment)
    token = login(api_client, user=actor)
    group = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="No Hide",
        membership_ids=[actor_membership.id, peer_membership.id],
    )
    group_id = group.json()["conversation"]["id"]
    response = api_client.post(
        chat_url(establishment.id, f"conversations/{group_id}/hide/"),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 400


def test_leave_clears_pin_and_schedules_access_revoked(api_client):
    establishment = create_establishment()
    actor = create_user(username="leave_pin_actor")
    peer = create_user(username="leave_pin_peer")
    actor_membership = create_membership(user=actor, establishment=establishment)
    peer_membership = create_membership(user=peer, establishment=establishment)
    token = login(api_client, user=actor)
    group = create_group(
        api_client,
        token=token,
        establishment_id=establishment.id,
        title="Leave Me",
        membership_ids=[actor_membership.id, peer_membership.id],
    )
    conversation_id = uuid.UUID(group.json()["conversation"]["id"])
    pin_conversation(actor_membership=actor_membership, conversation_id=conversation_id)

    with patch("houston.chat.services.schedule_conversation_access_revoked") as schedule_revoked:
        leave_group_conversation(
            actor_membership=actor_membership,
            conversation_id=conversation_id,
        )
    schedule_revoked.assert_called_once()
    assert schedule_revoked.call_args.kwargs["reason"] == "participant_left"

    participant = ChatParticipant.objects.get(
        conversation_id=conversation_id,
        membership=actor_membership,
    )
    assert participant.left_at is not None
    assert participant.pinned_at is None


def test_member_cannot_delete_group_admin_can(api_client):
    establishment = create_establishment()
    admin = create_user(username="delete_admin")
    member = create_user(username="delete_member")
    admin_membership = create_membership(user=admin, establishment=establishment)
    member_membership = create_membership(user=member, establishment=establishment)
    admin_token = login(api_client, user=admin)
    group = create_group(
        api_client,
        token=admin_token,
        establishment_id=establishment.id,
        title="Delete Me",
        membership_ids=[admin_membership.id, member_membership.id],
    )
    conversation_id = group.json()["conversation"]["id"]

    member_client = APIClient()
    member_token = login(member_client, user=member)
    forbidden = member_client.delete(
        chat_url(establishment.id, f"conversations/{conversation_id}/"),
        HTTP_AUTHORIZATION=f"Bearer {member_token}",
    )
    assert forbidden.status_code == 403

    allowed = api_client.delete(
        chat_url(establishment.id, f"conversations/{conversation_id}/"),
        HTTP_AUTHORIZATION=f"Bearer {admin_token}",
    )
    assert allowed.status_code == 204


def test_mark_conversation_seen_respects_history_cutoff():
    establishment = create_establishment()
    alice = create_user(username="seen_cutoff_alice")
    bob = create_user(username="seen_cutoff_bob")
    alice_membership = create_membership(user=alice, establishment=establishment)
    bob_membership = create_membership(user=bob, establishment=establishment)
    api_client = APIClient()
    token = login(api_client, user=alice)
    dm = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=bob_membership.id,
    )
    conversation_id = uuid.UUID(dm.json()["conversation"]["id"])
    create_message(
        author_membership=bob_membership,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        client_message_id=uuid.uuid4(),
        body="old",
    )
    hide_dm_conversation(
        actor_membership=alice_membership,
        conversation_id=conversation_id,
    )
    participant = mark_conversation_seen(
        actor_membership=alice_membership,
        conversation_id=conversation_id,
    )
    # No visible messages after cutoff → no-op relative to advancing onto cutoff-hidden msgs
    seen_after_empty = participant.last_seen_message_id

    new = create_message(
        author_membership=bob_membership,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        client_message_id=uuid.uuid4(),
        body="new",
    ).message
    participant = mark_conversation_seen(
        actor_membership=alice_membership,
        conversation_id=conversation_id,
    )
    assert participant.last_seen_message_id == new.id
    assert seen_after_empty != new.id


def test_list_item_exposes_can_delete_for_group_admin(api_client):
    establishment = create_establishment()
    admin = create_user(username="list_can_delete_admin")
    member = create_user(username="list_can_delete_member")
    admin_membership = create_membership(user=admin, establishment=establishment)
    member_membership = create_membership(user=member, establishment=establishment)
    admin_token = login(api_client, user=admin)
    group = create_group(
        api_client,
        token=admin_token,
        establishment_id=establishment.id,
        title="Flags",
        membership_ids=[admin_membership.id, member_membership.id],
    )
    group_id = group.json()["conversation"]["id"]

    admin_list = api_client.get(
        chat_url(establishment.id, "conversations/"),
        HTTP_AUTHORIZATION=f"Bearer {admin_token}",
    )
    admin_item = next(item for item in admin_list.json()["items"] if item["id"] == group_id)
    assert admin_item["can_delete"] is True

    member_client = APIClient()
    member_token = login(member_client, user=member)
    member_list = member_client.get(
        chat_url(establishment.id, "conversations/"),
        HTTP_AUTHORIZATION=f"Bearer {member_token}",
    )
    member_item = next(item for item in member_list.json()["items"] if item["id"] == group_id)
    assert member_item["can_delete"] is False
