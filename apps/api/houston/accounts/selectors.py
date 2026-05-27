from __future__ import annotations

from django.db.models import Prefetch

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipDomain,
)
from houston.organizations.models import Organization


def list_bootstrap_memberships(user: User) -> list[dict]:
    memberships = _active_membership_queryset(user)
    return [_serialize_membership(membership) for membership in memberships]


def build_bootstrap_payload(user: User) -> dict:
    memberships = list_bootstrap_memberships(user)
    active_membership = memberships[0] if len(memberships) == 1 else None

    return {
        "authenticated": True,
        "user": _serialize_user(user),
        "memberships": memberships,
        "active_membership": active_membership,
    }


def _active_membership_queryset(user: User):
    domain_prefetch = Prefetch(
        "domain_links",
        queryset=MembershipDomain.objects.filter(
            operational_domain__active=True,
        )
        .select_related("operational_domain")
        .order_by("operational_domain__key"),
    )

    return (
        EstablishmentMembership.objects.filter(
            user=user,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related("establishment", "establishment__organization")
        .prefetch_related(domain_prefetch)
        .order_by("establishment__name", "establishment_id")
    )


def _serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "identity_type": user.identity_type,
    }


def _serialize_membership(membership: EstablishmentMembership) -> dict:
    return {
        "id": str(membership.id),
        "establishment_id": str(membership.establishment_id),
        "establishment_name": membership.establishment.name,
        "organization_id": str(membership.establishment.organization_id),
        "organization_name": membership.establishment.organization.name,
        "role": membership.role,
        "status": membership.status,
        "operational_domains": [
            link.operational_domain.key for link in membership.domain_links.all()
        ],
    }
