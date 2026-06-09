from __future__ import annotations

import uuid
from typing import Any

from houston.establishments.access import get_api_access_context
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import _is_valid_membership

from .permissions import can_access_chat


def _resolve_establishment_membership(
    request: Any,
    *,
    establishment_id: uuid.UUID,
) -> EstablishmentMembership | None:
    access_context = get_api_access_context(request)
    membership = access_context.active_membership
    if membership is None:
        return None
    if membership.establishment_id != establishment_id:
        return None
    if not _is_valid_membership(membership):
        return None
    return membership


def resolve_chat_actor_membership(
    request: Any,
    *,
    establishment_id: uuid.UUID,
) -> EstablishmentMembership | None:
    membership = _resolve_establishment_membership(
        request,
        establishment_id=establishment_id,
    )
    if membership is None:
        return None
    if not can_access_chat(membership):
        return None
    return membership


def resolve_chat_settings_actor_membership(
    request: Any,
    *,
    establishment_id: uuid.UUID,
) -> EstablishmentMembership | None:
    return _resolve_establishment_membership(
        request,
        establishment_id=establishment_id,
    )
