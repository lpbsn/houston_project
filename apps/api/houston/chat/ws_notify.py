from __future__ import annotations

import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from houston.chat.groups import membership_group_name, session_group_name
from houston.chat.ws_payloads import (
    build_conversation_access_revoked_payload,
    build_membership_access_revoked_payload,
)


def _send_access_revoked_to_group(
    *,
    group_name: str,
    handler_type: str,
    reason: str,
) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    payload = build_membership_access_revoked_payload(reason=reason)
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": handler_type,
            "payload": payload,
        },
    )


def notify_conversation_access_revoked(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
    conversation_id: uuid.UUID,
    reason: str,
) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    payload = build_conversation_access_revoked_payload(
        conversation_id=conversation_id,
        reason=reason,
    )
    async_to_sync(channel_layer.group_send)(
        membership_group_name(
            establishment_id=establishment_id,
            membership_id=membership_id,
        ),
        {
            "type": "chat.conversation.access_revoked",
            "payload": payload,
        },
    )


def notify_conversation_access_revoked_for_memberships(
    *,
    establishment_id: uuid.UUID,
    conversation_id: uuid.UUID,
    membership_ids: list[uuid.UUID],
    reason: str,
) -> None:
    for membership_id in membership_ids:
        notify_conversation_access_revoked(
            establishment_id=establishment_id,
            membership_id=membership_id,
            conversation_id=conversation_id,
            reason=reason,
        )


def schedule_conversation_access_revoked(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
    conversation_id: uuid.UUID,
    reason: str,
) -> None:
    transaction.on_commit(
        lambda: notify_conversation_access_revoked(
            establishment_id=establishment_id,
            membership_id=membership_id,
            conversation_id=conversation_id,
            reason=reason,
        )
    )


def notify_membership_access_revoked(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
    reason: str,
) -> None:
    _send_access_revoked_to_group(
        group_name=membership_group_name(
            establishment_id=establishment_id,
            membership_id=membership_id,
        ),
        handler_type="chat.membership.access_revoked",
        reason=reason,
    )


def notify_session_access_revoked(
    *,
    session_id: uuid.UUID,
    reason: str,
) -> None:
    _send_access_revoked_to_group(
        group_name=session_group_name(session_id=session_id),
        handler_type="chat.session.access_revoked",
        reason=reason,
    )


def schedule_membership_access_revoked(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
    reason: str,
) -> None:
    transaction.on_commit(
        lambda: notify_membership_access_revoked(
            establishment_id=establishment_id,
            membership_id=membership_id,
            reason=reason,
        )
    )


def schedule_session_access_revoked(
    *,
    session_id: uuid.UUID,
    reason: str,
) -> None:
    transaction.on_commit(
        lambda: notify_session_access_revoked(
            session_id=session_id,
            reason=reason,
        )
    )


def schedule_conversation_access_revoked_for_memberships(
    *,
    establishment_id: uuid.UUID,
    conversation_id: uuid.UUID,
    membership_ids: list[uuid.UUID],
    reason: str,
) -> None:
    captured_membership_ids = list(membership_ids)

    def _notify() -> None:
        notify_conversation_access_revoked_for_memberships(
            establishment_id=establishment_id,
            conversation_id=conversation_id,
            membership_ids=captured_membership_ids,
            reason=reason,
        )

    transaction.on_commit(_notify)
