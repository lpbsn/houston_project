"""Append-only Signal lifecycle journal helpers.

Business services must only insert via ``record_signal_lifecycle_event``.
Never update or delete ``SignalLifecycleEvent`` rows from domain services.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from houston.establishments.models import EstablishmentMembership
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_TYPE_VALUES,
    SIGNAL_LIFECYCLE_METADATA_SAFE_KEYS,
)
from houston.signals.models import Signal, SignalLifecycleEvent


def sanitize_lifecycle_metadata_safe(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Keep only allowlisted structured keys; stringify UUID-like values."""
    if not metadata:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if key not in SIGNAL_LIFECYCLE_METADATA_SAFE_KEYS:
            continue
        if value is None:
            continue
        if isinstance(value, UUID):
            safe[key] = str(value)
        elif isinstance(value, datetime):
            safe[key] = value.isoformat()
        elif isinstance(value, (str, int, float, bool)):
            safe[key] = value
        else:
            # Reject nested objects / lists — keep journal free of free-form payloads.
            continue
    return safe


def record_signal_lifecycle_event(
    *,
    signal: Signal,
    event_type: str,
    occurred_at: datetime,
    actor_membership: EstablishmentMembership | None = None,
    metadata_safe: dict[str, Any] | None = None,
) -> SignalLifecycleEvent:
    """Insert-only lifecycle event. Caller must be inside the transition transaction."""
    if event_type not in SIGNAL_LIFECYCLE_EVENT_TYPE_VALUES:
        raise ValueError(f"Unsupported signal lifecycle event_type: {event_type}")
    return SignalLifecycleEvent.objects.create(
        signal=signal,
        establishment_id=signal.establishment_id,
        event_type=event_type,
        actor_membership=actor_membership,
        occurred_at=occurred_at,
        metadata_safe=sanitize_lifecycle_metadata_safe(metadata_safe),
    )
