from __future__ import annotations

from houston.accounts.models import User
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import (
    can_manage_organization,
    resolve_active_establishment_admin_actor,
)
from houston.organizations.models import Organization
from houston.signals.models import Signal


def can_correct_operational_patterns(
    membership: EstablishmentMembership | None,
    *,
    organization: Organization,
) -> bool:
    if membership is None:
        return False
    if membership.role != EstablishmentMembership.Role.OWNER:
        return False
    if membership.status != EstablishmentMembership.Status.ACTIVE:
        return False
    if membership.user.status != User.Status.ACTIVE:
        return False
    if membership.establishment.organization_id != organization.id:
        return False
    return can_manage_organization(membership.user, organization_id=organization.id)


def can_correct_signal_pattern_assignment(
    membership: EstablishmentMembership,
    *,
    signal: Signal,
) -> bool:
    actor = resolve_active_establishment_admin_actor(membership.user, signal.establishment_id)
    if actor is None:
        return False
    return actor.membership.role == EstablishmentMembership.Role.OWNER
