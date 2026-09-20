from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from houston.chat.api.serializers import membership_display_name
from houston.chat.exceptions import ChatValidationError
from houston.chat.models import ChatMessage, ChatMessageMention
from houston.chat.services import create_message
from houston.chat.tests.conftest import create_establishment, create_membership, create_user, login
from houston.chat.tests.helpers import create_dm, send_message

pytestmark = pytest.mark.django_db


def _setup_dm():
    establishment = create_establishment()
    sender = create_user(username=f"chat_http_{uuid.uuid4().hex[:8]}")
    receiver = create_user(username=f"chat_http_peer_{uuid.uuid4().hex[:8]}")
    sender_membership = create_membership(user=sender, establishment=establishment)
    receiver_membership = create_membership(user=receiver, establishment=establishment)
    return establishment, sender, receiver, sender_membership, receiver_membership


def test_http_send_creates_message(api_client):
    establishment, sender, _receiver, _sender_membership, receiver_membership = _setup_dm()
    token = login(api_client, user=sender)
    dm = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    conversation_id = dm.json()["conversation"]["id"]
    client_message_id = uuid.uuid4()

    response = send_message(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        body="  hello http  ",
        client_message_id=client_message_id,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["created"] is True
    assert payload["message"]["body"] == "hello http"
    assert payload["message"]["client_message_id"] == str(client_message_id)
    assert payload["message"]["is_reply"] is False
    assert payload["message"]["mentions"] == []
    assert ChatMessage.objects.filter(conversation_id=conversation_id).count() == 1


def test_http_send_idempotent_without_second_fanout_or_notification(api_client):
    establishment, sender, _receiver, sender_membership, receiver_membership = _setup_dm()
    token = login(api_client, user=sender)
    dm = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    conversation_id = uuid.UUID(dm.json()["conversation"]["id"])
    client_message_id = uuid.uuid4()

    first = send_message(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        body="once",
        client_message_id=client_message_id,
    )
    assert first.status_code == 201

    retry = send_message(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        body="once",
        client_message_id=client_message_id,
    )
    assert retry.status_code == 200
    assert retry.json()["created"] is False
    assert retry.json()["message"]["id"] == first.json()["message"]["id"]
    assert ChatMessage.objects.filter(conversation_id=conversation_id).count() == 1

    with (
        patch("houston.chat.ws_notify.notify_message_created") as mock_fanout,
        patch(
            "houston.notifications.scheduling.schedule_chat_message_received_notification"
        ) as mock_notif,
    ):
        result = create_message(
            author_membership=sender_membership,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            client_message_id=client_message_id,
            body="once",
        )

    assert result.created is False
    mock_fanout.assert_not_called()
    mock_notif.assert_not_called()


def test_http_send_rejects_empty_body(api_client):
    establishment, sender, _receiver, _sender_membership, receiver_membership = _setup_dm()
    token = login(api_client, user=sender)
    dm = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    response = send_message(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=dm.json()["conversation"]["id"],
        body="   ",
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_http_send_rejects_outsider(api_client):
    establishment, sender, _receiver, _sender_membership, receiver_membership = _setup_dm()
    outsider = create_user(username="chat_http_outsider")
    create_membership(user=outsider, establishment=establishment)
    token = login(api_client, user=sender)
    dm = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    outsider_token = login(api_client, user=outsider)
    response = send_message(
        api_client,
        token=outsider_token,
        establishment_id=establishment.id,
        conversation_id=dm.json()["conversation"]["id"],
        body="nope",
    )
    assert response.status_code == 404


def test_mentions_and_reply_validation(api_client):
    establishment, sender, receiver, sender_membership, receiver_membership = _setup_dm()
    token = login(api_client, user=sender)
    dm = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=receiver_membership.id,
    )
    conversation_id = uuid.UUID(dm.json()["conversation"]["id"])
    label = f"@{membership_display_name(receiver_membership)}"
    body = f"hello {label} and {label}"
    first_start = body.index(label)
    first_end = first_start + len(label)
    second_start = body.index(label, first_end)
    second_end = second_start + len(label)

    parent = create_message(
        author_membership=sender_membership,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        client_message_id=uuid.uuid4(),
        body="parent",
    ).message

    ok = send_message(
        api_client,
        token=token,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        body=body,
        reply_to_id=parent.id,
        mentions=[
            {
                "membership_id": str(receiver_membership.id),
                "start": first_start,
                "end": first_end,
            },
            {
                "membership_id": str(receiver_membership.id),
                "start": second_start,
                "end": second_end,
            },
        ],
    )
    assert ok.status_code == 201
    payload = ok.json()["message"]
    assert payload["is_reply"] is True
    assert payload["reply_to"]["unavailable"] is False
    assert payload["reply_to"]["excerpt"] == "parent"
    assert len(payload["mentions"]) == 2
    assert ChatMessageMention.objects.filter(message_id=payload["id"]).count() == 2

    with pytest.raises(ChatValidationError):
        create_message(
            author_membership=sender_membership,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            client_message_id=uuid.uuid4(),
            body=body,
            mentions=[{"membership_id": receiver_membership.id, "start": -1, "end": 1}],
        )
    with pytest.raises(ChatValidationError):
        create_message(
            author_membership=sender_membership,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            client_message_id=uuid.uuid4(),
            body=body,
            mentions=[
                {
                    "membership_id": receiver_membership.id,
                    "start": first_start,
                    "end": first_end,
                },
                {
                    "membership_id": receiver_membership.id,
                    "start": first_start + 1,
                    "end": first_end + 1,
                },
            ],
        )
    outsider = create_user(username="chat_mention_inactive")
    outsider_membership = create_membership(user=outsider, establishment=establishment)
    with pytest.raises(ChatValidationError):
        create_message(
            author_membership=sender_membership,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            client_message_id=uuid.uuid4(),
            body=f"@{membership_display_name(outsider_membership)}",
            mentions=[
                {
                    "membership_id": outsider_membership.id,
                    "start": 0,
                    "end": len(f"@{membership_display_name(outsider_membership)}"),
                }
            ],
        )
    with pytest.raises(ChatValidationError):
        create_message(
            author_membership=sender_membership,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            client_message_id=uuid.uuid4(),
            body=body,
            mentions=[
                {
                    "membership_id": receiver_membership.id,
                    "start": first_start,
                    "end": first_end - 1,
                }
            ],
        )
    with pytest.raises(ChatValidationError):
        create_message(
            author_membership=sender_membership,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            client_message_id=uuid.uuid4(),
            body="reply missing parent",
            reply_to_id=uuid.uuid4(),
        )
    _ = receiver


@pytest.mark.django_db(transaction=True)
def test_message_created_fanout_is_on_commit_only():
    establishment, sender, _receiver, sender_membership, receiver_membership = _setup_dm()
    from houston.chat.services import create_or_get_dm_conversation

    conversation, _created = create_or_get_dm_conversation(
        actor_membership=sender_membership,
        target_membership_id=receiver_membership.id,
    )

    with patch("houston.chat.ws_notify.notify_message_created") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                create_message(
                    author_membership=sender_membership,
                    establishment_id=establishment.id,
                    conversation_id=conversation.id,
                    client_message_id=uuid.uuid4(),
                    body="rolled back",
                )
                raise RuntimeError("force rollback")
        mock_notify.assert_not_called()

    with patch("houston.chat.ws_notify.notify_message_created") as mock_notify:
        result = create_message(
            author_membership=sender_membership,
            establishment_id=establishment.id,
            conversation_id=conversation.id,
            client_message_id=uuid.uuid4(),
            body="committed",
        )
        mock_notify.assert_called_once()
        assert result.created is True
