from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from houston.chat.models import ChatConversation, ChatMessage, ChatParticipant
from houston.chat.selectors import (
    count_unread_messages_for_participant,
    get_unread_message_counts_by_conversation_ids,
)
from houston.chat.tests.conftest import create_establishment, create_membership, create_user

pytestmark = pytest.mark.django_db


def _create_dm_conversation(*, establishment, membership_a, membership_b):
    first_id, second_id = sorted((membership_a.id, membership_b.id))
    conversation = ChatConversation.objects.create(
        establishment=establishment,
        type=ChatConversation.Type.DM,
        dm_membership_a_id=first_id,
        dm_membership_b_id=second_id,
        created_by_membership=membership_a,
    )
    ChatParticipant.objects.create(conversation=conversation, membership=membership_a)
    ChatParticipant.objects.create(conversation=conversation, membership=membership_b)
    return conversation


def _create_message(*, conversation, author_membership, body: str, created_at=None):
    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=author_membership,
        body=body,
        client_message_id=uuid.uuid4(),
    )
    if created_at is not None:
        ChatMessage.objects.filter(id=message.id).update(created_at=created_at)
        message.refresh_from_db()
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message_at", "updated_at"])
    return message


def _viewer_participant(*, conversation, viewer_membership):
    return ChatParticipant.objects.get(
        conversation=conversation,
        membership=viewer_membership,
    )


def test_count_unread_messages_returns_zero_after_seen_cursor():
    establishment = create_establishment()
    sender = create_membership(user=create_user(username="sender"), establishment=establishment)
    receiver = create_membership(user=create_user(username="receiver"), establishment=establishment)
    conversation = _create_dm_conversation(
        establishment=establishment,
        membership_a=sender,
        membership_b=receiver,
    )
    message = _create_message(
        conversation=conversation,
        author_membership=sender,
        body="hello",
    )
    participant = _viewer_participant(conversation=conversation, viewer_membership=receiver)
    participant.last_seen_message_id = message.id
    participant.last_seen_message_created_at = message.created_at
    participant.save(
        update_fields=[
            "last_seen_message_id",
            "last_seen_message_created_at",
            "updated_at",
        ]
    )

    assert count_unread_messages_for_participant(participant=participant) == 0


def test_count_unread_messages_counts_incoming_messages_before_seen():
    establishment = create_establishment()
    sender = create_membership(
        user=create_user(username="sender2"),
        establishment=establishment,
    )
    receiver = create_membership(
        user=create_user(username="receiver2"),
        establishment=establishment,
    )
    conversation = _create_dm_conversation(
        establishment=establishment,
        membership_a=sender,
        membership_b=receiver,
    )
    base_time = timezone.now()
    for index in range(3):
        _create_message(
            conversation=conversation,
            author_membership=sender,
            body=f"msg-{index}",
            created_at=base_time + timedelta(minutes=index),
        )
    participant = _viewer_participant(conversation=conversation, viewer_membership=receiver)

    assert count_unread_messages_for_participant(participant=participant) == 3


def test_count_unread_messages_excludes_viewer_messages():
    establishment = create_establishment()
    sender = create_membership(
        user=create_user(username="sender3"),
        establishment=establishment,
    )
    receiver = create_membership(
        user=create_user(username="receiver3"),
        establishment=establishment,
    )
    conversation = _create_dm_conversation(
        establishment=establishment,
        membership_a=sender,
        membership_b=receiver,
    )
    _create_message(conversation=conversation, author_membership=sender, body="from sender")
    _create_message(conversation=conversation, author_membership=receiver, body="from receiver")
    participant = _viewer_participant(conversation=conversation, viewer_membership=receiver)

    assert count_unread_messages_for_participant(participant=participant) == 1


def test_bulk_unread_counts_use_single_aggregated_query():
    establishment = create_establishment()
    sender = create_membership(
        user=create_user(username="sender4"),
        establishment=establishment,
    )
    receiver = create_membership(
        user=create_user(username="receiver4"),
        establishment=establishment,
    )
    other_peer = create_membership(
        user=create_user(username="receiver5"),
        establishment=establishment,
    )
    first_conversation = _create_dm_conversation(
        establishment=establishment,
        membership_a=sender,
        membership_b=receiver,
    )
    second_conversation = _create_dm_conversation(
        establishment=establishment,
        membership_a=sender,
        membership_b=other_peer,
    )
    _create_message(conversation=first_conversation, author_membership=sender, body="one")
    base_time = timezone.now()
    for index in range(2):
        _create_message(
            conversation=second_conversation,
            author_membership=sender,
            body=f"two-{index}",
            created_at=base_time + timedelta(minutes=index),
        )

    with CaptureQueriesContext(connection) as captured:
        counts = get_unread_message_counts_by_conversation_ids(
            membership_id=receiver.id,
            conversation_ids=[first_conversation.id, second_conversation.id],
        )

    assert len(captured.captured_queries) == 1
    assert counts[first_conversation.id] == 1
    assert counts[second_conversation.id] == 0
