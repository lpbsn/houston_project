"""Append-only ActionPlanExecution lifecycle journal helpers.

Business services must only insert via ``record_execution_lifecycle_event``.
Never update or delete ``ActionPlanExecutionLifecycleEvent`` rows from domain services.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_TYPE_VALUES,
    EXECUTION_LIFECYCLE_METADATA_SAFE_KEYS,
)
from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionLifecycleEvent
from houston.establishments.models import EstablishmentMembership


def sanitize_lifecycle_metadata_safe(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Keep only allowlisted structured keys; stringify UUID-like values."""
    if not metadata:
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        if key not in EXECUTION_LIFECYCLE_METADATA_SAFE_KEYS:
            continue
        if value is None:
            continue
        if isinstance(value, UUID):
            safe[key] = str(value)
        elif isinstance(value, (str, int, float, bool)):
            safe[key] = value
        else:
            # Reject nested objects / lists — keep journal free of free-form payloads.
            continue
    return safe


def record_execution_lifecycle_event(
    *,
    execution: ActionPlanExecution,
    event_type: str,
    occurred_at: datetime,
    actor_membership: EstablishmentMembership | None = None,
    metadata_safe: dict[str, Any] | None = None,
) -> ActionPlanExecutionLifecycleEvent:
    """Insert-only lifecycle event. Caller must be inside the transition transaction."""
    if event_type not in EXECUTION_LIFECYCLE_EVENT_TYPE_VALUES:
        raise ValueError(f"Unsupported execution lifecycle event_type: {event_type}")
    return ActionPlanExecutionLifecycleEvent.objects.create(
        action_plan_execution=execution,
        establishment_id=execution.establishment_id,
        event_type=event_type,
        actor_membership=actor_membership,
        occurred_at=occurred_at,
        metadata_safe=sanitize_lifecycle_metadata_safe(metadata_safe),
    )
