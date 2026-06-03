from __future__ import annotations

import uuid
from typing import Literal

from django.db.models import Case, IntegerField, QuerySet, Value, When

from houston.establishments.membership_scope import build_signal_feed_scope_q
from houston.establishments.models import EstablishmentMembership
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES
from houston.signals.models import Signal

ViewMode = Literal["personal", "general"]


def active_signals_for_establishment(*, establishment_id: uuid.UUID) -> QuerySet[Signal]:
    return (
        Signal.objects.filter(
            establishment_id=establishment_id,
            status__in=ACTIVE_SIGNAL_STATUSES,
        )
        .select_related(
            "operational_module",
            "operational_domain",
            "operational_subject",
            "operational_unit",
        )
        .prefetch_related("source_observation_links__observation__media_items")
    )


def apply_feed_sorting(queryset: QuerySet[Signal]) -> QuerySet[Signal]:
    status_order = Case(
        When(status=Signal.Status.OPEN, then=Value(0)),
        When(status=Signal.Status.IN_PROGRESS, then=Value(1)),
        default=Value(2),
        output_field=IntegerField(),
    )
    urgency_order = Case(
        When(urgency=Signal.Urgency.HIGH, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )
    return queryset.order_by(
        "-is_pinned",
        urgency_order,
        status_order,
        "-last_activity_at",
        "-created_at",
    )


def signal_feed_queryset(
    *,
    membership: EstablishmentMembership,
    view_mode: ViewMode,
) -> QuerySet[Signal]:
    queryset = active_signals_for_establishment(establishment_id=membership.establishment_id)

    if view_mode == "general":
        return apply_feed_sorting(queryset)

    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        return apply_feed_sorting(queryset)

    scope_q = build_signal_feed_scope_q(membership=membership)
    if scope_q is None:
        return apply_feed_sorting(queryset.none())
    return apply_feed_sorting(queryset.filter(scope_q))


def get_signal_for_detail(
    *,
    membership: EstablishmentMembership,
    signal_id: uuid.UUID,
) -> Signal | None:
    signal = (
        active_signals_for_establishment(establishment_id=membership.establishment_id)
        .filter(id=signal_id)
        .select_related("pinned_by_membership__user")
        .prefetch_related(
            "source_observation_links__observation__submitted_by_membership__user",
            "source_observation_links__observation__media_items",
        )
        .first()
    )
    if signal is None:
        return None
    if not _can_view_signal_detail(membership, signal):
        return None
    return signal


def _can_view_signal_detail(
    membership: EstablishmentMembership,
    signal: Signal,
) -> bool:
    # Feed listing applies MembershipScope for personal mode; any member who can
    # open the establishment feed may read active signal detail (pin/urgency gated separately).
    from houston.signals.permissions import can_view_signal_feed

    return can_view_signal_feed(membership)
