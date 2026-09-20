from __future__ import annotations

import uuid

from django.db.models import Q, QuerySet

from houston.accounts.display import user_display_name
from houston.accounts.models import User
from houston.establishments.membership_scope import membership_scope_rows_for_membership
from houston.establishments.models import Establishment, EstablishmentMembership, OnboardingSession
from houston.establishments.services import compute_activation_readiness
from houston.organizations.models import Organization
from houston.platform.cursor import apply_created_at_desc_cursor, encode_created_at_cursor
from houston.platform.delete_services import (
    establishment_delete_blocking_reasons,
    organization_delete_blocking_reasons,
)
from houston.platform.onboarding_status import derive_onboarding_functional_status


def _uuid_or_none(value: str | None):
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def serialize_onboarding_summary(*, establishment: Establishment) -> dict:
    session = (
        OnboardingSession.objects.filter(establishment_id=establishment.id)
        .order_by("-created_at", "-id")
        .first()
    )
    readiness = None
    if session is not None and session.status != OnboardingSession.Status.ACTIVATED:
        readiness = compute_activation_readiness(session=session)
    return {
        "functional_status": derive_onboarding_functional_status(
            establishment=establishment,
            session=session,
            readiness=readiness,
        ),
        "session_id": None if session is None else session.id,
        "current_step": "" if session is None else session.current_step,
        "source_mode": "" if session is None else session.source_mode,
        "last_error_code": "" if session is None else session.last_error_code,
    }


def serialize_organization_list_item(organization: Organization) -> dict:
    return {
        "id": organization.id,
        "name": organization.name,
        "status": organization.status,
        "created_at": organization.created_at,
        "has_been_operational": organization.has_been_operational,
    }


def serialize_organization_detail(organization: Organization) -> dict:
    reasons = organization_delete_blocking_reasons(organization)
    establishments = list(organization.establishments.order_by("name", "id"))
    return {
        **serialize_organization_list_item(organization),
        "updated_at": organization.updated_at,
        "can_delete": not reasons,
        "blocking_reasons": reasons,
        "establishments": [
            {
                "id": item.id,
                "name": item.name,
                "status": item.status,
            }
            for item in establishments
        ],
    }


def serialize_establishment_list_item(establishment: Establishment) -> dict:
    return {
        "id": establishment.id,
        "name": establishment.name,
        "status": establishment.status,
        "organization_id": establishment.organization_id,
        "organization_name": establishment.organization.name,
        "created_at": establishment.created_at,
        "onboarding": serialize_onboarding_summary(establishment=establishment),
    }


def serialize_establishment_detail(establishment: Establishment) -> dict:
    reasons = establishment_delete_blocking_reasons(establishment)
    return {
        **serialize_establishment_list_item(establishment),
        "timezone": establishment.timezone,
        "updated_at": establishment.updated_at,
        "can_delete": not reasons,
        "blocking_reasons": reasons,
    }


def serialize_user_list_item(user: User) -> dict:
    return {
        "id": user.id,
        "display_name": user_display_name(user),
        "email": user.email,
        "status": user.status,
        "created_at": user.created_at,
    }


def serialize_user_detail(user: User) -> dict:
    return {
        **serialize_user_list_item(user),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "updated_at": user.updated_at,
    }


def serialize_membership(membership: EstablishmentMembership) -> dict:
    scopes, _summary = membership_scope_rows_for_membership(membership)
    establishment = membership.establishment
    return {
        "id": membership.id,
        "user_id": membership.user_id,
        "user_display_name": user_display_name(membership.user),
        "user_email": membership.user.email,
        "establishment_id": membership.establishment_id,
        "establishment_name": establishment.name,
        "organization_id": establishment.organization_id,
        "organization_name": establishment.organization.name,
        "role": membership.role,
        "status": membership.status,
        "scopes": scopes,
    }


def serialize_onboarding_list_item(session: OnboardingSession) -> dict:
    establishment = session.establishment
    readiness = None
    if session.status != OnboardingSession.Status.ACTIVATED:
        readiness = compute_activation_readiness(session=session)
    return {
        "id": session.id,
        "establishment_id": session.establishment_id,
        "establishment_name": establishment.name,
        "organization_id": session.organization_id,
        "organization_name": session.organization.name,
        "functional_status": derive_onboarding_functional_status(
            establishment=establishment,
            session=session,
            readiness=readiness,
        ),
        "session_status": session.status,
        "current_step": session.current_step,
        "created_at": session.created_at,
    }


def paginate_created_at_desc(queryset: QuerySet, *, cursor: str | None, limit: int) -> dict:
    page = list(apply_created_at_desc_cursor(queryset, cursor=cursor)[: limit + 1])
    has_more = len(page) > limit
    items = page[:limit]
    next_cursor = None
    if has_more and items:
        last = items[-1]
        next_cursor = encode_created_at_cursor(created_at=last.created_at, object_id=last.id)
    return {"items": items, "next_cursor": next_cursor}


def organization_queryset(*, search: str = "", status: str = "") -> QuerySet:
    qs = Organization.objects.all().order_by("-created_at", "-id")
    if status:
        qs = qs.filter(status=status)
    if search:
        ident = _uuid_or_none(search)
        if ident is not None:
            qs = qs.filter(id=ident)
        else:
            qs = qs.filter(name__icontains=search)
    return qs


def establishment_queryset(
    *,
    search: str = "",
    status: str = "",
    organization_id: str = "",
) -> QuerySet:
    qs = Establishment.objects.select_related("organization").order_by("-created_at", "-id")
    if status:
        qs = qs.filter(status=status)
    org_id = _uuid_or_none(organization_id)
    if org_id is not None:
        qs = qs.filter(organization_id=org_id)
    if search:
        ident = _uuid_or_none(search)
        if ident is not None:
            qs = qs.filter(id=ident)
        else:
            qs = qs.filter(Q(name__icontains=search) | Q(organization__name__icontains=search))
    return qs


def user_queryset(*, search: str = "", status: str = "") -> QuerySet:
    qs = User.objects.all().order_by("-created_at", "-id")
    if status:
        qs = qs.filter(status=status)
    if search:
        ident = _uuid_or_none(search)
        if ident is not None:
            qs = qs.filter(id=ident)
        else:
            qs = qs.filter(
                Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(username__icontains=search)
            )
    return qs


def onboarding_queryset(*, search: str = "") -> QuerySet:
    qs = OnboardingSession.objects.select_related(
        "establishment",
        "organization",
    ).order_by("-created_at", "-id")
    if search:
        ident = _uuid_or_none(search)
        if ident is not None:
            qs = qs.filter(Q(id=ident) | Q(establishment_id=ident) | Q(organization_id=ident))
        else:
            qs = qs.filter(
                Q(establishment__name__icontains=search) | Q(organization__name__icontains=search)
            )
    return qs


def membership_queryset(
    *,
    user_id: str = "",
    establishment_id: str = "",
    organization_id: str = "",
    role: str = "",
    status: str = "",
) -> QuerySet:
    qs = EstablishmentMembership.objects.select_related(
        "user",
        "establishment",
        "establishment__organization",
    ).order_by("-created_at", "-id")
    user_uuid = _uuid_or_none(user_id)
    if user_uuid is not None:
        qs = qs.filter(user_id=user_uuid)
    est_uuid = _uuid_or_none(establishment_id)
    if est_uuid is not None:
        qs = qs.filter(establishment_id=est_uuid)
    org_uuid = _uuid_or_none(organization_id)
    if org_uuid is not None:
        qs = qs.filter(establishment__organization_id=org_uuid)
    if role:
        qs = qs.filter(role=role)
    if status:
        qs = qs.filter(status=status)
    return qs
