from __future__ import annotations

from django.db.models import Prefetch, Q

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipDomain,
)
from houston.organizations.models import Organization


def list_memberships_for_management(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
) -> list[EstablishmentMembership] | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    return list(_management_membership_queryset(establishment_id=establishment_id))


def get_membership_for_management(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    membership_id,
) -> EstablishmentMembership | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    return (
        _management_membership_queryset(establishment_id=establishment_id)
        .filter(id=membership_id)
        .first()
    )


def search_users_for_establishment(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    query: str,
) -> list[EstablishmentMembership] | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    normalized_query = query.strip()
    if not normalized_query:
        return []

    return list(
        _management_membership_queryset(establishment_id=establishment_id)
        .filter(
            user__status=User.Status.ACTIVE,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .filter(
            Q(user__first_name__icontains=normalized_query)
            | Q(user__last_name__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(user__email__icontains=normalized_query)
        )
    )


def _management_membership_queryset(*, establishment_id):
    domain_prefetch = Prefetch(
        "domain_links",
        queryset=MembershipDomain.objects.filter(
            operational_domain__active=True,
        )
        .select_related("operational_domain")
        .order_by("operational_domain__key"),
    )

    return (
        EstablishmentMembership.objects.filter(establishment_id=establishment_id)
        .select_related("user", "establishment", "establishment__organization")
        .prefetch_related(domain_prefetch)
        .order_by("user__username", "user__email", "id")
    )
