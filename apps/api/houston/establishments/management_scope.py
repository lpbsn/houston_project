"""Shared management-visible establishment scope (Analytics, Cross feeds)."""

from __future__ import annotations

from uuid import UUID

from django.db.models import QuerySet

from houston.accounts.models import User
from houston.establishments.membership_scope import membership_scope_prefetch
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.role_constants import _MANAGEMENT_ROLES
from houston.organizations.models import Organization

MANAGEMENT_ROLES = _MANAGEMENT_ROLES


def _management_memberships_for_user(
    user: User | None,
) -> QuerySet[EstablishmentMembership]:
    if user is None or user.status != User.Status.ACTIVE:
        return EstablishmentMembership.objects.none()
    return EstablishmentMembership.objects.filter(
            user_id=user.id,
            role__in=MANAGEMENT_ROLES,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )


def list_management_memberships_for_user(user: User | None) -> list[EstablishmentMembership]:
    return list(
        _management_memberships_for_user(user)
        .select_related("user", "establishment", "establishment__organization")
        .prefetch_related(membership_scope_prefetch())
        .order_by("establishment__name", "establishment_id", "id")
    )


def management_establishment_ids_for_user(user: User | None) -> list[UUID]:
    return [
        membership.establishment_id
        for membership in list_management_memberships_for_user(user)
    ]


def user_can_access_management_scope(user: User | None) -> bool:
    return _management_memberships_for_user(user).exists()


def resolve_management_memberships_for_scope(
    user: User | None,
    *,
    establishment_id: UUID | None = None,
) -> list[EstablishmentMembership]:
    memberships = list_management_memberships_for_user(user)
    if establishment_id is None:
        return memberships
    return [
        membership
        for membership in memberships
        if membership.establishment_id == establishment_id
    ]
