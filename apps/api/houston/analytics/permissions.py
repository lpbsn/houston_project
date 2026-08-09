from __future__ import annotations

from django.db.models import Q

from houston.accounts.models import User
from houston.establishments.membership_scope import membership_business_unit_scope_ids
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.permissions import (
    can_manage_organization,
    is_valid_membership,
    resolve_active_establishment_admin_actor,
)
from houston.establishments.role_constants import ADMIN_ROLES
from houston.organizations.models import Organization
from houston.signals.models import Signal

ANALYTICS_READ_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
    }
)


def empty_signal_scope_q() -> Q:
    return Q(pk__isnull=True)


def can_read_analytics(membership: EstablishmentMembership | None) -> bool:
    if not is_valid_membership(membership):
        return False
    return membership.role in ANALYTICS_READ_ROLES


def analytics_signal_scope_q_for_membership(
    membership: EstablishmentMembership | None,
) -> Q:
    if not can_read_analytics(membership):
        return empty_signal_scope_q()

    base_scope = Q(
        establishment_id=membership.establishment_id,
        establishment__status=Establishment.Status.ACTIVE,
        establishment__organization__status=Organization.Status.ACTIVE,
    )
    if membership.role in ADMIN_ROLES:
        return base_scope

    if membership.role == EstablishmentMembership.Role.MANAGER:
        scope_q = Q(routing_status=Signal.RoutingStatus.UNASSIGNED)
        business_unit_ids = membership_business_unit_scope_ids(membership)
        if business_unit_ids:
            scope_q |= Q(affected_business_unit_id__in=business_unit_ids)
            scope_q |= Q(responsible_business_unit_id__in=business_unit_ids)
        return base_scope & scope_q

    return empty_signal_scope_q()


def analytics_accessible_establishment_ids_for_user(
    user: User | None,
    *,
    organization_id=None,
) -> list:
    if user is None or user.status != User.Status.ACTIVE:
        return []

    queryset = EstablishmentMembership.objects.filter(
        user_id=user.id,
        role__in=ANALYTICS_READ_ROLES,
        status=EstablishmentMembership.Status.ACTIVE,
        establishment__status=Establishment.Status.ACTIVE,
        establishment__organization__status=Organization.Status.ACTIVE,
    )
    if organization_id is not None:
        queryset = queryset.filter(establishment__organization_id=organization_id)

    return list(
        queryset.values_list("establishment_id", flat=True)
        .distinct()
        .order_by("establishment_id")
    )


def can_govern_operational_patterns(
    membership: EstablishmentMembership | None,
    *,
    organization: Organization,
) -> bool:
    return can_correct_operational_patterns(membership, organization=organization)


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
