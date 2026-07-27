from __future__ import annotations

import uuid
from typing import Literal

from django.db.models import Count, Prefetch, Q, QuerySet

from houston.establishments.membership_scope import build_signal_feed_scope_q_v2
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES
from houston.observations.models import ObservationMedia
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES, FEED_SIGNAL_STATUSES
from houston.signals.feed_cursor import feed_sort_case_expressions
from houston.signals.feed_filters import SignalFeedFilters, apply_feed_filters
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.permissions import can_view_signal_detail

ViewMode = Literal["personal", "general"]

_SIGNAL_LIST_SELECT_RELATED = (
    "operational_unit",
    "affected_business_unit",
    "responsible_business_unit",
    "activity_subject",
    "activity_subject__catalog_activity_subject",
)
_SIGNAL_CREATED_FROM_PREFETCH = Prefetch(
    "source_observation_links",
    queryset=(
        SignalSourceObservation.objects.filter(
            link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        )
        .select_related("observation__submitted_by_membership__user")
        .prefetch_related(
            Prefetch(
                "observation__media_items",
                queryset=ObservationMedia.objects.order_by("position"),
            ),
        )
        .order_by("observation__created_at", "observation__id")
    ),
    to_attr="created_from_source_links",
)
_SIGNAL_LIST_PREFETCH = (_SIGNAL_CREATED_FROM_PREFETCH,)
_SIGNAL_AGGREGATION_COUNT_ANNOTATION = {
    "aggregation_count": Count(
        "source_observation_links",
        filter=Q(
            source_observation_links__link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
        ),
        distinct=True,
    ),
}

_TOTAL_UNCLASSIFIED_Q = Q(
    affected_business_unit__isnull=True,
    responsible_business_unit__isnull=True,
    activity_subject__isnull=True,
)
_UNASSIGNED_ROUTING_Q = Q(routing_status=Signal.RoutingStatus.UNASSIGNED)


def active_signals_for_establishment(*, establishment_id: uuid.UUID) -> QuerySet[Signal]:
    return (
        Signal.objects.filter(
            establishment_id=establishment_id,
            status__in=ACTIVE_SIGNAL_STATUSES,
        )
        .select_related(*_SIGNAL_LIST_SELECT_RELATED)
        .prefetch_related(*_SIGNAL_LIST_PREFETCH)
    )


def feed_signals_for_establishment(*, establishment_id: uuid.UUID) -> QuerySet[Signal]:
    return (
        Signal.objects.filter(
            establishment_id=establishment_id,
            status__in=FEED_SIGNAL_STATUSES,
        )
        .annotate(**_SIGNAL_AGGREGATION_COUNT_ANNOTATION)
        .select_related(*_SIGNAL_LIST_SELECT_RELATED)
        .prefetch_related(*_SIGNAL_LIST_PREFETCH)
    )


def _apply_staff_total_unclassified_exclusion(
    queryset: QuerySet[Signal],
    *,
    membership: EstablishmentMembership,
) -> QuerySet[Signal]:
    if membership.role != EstablishmentMembership.Role.STAFF:
        return queryset
    return queryset.exclude(_TOTAL_UNCLASSIFIED_Q)


def _apply_canceled_feed_visibility_for_non_admin(
    queryset: QuerySet[Signal],
    *,
    membership: EstablishmentMembership,
) -> QuerySet[Signal]:
    if membership.role in ADMIN_ROLES:
        return queryset

    scope_q = build_signal_feed_scope_q_v2(membership=membership)
    # Managers may always see canceled unassigned (establishment triage).
    if membership.role == EstablishmentMembership.Role.MANAGER:
        canceled_visible = _UNASSIGNED_ROUTING_Q
        if scope_q is not None:
            canceled_visible = canceled_visible | scope_q
        return queryset.filter(~Q(status=Signal.Status.CANCELED) | canceled_visible)

    if scope_q is None:
        return queryset.exclude(status=Signal.Status.CANCELED)
    return queryset.filter(~Q(status=Signal.Status.CANCELED) | scope_q)


def apply_feed_sorting(queryset: QuerySet[Signal]) -> QuerySet[Signal]:
    status_group_rank, status_rank = feed_sort_case_expressions()
    return queryset.order_by(
        status_group_rank,
        "-is_pinned",
        status_rank,
        "-last_activity_at",
        "-created_at",
        "-id",
    )


def signal_feed_queryset(
    *,
    membership: EstablishmentMembership,
    view_mode: ViewMode,
    filters: SignalFeedFilters | None = None,
) -> QuerySet[Signal]:
    queryset = feed_signals_for_establishment(establishment_id=membership.establishment_id)
    queryset = _apply_staff_total_unclassified_exclusion(queryset, membership=membership)

    if view_mode == "general":
        queryset = _apply_canceled_feed_visibility_for_non_admin(
            queryset,
            membership=membership,
        )
        queryset = apply_feed_filters(queryset, filters=filters)
        return apply_feed_sorting(queryset)

    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        queryset = apply_feed_filters(queryset, filters=filters)
        return apply_feed_sorting(queryset)

    if membership.role == EstablishmentMembership.Role.MANAGER:
        # Personal = MembershipScope poles OR totally unclassified (three nulls).
        # Partial unassigned outside scope stays in general, not Ma zone.
        scope_q = build_signal_feed_scope_q_v2(membership=membership)
        if scope_q is None:
            queryset = queryset.filter(_TOTAL_UNCLASSIFIED_Q)
        else:
            queryset = queryset.filter(scope_q | _TOTAL_UNCLASSIFIED_Q)
        queryset = apply_feed_filters(queryset, filters=filters)
        return apply_feed_sorting(queryset)

    # Staff: Ma vue = BU scope only (total unclassified already excluded).
    scope_q = build_signal_feed_scope_q_v2(membership=membership)
    if scope_q is None:
        return apply_feed_sorting(queryset.none())
    queryset = queryset.filter(scope_q)
    queryset = apply_feed_filters(queryset, filters=filters)
    return apply_feed_sorting(queryset)


def get_signal_for_qualify_routing(
    *,
    membership: EstablishmentMembership,
    signal_id: uuid.UUID,
) -> Signal | None:
    """Load a signal for qualify, including archived already-merged sources."""
    return (
        Signal.objects.filter(
            establishment_id=membership.establishment_id,
            id=signal_id,
        )
        .select_related(
            "pinned_by_membership__user",
            "merged_into",
            *_SIGNAL_LIST_SELECT_RELATED,
            "merged_into__affected_business_unit",
            "merged_into__responsible_business_unit",
            "merged_into__activity_subject",
            "merged_into__operational_unit",
        )
        .prefetch_related(*_SIGNAL_LIST_PREFETCH)
        .annotate(**_SIGNAL_AGGREGATION_COUNT_ANNOTATION)
        .first()
    )


def get_signal_for_detail(
    *,
    membership: EstablishmentMembership,
    signal_id: uuid.UUID,
) -> Signal | None:
    signal = (
        feed_signals_for_establishment(establishment_id=membership.establishment_id)
        .filter(id=signal_id)
        .select_related("pinned_by_membership__user")
        .first()
    )
    if signal is not None:
        if not can_view_signal_detail(membership, signal):
            return None
        return signal

    canceled_signal = (
        Signal.objects.filter(
            establishment_id=membership.establishment_id,
            id=signal_id,
            status=Signal.Status.CANCELED,
        )
        .annotate(**_SIGNAL_AGGREGATION_COUNT_ANNOTATION)
        .select_related(
            "pinned_by_membership__user",
            *_SIGNAL_LIST_SELECT_RELATED,
        )
        .prefetch_related(*_SIGNAL_LIST_PREFETCH)
        .first()
    )
    if canceled_signal is None:
        return None

    if not can_view_signal_detail(membership, canceled_signal):
        return None
    return canceled_signal
