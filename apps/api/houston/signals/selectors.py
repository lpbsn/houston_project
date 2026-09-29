from __future__ import annotations

import uuid
from typing import Literal

from django.db.models import (
    BooleanField,
    Count,
    Exists,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
)

from houston.establishments.membership_scope import build_signal_feed_scope_q_v2
from houston.establishments.models import EstablishmentMembership
from houston.observations.models import ObservationMedia
from houston.signals.constants import (
    ACTIVE_SIGNAL_STATUSES,
    FEED_SIGNAL_STATUSES,
    OPERATIONAL_SIGNAL_FEED_STATUSES,
    PINNABLE_SIGNAL_STATUSES,
)
from houston.signals.feed_cursor import operational_status_rank_case
from houston.signals.feed_filters import (
    SignalFeedFilters,
    apply_signal_feed_context_filters,
    signal_feed_status_selection,
)
from houston.signals.models import Signal, SignalResolutionRequest, SignalSourceObservation
from houston.signals.permissions import can_view_signal_detail

ViewMode = Literal["personal", "general"]

_SIGNAL_LIST_SELECT_RELATED = (
    "establishment",
    "operational_unit",
    "affected_business_unit",
    "responsible_business_unit",
    "activity_subject",
    "activity_subject__catalog_activity_subject",
    "activity_subject__business_unit",
    "pinned_by_membership__user",
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
_SIGNAL_PENDING_RESOLUTION_REQUEST_PREFETCH = Prefetch(
    "resolution_requests",
    queryset=(
        SignalResolutionRequest.objects.filter(
            status=SignalResolutionRequest.Status.PENDING,
        ).select_related("requested_by_membership")
    ),
    to_attr="pending_resolution_requests",
)
_SIGNAL_LIST_PREFETCH = (
    _SIGNAL_CREATED_FROM_PREFETCH,
    _SIGNAL_PENDING_RESOLUTION_REQUEST_PREFETCH,
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

_TOTAL_UNCLASSIFIED_Q = Q(
    affected_business_unit__isnull=True,
    responsible_business_unit__isnull=True,
    activity_subject__isnull=True,
)


def _signal_blocking_execution_annotation() -> dict:
    from houston.action_plans.constants import SIGNAL_BLOCKING_EXECUTION_STATUSES
    from houston.action_plans.models import ActionPlanExecution

    return {
        "has_blocking_linked_execution": Exists(
            ActionPlanExecution.objects.filter(
                source_signal_id=OuterRef("pk"),
                status__in=SIGNAL_BLOCKING_EXECUTION_STATUSES,
            )
        ),
    }


def _signal_list_annotations() -> dict:
    return {
        **_SIGNAL_AGGREGATION_COUNT_ANNOTATION,
        **_signal_blocking_execution_annotation(),
    }


def annotate_has_eligible_resolution_reviewers(
    queryset: QuerySet[Signal],
    *,
    membership: EstablishmentMembership,
) -> QuerySet[Signal]:
    """Fold reviewer-eligibility into the list SELECT (O(1) queries, any distinct BUs)."""
    from houston.signals.permissions import resolve_review_route_for_membership

    review_route = resolve_review_route_for_membership(membership)
    if review_route is None:
        return queryset.annotate(
            has_eligible_resolution_reviewers=Value(False, output_field=BooleanField()),
        )

    if review_route == SignalResolutionRequest.ReviewRoute.STAFF_TO_MANAGER:
        return queryset.annotate(
            has_eligible_resolution_reviewers=Exists(
                EstablishmentMembership.objects.filter(
                    establishment_id=OuterRef("establishment_id"),
                    status=EstablishmentMembership.Status.ACTIVE,
                    role=EstablishmentMembership.Role.MANAGER,
                    scope_links__business_unit_id=OuterRef("responsible_business_unit_id"),
                )
            ),
        )

    if review_route == SignalResolutionRequest.ReviewRoute.MANAGER_TO_DIRECTOR:
        return queryset.annotate(
            has_eligible_resolution_reviewers=Exists(
                EstablishmentMembership.objects.filter(
                    establishment_id=OuterRef("establishment_id"),
                    status=EstablishmentMembership.Status.ACTIVE,
                    role=EstablishmentMembership.Role.DIRECTOR,
                )
            ),
        )

    return queryset.annotate(
        has_eligible_resolution_reviewers=Value(False, output_field=BooleanField()),
    )


def active_signals_for_establishment(*, establishment_id: uuid.UUID) -> QuerySet[Signal]:
    return (
        Signal.objects.filter(
            establishment_id=establishment_id,
            status__in=ACTIVE_SIGNAL_STATUSES,
        )
        .select_related(*_SIGNAL_LIST_SELECT_RELATED)
        .prefetch_related(*_SIGNAL_LIST_PREFETCH)
        .annotate(**_signal_blocking_execution_annotation())
    )


def feed_signals_for_establishment(*, establishment_id: uuid.UUID) -> QuerySet[Signal]:
    return (
        Signal.objects.filter(
            establishment_id=establishment_id,
            status__in=FEED_SIGNAL_STATUSES,
        )
        .annotate(**_signal_list_annotations())
        .select_related(*_SIGNAL_LIST_SELECT_RELATED)
        .prefetch_related(*_SIGNAL_LIST_PREFETCH)
    )


def apply_feed_sorting(queryset: QuerySet[Signal]) -> QuerySet[Signal]:
    return queryset.annotate(status_rank=operational_status_rank_case()).order_by(
        "status_rank",
        "-last_activity_at",
        "-created_at",
        "-id",
    )


def signal_read_visibility_q(
    *,
    membership: EstablishmentMembership,
    view_mode: ViewMode,
    statuses: frozenset[str],
) -> Q:
    """Role and scope visibility for a status set. No status selection inside the set."""
    visible = Q(
        establishment_id=membership.establishment_id,
        status__in=statuses,
    )
    if membership.role == EstablishmentMembership.Role.STAFF:
        visible &= ~_TOTAL_UNCLASSIFIED_Q

    if view_mode == "general":
        return visible

    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        return visible

    scope_q = build_signal_feed_scope_q_v2(membership=membership)
    if membership.role == EstablishmentMembership.Role.MANAGER:
        if scope_q is None:
            return visible & _TOTAL_UNCLASSIFIED_Q
        return visible & (scope_q | _TOTAL_UNCLASSIFIED_Q)

    if scope_q is None:
        return Q(pk__in=[])
    return visible & scope_q


def signal_feed_visibility_q(
    *,
    membership: EstablishmentMembership,
    view_mode: ViewMode,
) -> Q:
    """Rows this membership may see in the operational feed. No status selection."""
    return signal_read_visibility_q(
        membership=membership,
        view_mode=view_mode,
        statuses=OPERATIONAL_SIGNAL_FEED_STATUSES,
    )


def _operational_signal_feed_queryset(*, visibility: Q) -> QuerySet[Signal]:
    return (
        Signal.objects.filter(visibility)
        .annotate(**_signal_list_annotations())
        .select_related(*_SIGNAL_LIST_SELECT_RELATED)
        .prefetch_related(*_SIGNAL_LIST_PREFETCH)
    )


def signal_feed_queryset(
    *,
    membership: EstablishmentMembership,
    view_mode: ViewMode,
    filters: SignalFeedFilters | None = None,
) -> QuerySet[Signal]:
    queryset = _operational_signal_feed_queryset(
        visibility=signal_feed_visibility_q(membership=membership, view_mode=view_mode),
    )
    queryset = annotate_has_eligible_resolution_reviewers(
        queryset,
        membership=membership,
    )
    return apply_signal_feed_context_filters(queryset, filters=filters)


def signal_feed_list_queryset(
    queryset: QuerySet[Signal],
    *,
    filters: SignalFeedFilters | None,
) -> QuerySet[Signal]:
    """Unpinned operational list for the active status selection."""
    listed = queryset.exclude(is_pinned=True, status__in=PINNABLE_SIGNAL_STATUSES)
    selection = signal_feed_status_selection(filters)
    if selection != "all":
        listed = listed.filter(status=selection)
    return apply_feed_sorting(listed)


def signal_feed_pins_queryset(
    queryset: QuerySet[Signal],
    *,
    filters: SignalFeedFilters | None,
) -> QuerySet[Signal]:
    """Eligible pins for the active status selection. In progress has no pin zone."""
    selection = signal_feed_status_selection(filters)
    if selection == Signal.Status.IN_PROGRESS:
        return queryset.none()
    pinned = queryset.filter(
        is_pinned=True,
        status__in=PINNABLE_SIGNAL_STATUSES,
        pinned_at__isnull=False,
    )
    if selection != "all":
        pinned = pinned.filter(status=selection)
    return pinned.order_by("-pinned_at", "-id")


def signal_feed_counts(
    queryset: QuerySet[Signal],
    *,
    filters: SignalFeedFilters | None,
) -> dict[str, int]:
    """Status totals are unpinned only and ignore the selected status."""
    selection = signal_feed_status_selection(filters)
    pin_filter = Q(is_pinned=True, status__in=PINNABLE_SIGNAL_STATUSES)
    if selection not in {"all", Signal.Status.IN_PROGRESS}:
        pin_filter &= Q(status=selection)
    aggregated = queryset.aggregate(
        open=Count("id", filter=Q(status=Signal.Status.OPEN, is_pinned=False)),
        in_progress=Count("id", filter=Q(status=Signal.Status.IN_PROGRESS, is_pinned=False)),
        interesting=Count("id", filter=Q(status=Signal.Status.INTERESTING, is_pinned=False)),
        pinned=Count("id", filter=pin_filter),
    )
    counts = {key: aggregated[key] or 0 for key in ("open", "in_progress", "interesting", "pinned")}
    if selection == Signal.Status.IN_PROGRESS:
        counts["pinned"] = 0
    return counts


def get_signal_for_qualify_routing(
    *,
    membership: EstablishmentMembership,
    signal_id: uuid.UUID,
) -> Signal | None:
    """Load a signal for qualify."""
    return (
        Signal.objects.filter(
            establishment_id=membership.establishment_id,
            id=signal_id,
        )
        .select_related(
            "pinned_by_membership__user",
            *_SIGNAL_LIST_SELECT_RELATED,
        )
        .prefetch_related(*_SIGNAL_LIST_PREFETCH)
        .annotate(**_signal_list_annotations())
        .first()
    )


def get_signal_for_detail(
    *,
    membership: EstablishmentMembership,
    signal_id: uuid.UUID,
) -> Signal | None:
    signal = (
        annotate_has_eligible_resolution_reviewers(
            feed_signals_for_establishment(establishment_id=membership.establishment_id),
            membership=membership,
        )
        .filter(id=signal_id)
        .select_related(
            "pinned_by_membership__user",
            "marked_interesting_by_membership",
            "resolved_by_membership",
            "canceled_by_membership",
        )
        .first()
    )
    if signal is not None:
        if not can_view_signal_detail(membership, signal):
            return None
        return signal

    canceled_signal = annotate_has_eligible_resolution_reviewers(
        Signal.objects.filter(
            establishment_id=membership.establishment_id,
            id=signal_id,
            status=Signal.Status.CANCELED,
        )
        .annotate(**_signal_list_annotations())
        .select_related(
            "pinned_by_membership__user",
            "marked_interesting_by_membership",
            "resolved_by_membership",
            "canceled_by_membership",
            *_SIGNAL_LIST_SELECT_RELATED,
        )
        .prefetch_related(*_SIGNAL_LIST_PREFETCH),
        membership=membership,
    ).first()
    if canceled_signal is None:
        return None

    if not can_view_signal_detail(membership, canceled_signal):
        return None
    return canceled_signal


def cross_signal_feed_queryset(
    *,
    memberships: list[EstablishmentMembership],
    filters: SignalFeedFilters | None = None,
) -> QuerySet[Signal]:
    if not memberships:
        return Signal.objects.none()
    visibility = Q()
    for membership in memberships:
        visibility |= signal_feed_visibility_q(membership=membership, view_mode="general")
    queryset = Signal.objects.filter(visibility)
    return apply_signal_feed_context_filters(queryset, filters=filters)


def hydrate_cross_signal_feed_queryset(
    queryset: QuerySet[Signal],
    *,
    limit: int,
) -> QuerySet[Signal]:
    """Hydrate a bounded Cross collection under one statement snapshot.

    The ordered subquery revalidates visibility, filters, cursor and L/P membership
    when the statement executes. The outer query can therefore hydrate only those
    selected IDs under the same statement snapshot.
    """
    selected_ids = queryset.values("pk")[:limit]
    hydration_base = Signal.objects.all()
    if "status_rank" not in queryset.query.annotations:
        # Keeping the pin predicates on the outer query lets PostgreSQL retain the
        # selective pinned-row plan while revalidating P membership explicitly.
        hydration_base = queryset
    hydrated = (
        hydration_base.filter(pk__in=Subquery(selected_ids))
        .annotate(**_SIGNAL_AGGREGATION_COUNT_ANNOTATION)
        .select_related(*_SIGNAL_LIST_SELECT_RELATED)
        .prefetch_related(*_SIGNAL_LIST_PREFETCH)
    )
    if "status_rank" in queryset.query.annotations:
        return apply_feed_sorting(hydrated)
    return hydrated.order_by(*queryset.query.order_by)


def get_cross_signal_for_detail(
    *,
    memberships: list[EstablishmentMembership],
    signal_id: uuid.UUID,
) -> tuple[Signal | None, EstablishmentMembership | None]:
    by_establishment = {
        membership.establishment_id: membership for membership in memberships
    }
    signal = Signal.objects.filter(
        id=signal_id,
        establishment_id__in=by_establishment,
    ).only("id", "establishment_id").first()
    if signal is None:
        return None, None
    membership = by_establishment[signal.establishment_id]
    return get_signal_for_detail(membership=membership, signal_id=signal_id), membership


def get_pending_resolution_request(
    *,
    signal_id: uuid.UUID,
):
    from houston.signals.models import SignalResolutionRequest

    return (
        SignalResolutionRequest.objects.filter(
            signal_id=signal_id,
            status=SignalResolutionRequest.Status.PENDING,
        )
        .select_related(
            "requested_by_membership__user",
            "reviewed_by_membership__user",
        )
        .first()
    )


def list_resolution_requests_for_signal(
    *,
    signal_id: uuid.UUID,
):
    from houston.signals.models import SignalResolutionRequest

    return list(
        SignalResolutionRequest.objects.filter(signal_id=signal_id)
        .select_related(
            "requested_by_membership__user",
            "reviewed_by_membership__user",
        )
        .order_by("requested_at", "id")
    )


_EVENT_TYPE_SORT_ORDER = {
    "created": 0,
    "approved": 1,
    "rejected": 1,
    "canceled": 1,
}


def _membership_display_name(membership) -> str | None:
    from houston.accounts.display import membership_display_name

    return membership_display_name(membership)


def build_resolution_request_events(requests) -> list[dict]:
    """Project incremental history events from resolution request rows."""
    from houston.signals.models import SignalResolutionRequest

    events: list[dict] = []
    for request in requests:
        requester_name = _membership_display_name(request.requested_by_membership)
        events.append(
            {
                "request_id": request.id,
                "event_type": "created",
                "occurred_at": request.requested_at,
                "actor_display_name": requester_name,
            }
        )
        if request.status == SignalResolutionRequest.Status.APPROVED:
            events.append(
                {
                    "request_id": request.id,
                    "event_type": "approved",
                    "occurred_at": request.reviewed_at,
                    "actor_display_name": _membership_display_name(
                        request.reviewed_by_membership
                    ),
                }
            )
        elif request.status == SignalResolutionRequest.Status.REJECTED:
            events.append(
                {
                    "request_id": request.id,
                    "event_type": "rejected",
                    "occurred_at": request.reviewed_at,
                    "actor_display_name": _membership_display_name(
                        request.reviewed_by_membership
                    ),
                }
            )
        elif request.status == SignalResolutionRequest.Status.CANCELED:
            actor_name = None
            if (
                request.canceled_reason
                == SignalResolutionRequest.CanceledReason.CANCELED_BY_REQUESTER
            ):
                actor_name = requester_name
            events.append(
                {
                    "request_id": request.id,
                    "event_type": "canceled",
                    "occurred_at": request.canceled_at,
                    "actor_display_name": actor_name,
                }
            )

    events.sort(
        key=lambda event: (
            event["occurred_at"],
            str(event["request_id"]),
            _EVENT_TYPE_SORT_ORDER.get(event["event_type"], 0),
        ),
        reverse=True,
    )
    return events


def get_resolution_request_for_signal_command(
    *,
    membership: EstablishmentMembership,
    signal_id: uuid.UUID,
    request_id: uuid.UUID,
):
    from houston.signals.models import SignalResolutionRequest

    signal = get_signal_for_detail(membership=membership, signal_id=signal_id)
    if signal is None:
        return None, None
    resolution_request = (
        SignalResolutionRequest.objects.filter(
            id=request_id,
            signal_id=signal.id,
        )
        .select_related(
            "signal",
            "requested_by_membership__user",
            "reviewed_by_membership__user",
        )
        .first()
    )
    if resolution_request is None:
        return signal, None
    return signal, resolution_request
