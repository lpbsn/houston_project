from __future__ import annotations

import uuid

import pytest
from houston.chat.exceptions import ChatNotFoundError, ChatValidationError
from houston.chat.models import ChatMessage
from houston.chat.services import create_message
from houston.chat.tests.conftest import (
    create_establishment,
    create_membership,
    create_user,
    login,
)
from houston.chat.tests.test_rest_api import create_dm
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_create_message_requires_active_participation():
    establishment = create_establishment()
    author = create_user(username="chat_service_author")
    target = create_user(username="chat_service_target")
    outsider = create_user(username="chat_service_outsider")
    author_membership = create_membership(user=author, establishment=establishment)
    target_membership = create_membership(user=target, establishment=establishment)
    outsider_membership = create_membership(user=outsider, establishment=establishment)

    api_client = APIClient()
    token = login(api_client, user=author)
    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=target_membership.id,
    )
    conversation_id = uuid.UUID(dm_response.json()["conversation"]["id"])

    with pytest.raises(ChatNotFoundError):
        create_message(
            author_membership=outsider_membership,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            client_message_id=uuid.uuid4(),
            body="blocked",
        )

    result = create_message(
        author_membership=author_membership,
        establishment_id=establishment.id,
        conversation_id=conversation_id,
        client_message_id=uuid.uuid4(),
        body="allowed",
    )
    assert result.created is True
    assert ChatMessage.objects.filter(conversation_id=conversation_id).count() == 1


def test_create_message_rejects_invalid_body():
    establishment = create_establishment()
    author = create_user(username="chat_service_invalid_body")
    target = create_user(username="chat_service_invalid_target")
    author_membership = create_membership(user=author, establishment=establishment)
    target_membership = create_membership(user=target, establishment=establishment)

    api_client = APIClient()
    token = login(api_client, user=author)
    dm_response = create_dm(
        api_client,
        token=token,
        establishment_id=establishment.id,
        target_membership_id=target_membership.id,
    )
    conversation_id = uuid.UUID(dm_response.json()["conversation"]["id"])

    with pytest.raises(ChatValidationError):
        create_message(
            author_membership=author_membership,
            establishment_id=establishment.id,
            conversation_id=conversation_id,
            client_message_id=uuid.uuid4(),
            body=" ",
        )


def test_create_message_not_found_for_unknown_conversation():
    establishment = create_establishment()
    author = create_user(username="chat_service_missing_conv")
    author_membership = create_membership(user=author, establishment=establishment)

    with pytest.raises(ChatNotFoundError):
        create_message(
            author_membership=author_membership,
            establishment_id=establishment.id,
            conversation_id=uuid.uuid4(),
            client_message_id=uuid.uuid4(),
            body="missing",
        )
