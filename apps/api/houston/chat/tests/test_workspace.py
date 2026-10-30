import uuid

import pytest
from django.utils import timezone
from houston.chat.exceptions import ChatNotFoundError
from houston.chat.message_tools import (
    acknowledge_message,
    observation_from_message,
    require_message,
    set_conversation_notifications,
)
from houston.chat.models import (
    ChatMessage,
    ChatMessageMention,
    ChatObservationSource,
    ChatParticipant,
)
from houston.chat.services import create_or_get_dm_conversation
from houston.chat.workspace_selectors import communication_search
from houston.notifications.discussion_preferences import chat_message_notification_allowed
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_establishment, create_membership

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup_chat():
    site = create_establishment()
    author = create_membership(establishment=site, role="owner")
    peer = create_membership(establishment=site, role="staff")
    conversation, _ = create_or_get_dm_conversation(
        actor_membership=author, target_membership_id=peer.id
    )
    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=author,
        body="Les affiches de livraison sont absentes.",
        client_message_id=uuid.uuid4(),
    )
    return author, peer, conversation, message


def test_private_history_is_not_exposed_by_search_or_tools(setup_chat):
    author, peer, conversation, message = setup_chat
    outsider = create_membership(establishment=author.establishment, role="owner")
    assert communication_search(membership=outsider, query="livraison")["items"] == []
    with pytest.raises(ChatNotFoundError):
        require_message(membership=outsider, message_id=message.id)
    ChatParticipant.objects.filter(conversation=conversation, membership=peer).update(
        history_cutoff_at=timezone.now()
    )
    assert communication_search(membership=peer, query="livraison")["items"] == []
    with pytest.raises(ChatNotFoundError):
        acknowledge_message(membership=peer, message_id=message.id, active=True)
    assert len(communication_search(membership=author, query="livraison")["items"]) == 1


def test_departed_or_disabled_user_cannot_use_tools(setup_chat):
    author, peer, conversation, message = setup_chat
    ChatParticipant.objects.filter(conversation=conversation, membership=peer).update(
        left_at=timezone.now()
    )
    with pytest.raises(ChatNotFoundError):
        observation_from_message(membership=peer, message_id=message.id, text=message.body)
    author.status = "deactivated"
    author.save(update_fields=["status"])
    assert communication_search(membership=author)["items"] == []


def test_acknowledgement_is_idempotent_and_does_not_mean_execution(setup_chat):
    _, peer, _, message = setup_chat
    acknowledge_message(membership=peer, message_id=message.id, active=True)
    acknowledge_message(membership=peer, message_id=message.id, active=True)
    assert message.acknowledgements.count() == 1
    acknowledge_message(membership=peer, message_id=message.id, active=False)
    assert message.acknowledgements.count() == 0


def test_explicit_handoff_is_unique_and_survives_message_purge(setup_chat):
    author, peer, _, message = setup_chat
    source = observation_from_message(membership=author, message_id=message.id, text=message.body)
    again = observation_from_message(membership=peer, message_id=message.id, text=message.body)
    assert source.id == again.id
    assert source.source_author == author
    original_id = message.id
    message.delete()
    source.refresh_from_db()
    assert source.message_id is None
    assert source.source_message_id == original_id
    assert source.observation.raw_text == "Les affiches de livraison sont absentes."
    assert ChatObservationSource.objects.count() == 1


def test_mentions_and_silent_modes_filter_notifications(setup_chat):
    _, peer, conversation, message = setup_chat
    set_conversation_notifications(
        membership=peer, conversation_id=conversation.id, mode="mentions"
    )
    assert not chat_message_notification_allowed(message=message, membership_id=peer.id)
    ChatMessageMention.objects.create(message=message, membership=peer, start=0, end=1)
    assert chat_message_notification_allowed(message=message, membership_id=peer.id)
    set_conversation_notifications(membership=peer, conversation_id=conversation.id, mode="silent")
    assert not chat_message_notification_allowed(message=message, membership_id=peer.id)
    assert len(communication_search(membership=peer, mentions=True)["items"]) == 1


def test_search_pagination_does_not_repeat_messages(setup_chat):
    author, _, conversation, _ = setup_chat
    for i in range(35):
        ChatMessage.objects.create(
            conversation=conversation,
            author_membership=author,
            body=f"Livraison numéro {i}",
            client_message_id=uuid.uuid4(),
        )
    first = communication_search(membership=author, query="livraison")
    from houston.chat.api.views import _parse_message_cursor

    second = communication_search(
        membership=author, query="livraison", cursor=_parse_message_cursor(first["cursor"])
    )
    assert len(first["items"]) == 30
    assert len(second["items"]) == 6
    assert not {r["id"] for r in first["items"]} & {r["id"] for r in second["items"]}
    assert second["cursor"] is None


def test_workspace_api_contract_and_tenant_boundary(api_client, setup_chat):
    author, _, _, message = setup_chat
    token = login(api_client, user=author.user)
    base = f"/api/v1/establishments/{author.establishment_id}/chat/"
    response = api_client.get(base + "workspace/?tab=search&q=livraison", **auth_headers(token))
    assert response.status_code == 200
    assert response.json()["items"][0]["id"] == str(message.id)
    assert (
        api_client.get(base + "workspace/?cursor=invalid", **auth_headers(token)).status_code == 400
    )
    assert (
        api_client.post(
            base + f"messages/{message.id}/tools/",
            {"operation": "observe"},
            format="json",
            **auth_headers(token),
        ).status_code
        == 400
    )
    other = create_establishment()
    assert api_client.get(
        f"/api/v1/establishments/{other.id}/chat/workspace/", **auth_headers(token)
    ).status_code in (403, 404)
