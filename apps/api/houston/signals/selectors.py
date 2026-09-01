from __future__ import annotations

import uuid
from typing import Literal

from django.db.models import BooleanField, Count, Exists, OuterRef, Prefetch, Q, QuerySet, Value

from houston.establishments.membership_scope import build_signal_feed_scope_q_v2
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES
from houston.observations.models import ObservationMedia
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES, FEED_SIGNAL_STATUSES
from houston.signals.feed_cursor import feed_sort_case_expressions
from houston.signals.feed_filters import SignalFeedFilters, apply_feed_filters
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
_UNASSIGNED_ROUTING_Q = Q(routing_status=Signal.RoutingStatus.UNASSIGNED)


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
    queryset = annotate_has_eligible_resolution_reviewers(
        queryset,
        membership=membership,
    )
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
            "archived_by_membership",
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
            "archived_by_membership",
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
    signal_ids: list[uuid.UUID] = []
    for membership in memberships:
        signal_ids.extend(
            signal_feed_queryset(
                membership=membership,
                view_mode="general",
                filters=filters,
            ).values_list("id", flat=True)
        )
    if not signal_ids:
        return Signal.objects.none()
    return apply_feed_sorting(
        Signal.objects.filter(id__in=signal_ids)
        .annotate(**_signal_list_annotations())
        .annotate(
            has_eligible_resolution_reviewers=Value(False, output_field=BooleanField()),
        )
        .select_related(*_SIGNAL_LIST_SELECT_RELATED, "establishment")
        .prefetch_related(*_SIGNAL_LIST_PREFETCH)
    )


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
