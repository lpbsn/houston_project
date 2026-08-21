from __future__ import annotations

import uuid
from typing import Any

from houston.establishments.access import get_api_access_context
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import can_create_observation


def resolve_observation_actor_membership(
    request: Any,
    *,
    establishment_id: uuid.UUID,
) -> EstablishmentMembership | None:
    access_context = get_api_access_context(request)
    membership = access_context.membership_for_establishment(establishment_id)
    if membership is None:
        return None
    if not can_create_observation(membership):
        return None
    return membership
