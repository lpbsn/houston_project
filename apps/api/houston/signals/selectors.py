from __future__ import annotations

import uuid
from typing import Literal

from django.db.models import Count, Prefetch, Q, QuerySet

from houston.establishments.membership_scope import build_signal_feed_scope_q_v2
from houston.establishments.models import EstablishmentMembership
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
)
_SIGNAL_REPORTER_PREFETCH = Prefetch(
    "source_observation_links",
    queryset=SignalSourceObservation.objects.select_related(
        "observation__submitted_by_membership__user",
    ).order_by("observation__created_at", "observation__id"),
    to_attr="source_links_by_observation_chronology",
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
_SIGNAL_LIST_PREFETCH = (
    _SIGNAL_CREATED_FROM_PREFETCH,
    _SIGNAL_REPORTER_PREFETCH,
)
_SIGNAL_AGGREGATION_COUNT_ANNOTATION = {
    "aggregation_count": Count(
        "source_observation_links",
        filter=Q(
            source_observation_links__link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
        ),
        distinct=True,
    ),
}


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


def apply_feed_sorting(queryset: QuerySet[Signal]) -> QuerySet[Signal]:
    status_group_rank, urgency_order, status_rank = feed_sort_case_expressions()
    return queryset.order_by(
        status_group_rank,
        "-is_pinned",
        urgency_order,
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

    if view_mode == "general":
        queryset = apply_feed_filters(queryset, filters=filters)
        return apply_feed_sorting(queryset)

    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        queryset = apply_feed_filters(queryset, filters=filters)
        return apply_feed_sorting(queryset)

    scope_q = build_signal_feed_scope_q_v2(membership=membership)
    if scope_q is None:
        return apply_feed_sorting(queryset.none())
    queryset = queryset.filter(scope_q)
    queryset = apply_feed_filters(queryset, filters=filters)
    return apply_feed_sorting(queryset)


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
        .select_related(
            "pinned_by_membership__user",
            "affected_business_unit",
            "responsible_business_unit",
        )
        .first()
    )
    if canceled_signal is None:
        return None

    if not can_view_signal_detail(membership, canceled_signal):
        return None
    return canceled_signal
