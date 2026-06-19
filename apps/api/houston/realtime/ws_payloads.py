from __future__ import annotations

from datetime import datetime
from uuid import UUID

from django.utils import timezone


def build_auth_ok_payload(
    *,
    membership_id: UUID,
    session_id: UUID,
) -> dict:
    return {
        "type": "auth.ok",
        "membership_id": str(membership_id),
        "session_id": str(session_id),
    }


def build_invalidate_payload(
    *,
    subject_type: str,
    reason: str,
    establishment_id: UUID,
    entity_id: UUID,
    occurred_at: datetime | None = None,
) -> dict:
    return {
        "type": "invalidate",
        "subject_type": subject_type,
        "reason": reason,
        "establishment_id": str(establishment_id),
        "entity_id": str(entity_id),
        "occurred_at": (occurred_at or timezone.now()).isoformat(),
    }


def build_access_payload(
    *,
    reason: str,
    establishment_id: UUID | None = None,
    membership_id: UUID | None = None,
    occurred_at: datetime | None = None,
) -> dict:
    payload = {
        "type": "access",
        "reason": reason,
        "occurred_at": (occurred_at or timezone.now()).isoformat(),
    }
    if establishment_id is not None:
        payload["establishment_id"] = str(establishment_id)
    if membership_id is not None:
        payload["membership_id"] = str(membership_id)
    return payload
