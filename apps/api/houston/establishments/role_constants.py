from __future__ import annotations

from houston.establishments.models import EstablishmentMembership

ADMIN_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }
)
_INVITATION_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
    }
)
_ACTION_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
    }
)
_MANAGEMENT_ROLES = _ACTION_ROLES
_VALID_ROLES = frozenset(choice for choice, _ in EstablishmentMembership.Role.choices)
