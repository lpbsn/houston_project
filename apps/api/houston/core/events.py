from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Mapping
from uuid import UUID

from django.utils import timezone

EventCategory = Literal["business", "technical", "ai", "audit", "system"]


@dataclass(frozen=True)
class EventEnvelope:
    event_type: str
    category: EventCategory
    subject_type: str
    subject_id: UUID
    correlation_id: UUID
    payload: Mapping[str, Any] = field(default_factory=dict)
    organization_id: UUID | None = None
    establishment_id: UUID | None = None
    actor_id: UUID | None = None
    causation_id: UUID | None = None
    idempotency_key: str | None = None
    event_version: int = 1
    id: UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=timezone.now)
