from __future__ import annotations

from django.db import transaction

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.selectors import org_establishments_draft_active
from houston.establishments.services import (
    _has_other_full_coverage_active_org_owner,
    _revoke_pending_invitations,
)
from houston.organizations.models import Organization


def organizations_requiring_closure(*, user: User) -> list[Organization]:
    organization_ids = list(
        EstablishmentMembership.objects.filter(
            user=user,
            role=EstablishmentMembership.Role.OWNER,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .values_list("establishment__organization_id", flat=True)
        .distinct()
    )
    required: list[Organization] = []
    for organization in Organization.objects.filter(id__in=organization_ids).order_by("id"):
        establishments = org_establishments_draft_active(organization_id=organization.id)
        if not _has_other_full_coverage_active_org_owner(
            exclude_user_id=user.id,
            establishments=establishments,
        ):
            required.append(organization)
    return required


def establishments_left_without_director(*, user: User) -> list[Establishment]:
    director_memberships = EstablishmentMembership.objects.filter(
        user=user,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.ACTIVE,
        establishment__status=Establishment.Status.ACTIVE,
        establishment__organization__status=Organization.Status.ACTIVE,
    ).select_related("establishment")
    left: list[Establishment] = []
    for membership in director_memberships:
        has_other = (
            EstablishmentMembership.objects.filter(
                establishment_id=membership.establishment_id,
                role=EstablishmentMembership.Role.DIRECTOR,
                status__in=[
                    EstablishmentMembership.Status.ACTIVE,
                    EstablishmentMembership.Status.INVITED,
                ],
            )
            .exclude(id=membership.id)
            .exists()
        )
        if not has_other:
            left.append(membership.establishment)
    return left


@transaction.atomic
def close_organization_for_account_deletion(*, organization: Organization) -> None:
    locked = Organization.objects.select_for_update().get(pk=organization.id)
    if locked.status == Organization.Status.ARCHIVED:
        return

    locked.status = Organization.Status.ARCHIVED
    locked.save(update_fields=["status", "updated_at"])

    establishments = list(
        Establishment.objects.select_for_update()
        .filter(
            organization_id=locked.id,
            status__in=[Establishment.Status.DRAFT, Establishment.Status.ACTIVE],
        )
        .order_by("id")
    )
    for establishment in establishments:
        establishment.status = Establishment.Status.DEACTIVATED
        establishment.save(update_fields=["status", "updated_at"])

    memberships = list(
        EstablishmentMembership.objects.select_for_update()
        .filter(establishment__organization_id=locked.id)
        .exclude(status=EstablishmentMembership.Status.DEACTIVATED)
        .order_by("id")
    )

    from houston.chat.services import handle_membership_chat_deactivation
    from houston.realtime.broadcast import schedule_access_event

    for membership in memberships:
        membership.status = EstablishmentMembership.Status.DEACTIVATED
        membership.save(update_fields=["status", "updated_at"])
        _revoke_pending_invitations(membership=membership)
        handle_membership_chat_deactivation(membership=membership)
        schedule_access_event(
            reason="membership.deactivated",
            establishment_id=membership.establishment_id,
            membership_id=membership.id,
        )
