from __future__ import annotations

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization

_ADMIN_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }
)
_ACTION_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
    }
)
_VALID_ROLES = frozenset(choice for choice, _ in EstablishmentMembership.Role.choices)


def can_access_app(membership: EstablishmentMembership | None) -> bool:
    return _is_valid_membership(membership)


def can_manage_establishment_settings(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, _ADMIN_ROLES)


def can_manage_memberships(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, _ADMIN_ROLES)


def can_manage_runtime_context(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, _ADMIN_ROLES)


def can_view_signal_feed(membership: EstablishmentMembership | None) -> bool:
    return _is_valid_membership(membership)


def can_create_observation(membership: EstablishmentMembership | None) -> bool:
    return _is_valid_membership(membership)


def can_create_action(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, _ACTION_ROLES)


def can_validate_action(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, _ACTION_ROLES)


def can_access_domain(
    membership: EstablishmentMembership | None,
    domain_key: str,
) -> bool:
    if not _is_valid_membership(membership):
        return False

    normalized_domain_key = _normalize_domain_key(domain_key)
    if normalized_domain_key is None:
        return False

    if membership.role in _ADMIN_ROLES:
        return True

    normalized_domains = _normalized_operational_domains(membership.operational_domains)
    if normalized_domains is None:
        return False

    return normalized_domain_key in normalized_domains


def _has_role(
    membership: EstablishmentMembership | None,
    allowed_roles: frozenset[str],
) -> bool:
    return _is_valid_membership(membership) and membership.role in allowed_roles


def _is_valid_membership(membership: EstablishmentMembership | None) -> bool:
    if membership is None:
        return False

    if membership.status != EstablishmentMembership.Status.ACTIVE:
        return False

    if membership.role not in _VALID_ROLES:
        return False

    user = getattr(membership, "user", None)
    if user is None or user.status != User.Status.ACTIVE:
        return False

    establishment = getattr(membership, "establishment", None)
    if establishment is None or establishment.status != Establishment.Status.ACTIVE:
        return False

    organization = getattr(establishment, "organization", None)
    if organization is None or organization.status != Organization.Status.ACTIVE:
        return False

    return True

def _normalize_domain_key(domain_key: str) -> str | None:
    if not isinstance(domain_key, str):
        return None

    normalized_domain_key = domain_key.strip()
    if not normalized_domain_key:
        return None

    return normalized_domain_key


def _normalized_operational_domains(value: object) -> set[str] | None:
    if not isinstance(value, list):
        return None

    normalized_domains: set[str] = set()
    for item in value:
        normalized_domain_key = _normalize_domain_key(item)
        if normalized_domain_key is None:
            return None
        normalized_domains.add(normalized_domain_key)

    return normalized_domains
