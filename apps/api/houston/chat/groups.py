from __future__ import annotations

from uuid import UUID


def membership_group_name(*, establishment_id: UUID, membership_id: UUID) -> str:
    return f"chat_est_{establishment_id}_mbr_{membership_id}"


def conversation_group_name(*, establishment_id: UUID, conversation_id: UUID) -> str:
    return f"chat_est_{establishment_id}_conv_{conversation_id}"
