from __future__ import annotations

import uuid

import pytest
from django.core.cache import cache
from houston.chat.presence import (
    is_chat_presence_active,
    touch_chat_presence,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_touch_chat_presence_sets_active_flag():
    membership_id = uuid.uuid4()
    conversation_id = uuid.uuid4()

    touch_chat_presence(membership_id=membership_id, conversation_id=conversation_id)

    assert is_chat_presence_active(
        membership_id=membership_id,
        conversation_id=conversation_id,
    )


def test_chat_presence_is_scoped_per_membership_and_conversation():
    membership_a = uuid.uuid4()
    membership_b = uuid.uuid4()
    conversation_a = uuid.uuid4()
    conversation_b = uuid.uuid4()

    touch_chat_presence(membership_id=membership_a, conversation_id=conversation_a)

    assert is_chat_presence_active(membership_id=membership_a, conversation_id=conversation_a)
    assert not is_chat_presence_active(membership_id=membership_b, conversation_id=conversation_a)
    assert not is_chat_presence_active(membership_id=membership_a, conversation_id=conversation_b)


def test_chat_presence_uses_expected_cache_key_and_ttl():
    membership_id = uuid.uuid4()
    conversation_id = uuid.uuid4()
    cache_key = f"chat:presence:{membership_id}:{conversation_id}"

    touch_chat_presence(membership_id=membership_id, conversation_id=conversation_id)

    assert cache.get(cache_key) == 1
    assert is_chat_presence_active(
        membership_id=membership_id,
        conversation_id=conversation_id,
    )
