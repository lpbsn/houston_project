from __future__ import annotations

from django.db.models import Q, QuerySet

from houston.accounts.models import User
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.analytics.permissions import (
    ANALYTICS_READ_ROLES,
    analytics_signal_scope_q_for_membership,
    empty_signal_scope_q,
)
from houston.establishments.membership_scope import membership_scope_prefetch
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization
from houston.signals.models import Signal


def analytics_readable_signals_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
) -> QuerySet[Signal]:
    scope_q = _analytics_signal_scope_q_for_user(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
    )
    return Signal.objects.filter(scope_q).distinct()


def analytics_readable_assignments_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
) -> QuerySet[SignalPatternAssignment]:
    readable_signals = analytics_readable_signals_queryset(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
    )
    return (
        SignalPatternAssignment.objects.filter(signal_id__in=readable_signals.values("id"))
        .select_related("signal", "pattern")
        .distinct()
    )


def analytics_readable_patterns_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
) -> QuerySet[OperationalPattern]:
    readable_assignments = analytics_readable_assignments_queryset(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
    )
    return (
        OperationalPattern.objects.filter(
            signal_assignments__id__in=readable_assignments.values("id")
        )
        .select_related("organization")
        .distinct()
    )


def _analytics_signal_scope_q_for_user(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
) -> Q:
    if user is None or user.status != User.Status.ACTIVE:
        return empty_signal_scope_q()

    memberships = (
        EstablishmentMembership.objects.filter(
            user_id=user.id,
            role__in=ANALYTICS_READ_ROLES,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related("user", "establishment", "establishment__organization")
        .prefetch_related(membership_scope_prefetch())
        .order_by("establishment_id", "id")
    )
    if organization_id is not None:
        memberships = memberships.filter(establishment__organization_id=organization_id)
    if establishment_id is not None:
        memberships = memberships.filter(establishment_id=establishment_id)

    scope_q = empty_signal_scope_q()
    for membership in memberships:
        scope_q |= analytics_signal_scope_q_for_membership(membership)
    return scope_q
