from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from houston.accounts.authentication import AccessTokenAuthContext
from houston.accounts.models import User
from houston.accounts.selectors import resolve_active_membership
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization

CURRENT_ESTABLISHMENT_SESSION_KEY = "current_establishment_id"
API_ACCESS_CONTEXT_REQUEST_ATTR = "_houston_api_access_context"

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


@dataclass(frozen=True)
class ApiAccessContext:
    user: User | None
    is_authenticated: bool
    state: str
    auth_session_id: str | None
    active_memberships: tuple[EstablishmentMembership, ...]
    active_membership: EstablishmentMembership | None
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


def get_api_access_context(request: Any) -> ApiAccessContext:
    cached_context = getattr(request, API_ACCESS_CONTEXT_REQUEST_ATTR, None)

    if cached_context is not None:
        return cached_context

    context = resolve_api_access_context(request)
    setattr(request, API_ACCESS_CONTEXT_REQUEST_ATTR, context)
    return context


def resolve_api_access_context(request: Any) -> ApiAccessContext:
    user = getattr(request, "user", None)
    auth_context = getattr(request, "auth", None)

    if not isinstance(auth_context, AccessTokenAuthContext):
        return ApiAccessContext(
            user=None,
            is_authenticated=False,
            state=ACCESS_STATE_ANONYMOUS,
            auth_session_id=None,
            active_memberships=(),
            active_membership=None,
            selected_establishment=None,
        )

    if user is None or not user.is_authenticated:
        return ApiAccessContext(
            user=None,
            is_authenticated=False,
            state=ACCESS_STATE_ANONYMOUS,
            auth_session_id=str(auth_context.session.id),
            active_memberships=(),
            active_membership=None,
            selected_establishment=None,
        )

    if user.status != User.Status.ACTIVE:
        return ApiAccessContext(
            user=user,
            is_authenticated=True,
            state=ACCESS_STATE_INACTIVE_USER,
            auth_session_id=str(auth_context.session.id),
            active_memberships=(),
            active_membership=None,
            selected_establishment=None,
        )

    memberships, active_membership = resolve_active_membership(
        user=user,
        session=auth_context.session,
    )
    active_memberships = tuple(memberships)

    if not active_memberships:
        return ApiAccessContext(
            user=user,
            is_authenticated=True,
            state=ACCESS_STATE_NO_MEMBERSHIPS,
            auth_session_id=str(auth_context.session.id),
            active_memberships=(),
            active_membership=None,
            selected_establishment=None,
        )

    if active_membership is None:
        return ApiAccessContext(
            user=user,
            is_authenticated=True,
            state=ACCESS_STATE_SELECTION_REQUIRED,
            auth_session_id=str(auth_context.session.id),
            active_memberships=active_memberships,
            active_membership=None,
            selected_establishment=None,
        )

    return ApiAccessContext(
        user=user,
        is_authenticated=True,
        state=ACCESS_STATE_READY,
        auth_session_id=str(auth_context.session.id),
        active_memberships=active_memberships,
        active_membership=active_membership,
        selected_establishment=active_membership.establishment,
    )
