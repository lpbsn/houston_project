from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from houston.accounts.models import User
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization

CURRENT_ESTABLISHMENT_SESSION_KEY = "current_establishment_id"

ACCESS_STATE_ANONYMOUS = "anonymous"
ACCESS_STATE_INACTIVE_USER = "inactive_user"
ACCESS_STATE_NO_MEMBERSHIPS = "no_memberships"
ACCESS_STATE_READY = "ready"
ACCESS_STATE_SELECTION_REQUIRED = "selection_required"


@dataclass(frozen=True)
class CurrentAccessContext:
    user: User | None
    is_authenticated: bool
    has_app_access: bool
    state: str
    active_memberships: tuple[EstablishmentMembership, ...]
    selected_membership: EstablishmentMembership | None
    selected_establishment: Establishment | None


def resolve_current_access_context(request: Any) -> CurrentAccessContext:
    user = request.user

    if not user.is_authenticated:
        return CurrentAccessContext(
            user=None,
            is_authenticated=False,
            has_app_access=False,
            state=ACCESS_STATE_ANONYMOUS,
            active_memberships=(),
            selected_membership=None,
            selected_establishment=None,
        )

    if user.status != User.Status.ACTIVE:
        _clear_current_establishment_id(request)
        return CurrentAccessContext(
            user=user,
            is_authenticated=True,
            has_app_access=False,
            state=ACCESS_STATE_INACTIVE_USER,
            active_memberships=(),
            selected_membership=None,
            selected_establishment=None,
        )

    active_memberships = tuple(
        EstablishmentMembership.objects.filter(
            user=user,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related("establishment", "establishment__organization")
        .order_by("establishment__name", "establishment_id")
    )

    if not active_memberships:
        _clear_current_establishment_id(request)
        return CurrentAccessContext(
            user=user,
            is_authenticated=True,
            has_app_access=False,
            state=ACCESS_STATE_NO_MEMBERSHIPS,
            active_memberships=(),
            selected_membership=None,
            selected_establishment=None,
        )

    if len(active_memberships) == 1:
        membership = active_memberships[0]
        _store_current_establishment_id(request, membership.establishment_id)
        return CurrentAccessContext(
            user=user,
            is_authenticated=True,
            has_app_access=True,
            state=ACCESS_STATE_READY,
            active_memberships=active_memberships,
            selected_membership=membership,
            selected_establishment=membership.establishment,
        )

    selected_membership = _resolve_membership_from_session(request, active_memberships)

    if selected_membership is not None:
        return CurrentAccessContext(
            user=user,
            is_authenticated=True,
            has_app_access=True,
            state=ACCESS_STATE_READY,
            active_memberships=active_memberships,
            selected_membership=selected_membership,
            selected_establishment=selected_membership.establishment,
        )

    _clear_current_establishment_id(request)
    return CurrentAccessContext(
        user=user,
        is_authenticated=True,
        has_app_access=False,
        state=ACCESS_STATE_SELECTION_REQUIRED,
        active_memberships=active_memberships,
        selected_membership=None,
        selected_establishment=None,
    )


def _resolve_membership_from_session(
    request: Any,
    active_memberships: tuple[EstablishmentMembership, ...],
) -> EstablishmentMembership | None:
    selected_id = request.session.get(CURRENT_ESTABLISHMENT_SESSION_KEY)

    if selected_id is None:
        return None

    memberships_by_establishment_id = {
        str(membership.establishment_id): membership for membership in active_memberships
    }
    membership = memberships_by_establishment_id.get(str(selected_id))

    if membership is None:
        _clear_current_establishment_id(request)
        return None

    _store_current_establishment_id(request, membership.establishment_id)
    return membership


def _store_current_establishment_id(request: Any, establishment_id: Any) -> None:
    request.session[CURRENT_ESTABLISHMENT_SESSION_KEY] = str(establishment_id)


def _clear_current_establishment_id(request: Any) -> None:
    request.session.pop(CURRENT_ESTABLISHMENT_SESSION_KEY, None)
