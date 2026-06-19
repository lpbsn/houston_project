from __future__ import annotations

from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import _is_valid_membership


def can_access_operational_realtime(membership: EstablishmentMembership | None) -> bool:
    return _is_valid_membership(membership)
