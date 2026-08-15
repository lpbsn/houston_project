from __future__ import annotations

from django.db.models import Q, QuerySet

from houston.accounts.models import User
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.analytics.permissions import (
    ANALYTICS_READ_ROLES,
    analytics_signal_scope_q_for_membership,
    empty_signal_scope_q,
)
from houston.analytics.status_matrix import (
    actionable_signal_q,
    default_analytics_signal_q,
    recurrence_signal_q,
    resolution_time_signal_q,
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
    establishment_ids=None,
) -> QuerySet[Signal]:
    scope_q = _analytics_signal_scope_q_for_user(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )
    return Signal.objects.filter(scope_q).distinct()


def analytics_default_signals_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> QuerySet[Signal]:
    return _analytics_readable_signals_for_status_q(
        user,
        default_analytics_signal_q(),
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )


def analytics_actionable_signals_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> QuerySet[Signal]:
    return _analytics_readable_signals_for_status_q(
        user,
        actionable_signal_q(),
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )


def analytics_recurrence_signals_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> QuerySet[Signal]:
    return _analytics_readable_signals_for_status_q(
        user,
        recurrence_signal_q(),
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )


def analytics_resolution_time_signals_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
) -> QuerySet[Signal]:
    return _analytics_readable_signals_for_status_q(
        user,
        resolution_time_signal_q(),
        organization_id=organization_id,
        establishment_id=establishment_id,
    )


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
    establishment_ids=None,
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
    if establishment_ids is not None:
        memberships = memberships.filter(establishment_id__in=establishment_ids)

    scope_q = empty_signal_scope_q()
    for membership in memberships:
        scope_q |= analytics_signal_scope_q_for_membership(membership)
    return scope_q


def _analytics_readable_signals_for_status_q(
    user: User | None,
    status_q: Q,
    *,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> QuerySet[Signal]:
    scope_q = _analytics_signal_scope_q_for_user(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )
    return Signal.objects.filter(scope_q & status_q).distinct()
