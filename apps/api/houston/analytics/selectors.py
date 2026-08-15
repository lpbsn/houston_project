from __future__ import annotations

from dataclasses import dataclass

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
from houston.establishments.role_constants import ADMIN_ROLES
from houston.organizations.models import Organization
from houston.signals.models import Signal


@dataclass(frozen=True)
class AnalyticsReadScope:
    signal_scope_q: Q

    def readable_signals_queryset(self) -> QuerySet[Signal]:
        return Signal.objects.filter(self.signal_scope_q).distinct()

    def default_signals_queryset(self) -> QuerySet[Signal]:
        return self._signals_for_status_q(default_analytics_signal_q())

    def actionable_signals_queryset(self) -> QuerySet[Signal]:
        return self._signals_for_status_q(actionable_signal_q())

    def recurrence_signals_queryset(self) -> QuerySet[Signal]:
        return self._signals_for_status_q(recurrence_signal_q())

    def resolution_time_signals_queryset(self) -> QuerySet[Signal]:
        return self._signals_for_status_q(resolution_time_signal_q())

    def _signals_for_status_q(self, status_q: Q) -> QuerySet[Signal]:
        return Signal.objects.filter(self.signal_scope_q & status_q).distinct()


def resolve_analytics_read_scope(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> AnalyticsReadScope:
    return AnalyticsReadScope(
        signal_scope_q=_analytics_signal_scope_q_for_user(
            user,
            organization_id=organization_id,
            establishment_id=establishment_id,
            establishment_ids=establishment_ids,
        )
    )


def analytics_readable_signals_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> QuerySet[Signal]:
    scope = resolve_analytics_read_scope(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )
    return scope.readable_signals_queryset()


def analytics_default_signals_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> QuerySet[Signal]:
    scope = resolve_analytics_read_scope(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )
    return scope.default_signals_queryset()


def analytics_actionable_signals_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> QuerySet[Signal]:
    scope = resolve_analytics_read_scope(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )
    return scope.actionable_signals_queryset()


def analytics_recurrence_signals_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
    establishment_ids=None,
) -> QuerySet[Signal]:
    scope = resolve_analytics_read_scope(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
        establishment_ids=establishment_ids,
    )
    return scope.recurrence_signals_queryset()


def analytics_resolution_time_signals_queryset(
    user: User | None,
    *,
    organization_id=None,
    establishment_id=None,
) -> QuerySet[Signal]:
    scope = resolve_analytics_read_scope(
        user,
        organization_id=organization_id,
        establishment_id=establishment_id,
    )
    return scope.resolution_time_signals_queryset()


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

    admin_establishment_ids = []
    membership_scopes = []
    for membership in memberships:
        if membership.role in ADMIN_ROLES:
            admin_establishment_ids.append(membership.establishment_id)
        else:
            membership_scopes.append(analytics_signal_scope_q_for_membership(membership))
    if admin_establishment_ids:
        membership_scopes.append(
            Q(
                establishment_id__in=admin_establishment_ids,
                establishment__status=Establishment.Status.ACTIVE,
                establishment__organization__status=Organization.Status.ACTIVE,
            )
        )
    if not membership_scopes:
        return empty_signal_scope_q()
    scope_q = membership_scopes[0]
    for membership_scope in membership_scopes[1:]:
        scope_q |= membership_scope
    return scope_q
