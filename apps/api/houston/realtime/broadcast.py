from __future__ import annotations

import uuid

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from houston.realtime.groups import (
    establishment_group_name,
    membership_group_name,
    session_group_name,
)
from houston.realtime.ws_payloads import build_access_payload, build_invalidate_payload

SESSION_ACCESS_REASONS = frozenset({"session.revoked", "establishment.switched"})
MEMBERSHIP_ACCESS_REASONS = frozenset({"membership.deactivated", "membership.updated"})


def _send_to_group(*, group_name: str, handler_type: str, payload: dict) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": handler_type,
            "payload": payload,
        },
    )


def notify_establishment_invalidation(
    *,
    establishment_id: uuid.UUID,
    subject_type: str,
    reason: str,
    entity_id: uuid.UUID,
) -> None:
    payload = build_invalidate_payload(
        subject_type=subject_type,
        reason=reason,
        establishment_id=establishment_id,
        entity_id=entity_id,
    )
    _send_to_group(
        group_name=establishment_group_name(establishment_id=establishment_id),
        handler_type="realtime.invalidation",
        payload=payload,
    )


def schedule_establishment_invalidation(
    *,
    establishment_id: uuid.UUID,
    subject_type: str,
    reason: str,
    entity_id: uuid.UUID,
) -> None:
    transaction.on_commit(
        lambda: notify_establishment_invalidation(
            establishment_id=establishment_id,
            subject_type=subject_type,
            reason=reason,
            entity_id=entity_id,
        )
    )


def notify_membership_invalidation(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
    subject_type: str,
    reason: str,
    entity_id: uuid.UUID,
) -> None:
    payload = build_invalidate_payload(
        subject_type=subject_type,
        reason=reason,
        establishment_id=establishment_id,
        entity_id=entity_id,
    )
    _send_to_group(
        group_name=membership_group_name(
            establishment_id=establishment_id,
            membership_id=membership_id,
        ),
        handler_type="realtime.invalidation",
        payload=payload,
    )


def schedule_membership_invalidation(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
    subject_type: str,
    reason: str,
    entity_id: uuid.UUID,
) -> None:
    transaction.on_commit(
        lambda: notify_membership_invalidation(
            establishment_id=establishment_id,
            membership_id=membership_id,
            subject_type=subject_type,
            reason=reason,
            entity_id=entity_id,
        )
    )


def notify_access_event(
    *,
    reason: str,
    establishment_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    membership_id: uuid.UUID | None = None,
) -> None:
    if reason in SESSION_ACCESS_REASONS:
        if session_id is None:
            return
        group_name = session_group_name(session_id=session_id)
        payload_membership_id = None
    elif reason in MEMBERSHIP_ACCESS_REASONS:
        if membership_id is None:
            return
        group_name = membership_group_name(
            establishment_id=establishment_id,
            membership_id=membership_id,
        )
        payload_membership_id = membership_id
    else:
        return

    payload = build_access_payload(
        reason=reason,
        establishment_id=establishment_id,
        membership_id=payload_membership_id,
    )
    _send_to_group(
        group_name=group_name,
        handler_type="realtime.access",
        payload=payload,
    )


def schedule_access_event(
    *,
    reason: str,
    establishment_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    membership_id: uuid.UUID | None = None,
) -> None:
    transaction.on_commit(
        lambda: notify_access_event(
            reason=reason,
            establishment_id=establishment_id,
            session_id=session_id,
            membership_id=membership_id,
        )
    )
