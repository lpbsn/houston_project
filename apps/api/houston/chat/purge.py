from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from houston.chat.constants import CHAT_MESSAGE_RETENTION_DAYS, CHAT_PURGE_BATCH_SIZE
from houston.chat.models import ChatConversation, ChatMessage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatPurgeResult:
    deleted_count: int
    batch_count: int
    dry_run: bool


def _purge_cutoff():
    retention_days = getattr(
        settings,
        "HOUSTON_CHAT_MESSAGE_RETENTION_DAYS",
        CHAT_MESSAGE_RETENTION_DAYS,
    )
    return timezone.now() - timedelta(days=retention_days)


def _messages_to_purge_queryset(*, establishment_id: uuid.UUID | None = None):
    queryset = ChatMessage.objects.filter(created_at__lt=_purge_cutoff())
    if establishment_id is not None:
        queryset = queryset.filter(conversation__establishment_id=establishment_id)
    return queryset


def _refresh_last_message_at(*, conversation_ids: list[uuid.UUID]) -> None:
    now = timezone.now()
    for conversation_id in conversation_ids:
        latest_message = (
            ChatMessage.objects.filter(conversation_id=conversation_id)
            .order_by("-created_at", "-id")
            .first()
        )
        ChatConversation.objects.filter(id=conversation_id).update(
            last_message_at=latest_message.created_at if latest_message else None,
            updated_at=now,
        )


def purge_chat_messages(
    *,
    establishment_id: uuid.UUID | None = None,
    dry_run: bool = False,
    batch_size: int | None = None,
) -> ChatPurgeResult:
    effective_batch_size = batch_size or getattr(
        settings,
        "HOUSTON_CHAT_PURGE_BATCH_SIZE",
        CHAT_PURGE_BATCH_SIZE,
    )

    if dry_run:
        deleted_count = _messages_to_purge_queryset(establishment_id=establishment_id).count()
        return ChatPurgeResult(deleted_count=deleted_count, batch_count=0, dry_run=True)

    total_deleted = 0
    batch_count = 0

    while True:
        message_ids = list(
            _messages_to_purge_queryset(establishment_id=establishment_id)
            .order_by("created_at", "id")
            .values_list("id", flat=True)[:effective_batch_size]
        )
        if not message_ids:
            break

        conversation_ids = list(
            ChatMessage.objects.filter(id__in=message_ids)
            .values_list("conversation_id", flat=True)
            .distinct()
        )
        deleted_count, _ = ChatMessage.objects.filter(id__in=message_ids).delete()
        total_deleted += deleted_count
        batch_count += 1
        _refresh_last_message_at(conversation_ids=conversation_ids)

        logger.info(
            "Purged chat messages batch",
            extra={
                "establishment_id": str(establishment_id) if establishment_id else None,
                "deleted_count": deleted_count,
                "batch": batch_count,
            },
        )

    return ChatPurgeResult(
        deleted_count=total_deleted,
        batch_count=batch_count,
        dry_run=False,
    )
