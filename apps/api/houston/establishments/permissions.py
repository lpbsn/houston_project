from __future__ import annotations

from rest_framework.permissions import BasePermission

from houston.accounts.models import User
from houston.establishments.access import get_api_access_context
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
)
from houston.organizations.models import Organization

_ADMIN_ROLES = frozenset(
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
_VALID_ROLES = frozenset(choice for choice, _ in EstablishmentMembership.Role.choices)


def can_access_app(membership: EstablishmentMembership | None) -> bool:
    return _is_valid_membership(membership)


def can_manage_establishment_settings(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, _ADMIN_ROLES)


def can_manage_memberships(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, _ADMIN_ROLES)


def can_invite_memberships(membership: EstablishmentMembership | None) -> bool:
    return _is_valid_invitation_membership(membership) and membership.role in _INVITATION_ROLES


def can_manage_runtime_context(membership: EstablishmentMembership | None) -> bool:
    """Owner/Director on an active establishment in workspace (session-selected) context.

    Intended for post-activation runtime administration APIs. Onboarding-session routes use
    ``get_onboarding_access_context`` instead (path-scoped session, draft/active establishment).
    """
    return _has_role(membership, _ADMIN_ROLES)


def can_view_signal_feed(membership: EstablishmentMembership | None) -> bool:
    return _is_valid_membership(membership)


def can_create_observation(membership: EstablishmentMembership | None) -> bool:
    return _is_valid_membership(membership)


def can_create_action(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, _ACTION_ROLES)


def can_validate_action(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, _ACTION_ROLES)


def _has_role(
    membership: EstablishmentMembership | None,
    allowed_roles: frozenset[str],
) -> bool:
    return _is_valid_membership(membership) and membership.role in allowed_roles


def _is_valid_invitation_membership(membership: EstablishmentMembership | None) -> bool:
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
    if establishment is None or establishment.status not in {
        Establishment.Status.ACTIVE,
        Establishment.Status.DRAFT,
    }:
        return False

    organization = getattr(establishment, "organization", None)
    if organization is None or organization.status != Organization.Status.ACTIVE:
        return False

    return True


def _is_valid_membership(membership: EstablishmentMembership | None) -> bool:
    if not _is_valid_invitation_membership(membership):
        return False

    establishment = membership.establishment
    if establishment.status != Establishment.Status.ACTIVE:
        return False

    return True


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


class CanInviteMemberships(BasePermission):
    message = "You do not have permission to invite memberships."

    def has_permission(self, request, view) -> bool:
        access_context = get_api_access_context(request)
        return can_invite_memberships(access_context.active_membership)


class CanManageRuntimeContext(BasePermission):
    """DRF guard for active-establishment runtime context; not used on onboarding-session views."""

    message = "You do not have permission to manage runtime context."

    def has_permission(self, request, view) -> bool:
        access_context = get_api_access_context(request)
        return can_manage_runtime_context(access_context.active_membership)
