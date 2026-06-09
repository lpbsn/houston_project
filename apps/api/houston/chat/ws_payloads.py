from __future__ import annotations

from uuid import UUID

from houston.chat.api.serializers import serialize_message
from houston.chat.models import ChatMessage


def serialize_message_for_ws(message: ChatMessage) -> dict:
    payload = serialize_message(message)
    return {
        "id": str(payload["id"]),
        "author_membership_id": str(payload["author_membership_id"]),
        "author_display_name": payload["author_display_name"],
        "body": payload["body"],
        "client_message_id": str(payload["client_message_id"]),
        "created_at": payload["created_at"].isoformat(),
    }


def build_message_created_payload(*, conversation_id: UUID, message: ChatMessage) -> dict:
    return {
        "type": "message.created",
        "conversation_id": str(conversation_id),
        "message": serialize_message_for_ws(message),
    }


def build_message_rejected_payload(
    *,
    client_message_id: UUID | None,
    code: str,
    detail: str,
) -> dict:
    payload = {
        "type": "message.rejected",
        "code": code,
        "detail": detail,
    }
    if client_message_id is not None:
        payload["client_message_id"] = str(client_message_id)
    return payload


def build_conversation_access_revoked_payload(
    *,
    conversation_id: UUID,
    reason: str,
) -> dict:
    return {
        "type": "conversation.access_revoked",
        "conversation_id": str(conversation_id),
        "reason": reason,
    }
