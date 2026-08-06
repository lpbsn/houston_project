from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import OperationalPattern, PatternLifecycleEvent
from houston.establishments.models import EstablishmentMembership
from houston.organizations.models import Organization


@transaction.atomic
def create_operational_pattern(
    *,
    organization: Organization,
    label: str,
    created_by_membership: EstablishmentMembership | None = None,
    occurred_at=None,
    metadata_safe: dict[str, Any] | None = None,
) -> OperationalPattern:
    pattern = OperationalPattern(
        organization=organization,
        label=label,
        created_by_membership=created_by_membership,
    )
    try:
        pattern.full_clean(validate_unique=False, validate_constraints=False)
    except ValidationError as exc:
        raise AnalyticsValidationError(str(exc)) from exc
    pattern.save()

    event = PatternLifecycleEvent(
        pattern=pattern,
        organization=organization,
        event_type=PatternLifecycleEvent.EventType.CREATED,
        actor_membership=created_by_membership,
        occurred_at=occurred_at or timezone.now(),
        metadata_safe=metadata_safe or {},
    )
    try:
        event.full_clean(validate_unique=False, validate_constraints=False)
    except ValidationError as exc:
        raise AnalyticsValidationError(str(exc)) from exc
    event.save()

    return pattern
