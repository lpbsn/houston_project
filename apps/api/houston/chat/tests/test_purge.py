from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone
from houston.chat.models import ChatConversation, ChatMessage
from houston.chat.purge import purge_chat_messages
from houston.chat.tests.conftest import create_establishment, create_membership, create_user, login
from houston.chat.tests.test_rest_api import create_dm


@pytest.mark.django_db
def test_purge_deletes_messages_older_than_retention_window(api_client):
    establishment = create_establishment()
    sender = create_user(username="chat_purge_sender")
    receiver = create_user(username="chat_purge_receiver")
    sender_membership = create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    token = login(api_client, user=sender)

    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    conversation = ChatConversation.objects.get(id=dm_response.json()["conversation"]["id"])

    old_message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="old",
        client_message_id=uuid.uuid4(),
    )
    recent_message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=sender_membership,
        body="recent",
        client_message_id=uuid.uuid4(),
    )
    old_created_at = timezone.now() - timedelta(days=8)
    recent_created_at = timezone.now() - timedelta(days=2)
    ChatMessage.objects.filter(id=old_message.id).update(created_at=old_created_at)
    ChatMessage.objects.filter(id=recent_message.id).update(created_at=recent_created_at)
    conversation.last_message_at = recent_created_at
    conversation.save(update_fields=["last_message_at", "updated_at"])

    dry_run = purge_chat_messages(dry_run=True)
    assert dry_run.deleted_count == 1
    assert dry_run.dry_run is True
    assert ChatMessage.objects.filter(id=old_message.id).exists()
    assert ChatMessage.objects.filter(id=recent_message.id).exists()

    result = purge_chat_messages(dry_run=False)
    assert result.deleted_count == 1
    assert result.batch_count == 1
    assert not ChatMessage.objects.filter(id=old_message.id).exists()
    assert ChatMessage.objects.filter(id=recent_message.id).exists()

    conversation.refresh_from_db()
    assert conversation.last_message_at == recent_created_at


@pytest.mark.django_db
def test_purge_can_be_scoped_to_establishment():
    establishment_a = create_establishment()
    establishment_b = create_establishment()
    user_a = create_user(username="chat_purge_a")
    user_a_peer = create_user(username="chat_purge_a_peer")
    user_b = create_user(username="chat_purge_b")
    user_b_peer = create_user(username="chat_purge_b_peer")
    membership_a = create_membership(user=user_a, establishment=establishment_a)
    membership_a_peer = create_membership(user=user_a_peer, establishment=establishment_a)
    membership_b = create_membership(user=user_b, establishment=establishment_b)
    membership_b_peer = create_membership(user=user_b_peer, establishment=establishment_b)

    conversation_a = ChatConversation.objects.create(
        establishment=establishment_a,
        type=ChatConversation.Type.DM,
        created_by_membership=membership_a,
        dm_membership_a=membership_a,
        dm_membership_b=membership_a_peer,
    )
    conversation_b = ChatConversation.objects.create(
        establishment=establishment_b,
        type=ChatConversation.Type.DM,
        created_by_membership=membership_b,
        dm_membership_a=membership_b,
        dm_membership_b=membership_b_peer,
    )

    message_a = ChatMessage.objects.create(
        conversation=conversation_a,
        author_membership=membership_a,
        body="a",
        client_message_id=uuid.uuid4(),
    )
    message_b = ChatMessage.objects.create(
        conversation=conversation_b,
        author_membership=membership_b,
        body="b",
        client_message_id=uuid.uuid4(),
    )
    old_created_at = timezone.now() - timedelta(days=8)
    ChatMessage.objects.filter(id=message_a.id).update(created_at=old_created_at)
    ChatMessage.objects.filter(id=message_b.id).update(created_at=old_created_at)

    result = purge_chat_messages(establishment_id=establishment_a.id, dry_run=False)
    assert result.deleted_count == 1
    assert not ChatMessage.objects.filter(id=message_a.id).exists()
    assert ChatMessage.objects.filter(id=message_b.id).exists()
