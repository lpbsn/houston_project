from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from houston.accounts.authentication import AccessTokenAuthContext
from houston.accounts.models import User
from houston.accounts.selectors import resolve_active_membership
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
)

API_ACCESS_CONTEXT_REQUEST_ATTR = "_houston_api_access_context"

ACCESS_STATE_ANONYMOUS = "anonymous"
ACCESS_STATE_INACTIVE_USER = "inactive_user"
ACCESS_STATE_NO_MEMBERSHIPS = "no_memberships"
ACCESS_STATE_READY = "ready"
ACCESS_STATE_SELECTION_REQUIRED = "selection_required"


@dataclass(frozen=True)
class ApiAccessContext:
    user: User | None
    is_authenticated: bool
    state: str
    auth_session_id: str | None
    active_memberships: tuple[EstablishmentMembership, ...]
    active_membership: EstablishmentMembership | None
    selected_establishment: Establishment | None

    def membership_for_establishment(
        self,
        establishment_id: UUID | None,
    ) -> EstablishmentMembership | None:
        if establishment_id is None:
            return None
        for membership in self.active_memberships:
            if membership.establishment_id == establishment_id:
                return membership
        return None


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
