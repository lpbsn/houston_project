from __future__ import annotations

from rest_framework.permissions import BasePermission

from houston.accounts.models import User
from houston.establishments.access import get_api_access_context
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipDomain,
    OperationalDomain,
)
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

    domain = (
        OperationalDomain.objects.filter(
            establishment=membership.establishment,
            key=normalized_domain_key,
            active=True,
        )
        .only("id")
        .first()
    )
    if domain is None:
        return False

    if membership.role in _ADMIN_ROLES:
        return True

    return MembershipDomain.objects.filter(
        membership=membership,
        operational_domain=domain,
    ).exists()


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


def _normalize_domain_key(domain_key: str | None) -> str | None:
    if not isinstance(domain_key, str):
        return None

    normalized_domain_key = domain_key.strip()
    if not normalized_domain_key:
        return None

    return normalized_domain_key


class HasActiveMembership(BasePermission):
    message = "An active establishment membership is required."

    def has_permission(self, request, view) -> bool:
        access_context = get_api_access_context(request)
        return bool(access_context.active_memberships)


class CanManageMemberships(BasePermission):
    message = "You do not have permission to manage memberships."

    def has_permission(self, request, view) -> bool:
        access_context = get_api_access_context(request)
        return can_manage_memberships(access_context.active_membership)


class CanManageRuntimeContext(BasePermission):
    message = "You do not have permission to manage runtime context."

    def has_permission(self, request, view) -> bool:
        access_context = get_api_access_context(request)
        return can_manage_runtime_context(access_context.active_membership)
