from __future__ import annotations

from django.db.models import Prefetch

from houston.accounts.models import User, UserSession
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipDomain,
)
from houston.organizations.models import Organization


def list_active_memberships(user: User) -> list[EstablishmentMembership]:
    return list(_active_membership_queryset(user))


def list_bootstrap_memberships(user: User) -> list[dict]:
    memberships = list_active_memberships(user)
    return [_serialize_membership(membership) for membership in memberships]


def build_bootstrap_payload(
    user: User,
    *,
    session: UserSession,
    autoselect_single_membership: bool = False,
) -> dict:
    memberships, active_membership = resolve_active_membership(
        user=user,
        session=session,
        autoselect_single_membership=autoselect_single_membership,
    )

    return {
        "authenticated": True,
        "user": _serialize_user(user),
        "memberships": [_serialize_membership(membership) for membership in memberships],
        "active_membership": (
            None if active_membership is None else _serialize_membership(active_membership)
        ),
    }


def resolve_active_membership(
    *,
    user: User,
    session: UserSession,
    autoselect_single_membership: bool = False,
) -> tuple[list[EstablishmentMembership], EstablishmentMembership | None]:
    memberships = list_active_memberships(user)
    memberships_by_establishment_id = {
        membership.establishment_id: membership for membership in memberships
    }

    selected_membership = None
    selected_establishment_id = session.selected_establishment_id

    if selected_establishment_id is not None:
        selected_membership = memberships_by_establishment_id.get(selected_establishment_id)

        if selected_membership is None:
            _update_selected_establishment(session=session, establishment=None)

    if (
        selected_membership is None
        and session.selected_establishment_id is None
        and autoselect_single_membership
        and len(memberships) == 1
    ):
        selected_membership = memberships[0]
        _update_selected_establishment(
            session=session,
            establishment=selected_membership.establishment,
        )

    return memberships, selected_membership


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


def _update_selected_establishment(
    *,
    session: UserSession,
    establishment: Establishment | None,
) -> None:
    next_establishment_id = None if establishment is None else establishment.id

    if session.selected_establishment_id == next_establishment_id:
        return

    session.selected_establishment = establishment
    session.save(update_fields=["selected_establishment", "updated_at"])
