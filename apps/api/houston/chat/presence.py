from __future__ import annotations

import uuid

from django.core.cache import cache

CHAT_PRESENCE_TTL_SECONDS = 45


def _presence_cache_key(
    *,
    membership_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> str:
    return f"chat:presence:{membership_id}:{conversation_id}"


def touch_chat_presence(
    *,
    membership_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> None:
    cache_key = _presence_cache_key(
        membership_id=membership_id,
        conversation_id=conversation_id,
    )
    cache.set(cache_key, 1, timeout=CHAT_PRESENCE_TTL_SECONDS)


def is_chat_presence_active(
    *,
    membership_id: uuid.UUID,
    conversation_id: uuid.UUID,
) -> bool:
    cache_key = _presence_cache_key(
        membership_id=membership_id,
        conversation_id=conversation_id,
    )
    return cache.get(cache_key) is not None
