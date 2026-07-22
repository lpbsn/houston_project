from __future__ import annotations

from dataclasses import dataclass

from rest_framework.permissions import BasePermission

from houston.accounts.models import User
from houston.establishments.access import get_api_access_context
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
)
from houston.establishments.role_constants import (
    _ACTION_ROLES,
    _INVITATION_ROLES,
    _VALID_ROLES,
    ADMIN_ROLES,
)
from houston.organizations.models import Organization


@dataclass(frozen=True)
class EstablishmentAdminActor:
    """Path-scoped admin actor for establishment management (Lots C/D)."""

    user: User
    establishment: Establishment
    membership: EstablishmentMembership
    via_organization_owner: bool


def _manageable_owner_memberships_qs(*, user: User):
    return EstablishmentMembership.objects.filter(
        user_id=user.id,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
        establishment__status__in=[
            Establishment.Status.ACTIVE,
            Establishment.Status.DRAFT,
        ],
        establishment__organization__status=Organization.Status.ACTIVE,
    ).select_related("establishment", "establishment__organization")


def list_manageable_organizations(user: User | None) -> list[Organization]:
    """Organizations the user can manage as an ACTIVE Owner on DRAFT|ACTIVE establishments."""
    if user is None or user.status != User.Status.ACTIVE:
        return []

    org_ids = list(
        _manageable_owner_memberships_qs(user=user)
        .values_list("establishment__organization_id", flat=True)
        .distinct()
        .order_by("establishment__organization_id")
    )
    if not org_ids:
        return []

    organizations_by_id = Organization.objects.in_bulk(org_ids)
    return [organizations_by_id[org_id] for org_id in org_ids if org_id in organizations_by_id]


def resolve_manageable_organization(
    user: User | None,
    *,
    preferred_organization_id=None,
) -> Organization | None:
    """Resolve one manageable organization for mutations, or None (fail closed).

    Preference order:
    1. ``preferred_organization_id`` when the user can manage that org
    2. the unique manageable organization
    3. None when zero or multiple organizations are manageable without a valid preference
    """
    organizations = list_manageable_organizations(user)
    if not organizations:
        return None

    if preferred_organization_id is not None:
        for organization in organizations:
            if organization.id == preferred_organization_id:
                return organization
        return None

    if len(organizations) == 1:
        return organizations[0]

    return None


def can_manage_organization(
    user: User | None,
    *,
    organization_id=None,
) -> bool:
    """True when the user can manage at least one org, or the given org specifically."""
    if organization_id is not None:
        return resolve_manageable_organization(
            user,
            preferred_organization_id=organization_id,
        ) is not None
    return bool(list_manageable_organizations(user))


def can_access_app(membership: EstablishmentMembership | None) -> bool:
    return is_valid_membership(membership)


def can_manage_establishment_settings(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, ADMIN_ROLES)


def can_view_team_memberships(membership: EstablishmentMembership | None) -> bool:
    return is_valid_membership(membership)


def can_invite_memberships(membership: EstablishmentMembership | None) -> bool:
    return _is_valid_invitation_membership(membership) and membership.role in _INVITATION_ROLES


def can_manage_runtime_context(membership: EstablishmentMembership | None) -> bool:
    """Owner/Director on an active establishment in workspace (session-selected) context.

    Intended for post-activation runtime administration APIs. Onboarding-session routes use
    ``get_onboarding_access_context`` instead (path-scoped session, draft/active establishment).
    """
    return _has_role(membership, ADMIN_ROLES)


def can_create_establishment(
    user: User | None,
    *,
    preferred_organization_id=None,
) -> bool:
    """Owner org capability (ACTIVE|DRAFT) — independent of session selection for the hint."""
    if preferred_organization_id is not None:
        return resolve_manageable_organization(
            user,
            preferred_organization_id=preferred_organization_id,
        ) is not None
    return can_manage_organization(user)


def resolve_establishment_admin_actor(
    user: User | None,
    establishment_id,
) -> EstablishmentAdminActor | None:
    """Path-scoped admin: org Owner on the establishment, or Director ACTIVE on ACTIVE est."""
    if user is None or user.status != User.Status.ACTIVE:
        return None

    establishment = (
        Establishment.objects.select_related("organization")
        .filter(id=establishment_id)
        .first()
    )
    if establishment is None:
        return None
    if establishment.organization.status != Organization.Status.ACTIVE:
        return None

    if can_manage_organization(user, organization_id=establishment.organization_id):
        if establishment.status not in {
            Establishment.Status.ACTIVE,
            Establishment.Status.DRAFT,
        }:
            return None
        membership = (
            EstablishmentMembership.objects.select_related("user", "establishment")
            .filter(
                user_id=user.id,
                establishment_id=establishment.id,
                role=EstablishmentMembership.Role.OWNER,
                status=EstablishmentMembership.Status.ACTIVE,
            )
            .first()
        )
        if membership is None:
            # Org owner may not yet have a row on this establishment; still path-admin via org.
            membership = (
                _manageable_owner_memberships_qs(user=user)
                .filter(establishment__organization_id=establishment.organization_id)
                .first()
            )
        if membership is None:
            return None
        return EstablishmentAdminActor(
            user=user,
            establishment=establishment,
            membership=membership,
            via_organization_owner=True,
        )

    if establishment.status != Establishment.Status.ACTIVE:
        return None

    membership = (
        EstablishmentMembership.objects.select_related("user", "establishment")
        .filter(
            user_id=user.id,
            establishment_id=establishment.id,
            role=EstablishmentMembership.Role.DIRECTOR,
            status=EstablishmentMembership.Status.ACTIVE,
        )
        .first()
    )
    if membership is None or not is_valid_membership(membership):
        return None

    return EstablishmentAdminActor(
        user=user,
        establishment=establishment,
        membership=membership,
        via_organization_owner=False,
    )


def can_view_signal_feed(membership: EstablishmentMembership | None) -> bool:
    return is_valid_membership(membership)


def can_create_observation(membership: EstablishmentMembership | None) -> bool:
    return is_valid_membership(membership)


def can_create_action(membership: EstablishmentMembership | None) -> bool:
    if not is_valid_membership(membership):
        return False
    return membership.role in _ACTION_ROLES or membership.role == EstablishmentMembership.Role.STAFF


def can_validate_action(membership: EstablishmentMembership | None) -> bool:
    return _has_role(membership, _ACTION_ROLES)


def _has_role(
    membership: EstablishmentMembership | None,
    allowed_roles: frozenset[str],
) -> bool:
    return is_valid_membership(membership) and membership.role in allowed_roles


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


def is_valid_membership(membership: EstablishmentMembership | None) -> bool:
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


class CanViewTeamMemberships(BasePermission):
    message = "You do not have permission to view team memberships."

    def has_permission(self, request, view) -> bool:
        access_context = get_api_access_context(request)
        return can_view_team_memberships(access_context.active_membership)


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


class CanCreateEstablishment(BasePermission):
    message = "You do not have permission to create an establishment."

    def has_permission(self, request, view) -> bool:
        return can_create_establishment(getattr(request, "user", None))


class CanManageOrganization(BasePermission):
    message = "You do not have permission to manage this organization."

    def has_permission(self, request, view) -> bool:
        return can_manage_organization(getattr(request, "user", None))
