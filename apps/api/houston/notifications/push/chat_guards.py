from __future__ import annotations

import uuid

from django.core.cache import cache

CHAT_PUSH_THROTTLE_TTL_SECONDS = 120


def _chat_push_throttle_cache_key(
    *,
    conversation_id: uuid.UUID,
    recipient_membership_id: uuid.UUID,
) -> str:
    return f"push:chat:{conversation_id}:{recipient_membership_id}"


def claim_chat_push_throttle(
    *,
    conversation_id: uuid.UUID,
    recipient_membership_id: uuid.UUID,
    owner_token: str,
) -> bool:
    cache_key = _chat_push_throttle_cache_key(
        conversation_id=conversation_id,
        recipient_membership_id=recipient_membership_id,
    )
    return cache.add(cache_key, owner_token, timeout=CHAT_PUSH_THROTTLE_TTL_SECONDS)


def release_chat_push_throttle(
    *,
    conversation_id: uuid.UUID,
    recipient_membership_id: uuid.UUID,
    owner_token: str,
) -> None:
    cache_key = _chat_push_throttle_cache_key(
        conversation_id=conversation_id,
        recipient_membership_id=recipient_membership_id,
    )
    if cache.get(cache_key) == owner_token:
        cache.delete(cache_key)
