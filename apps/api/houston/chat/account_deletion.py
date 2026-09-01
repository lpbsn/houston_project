from __future__ import annotations

import uuid

from houston.chat.models import ChatMessage
from houston.chat.purge import _refresh_last_message_at


def delete_messages_authored_by_memberships(*, membership_ids: list[uuid.UUID]) -> None:
    if not membership_ids:
        return
    conversation_ids = list(
        ChatMessage.objects.filter(author_membership_id__in=membership_ids)
        .values_list("conversation_id", flat=True)
        .distinct()
    )
    ChatMessage.objects.filter(author_membership_id__in=membership_ids).delete()
    if conversation_ids:
        _refresh_last_message_at(conversation_ids=conversation_ids)
