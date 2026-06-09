from __future__ import annotations

import uuid

from django.conf import settings
from django.core.cache import cache
from houston.chat.constants import CHAT_MESSAGE_SEND_RATE_LIMIT_PER_MINUTE


class ChatMessageRateLimitExceeded(Exception):
    pass


def _message_send_rate_limit() -> int:
    return int(
        getattr(
            settings,
            "HOUSTON_CHAT_MESSAGE_SEND_RATE_LIMIT_PER_MINUTE",
            CHAT_MESSAGE_SEND_RATE_LIMIT_PER_MINUTE,
        )
    )


def _message_send_rate_cache_key(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> str:
    return f"chat:msg_rate:{establishment_id}:{membership_id}"


def check_message_send_rate_limit(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> None:
    if not getattr(settings, "HOUSTON_CHAT_RATE_LIMIT_ENABLED", True):
        return

    cache_key = _message_send_rate_cache_key(
        establishment_id=establishment_id,
        membership_id=membership_id,
    )
    added = cache.add(cache_key, 1, timeout=60)
    if added:
        return

    try:
        current_count = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=60)
        return

    if current_count > _message_send_rate_limit():
        raise ChatMessageRateLimitExceeded()
