"""Post-resolver author-pole fallback for totally unclassified candidates.

Applies only when affected, responsible, and activity_subject are all null and
the observation author has exactly one active MembershipScope business unit.
Never sets responsible from the author pole. Never overwrites an
already-materialized affected business unit.
"""

from __future__ import annotations

import uuid
from typing import Any

from houston.establishments.models import BusinessUnit, MembershipScope
from houston.observations.models import Observation
from houston.signals.models import Signal
from houston.signals.routing_resolver import (
    RoutingResolution,
    build_dimension_audit,
)


def _unique_reliable_author_business_unit(
    *,
    observation: Observation,
) -> BusinessUnit | None:
    """Return the author's unique active scoped BU, or None if not exactly one.

    Does not require the BU to appear in routing_taxonomy (subjects). Affected-only
    UNASSIGNED signals are valid without activity subjects.
    """
    membership = observation.submitted_by_membership
    if membership is None:
        return None

    candidates: list[BusinessUnit] = []
    seen_ids: set[uuid.UUID] = set()
    scopes = MembershipScope.objects.filter(membership_id=membership.id).select_related(
        "business_unit",
    )
    for scope in scopes:
        business_unit = scope.business_unit
        if business_unit is None:
            continue
        if business_unit.establishment_id != observation.establishment_id:
            continue
        if not business_unit.active:
            continue
        if not business_unit.routing_key:
            continue
        if business_unit.id in seen_ids:
            continue
        seen_ids.add(business_unit.id)
        candidates.append(business_unit)

    if len(candidates) != 1:
        return None
    return candidates[0]


def apply_author_affected_fallback(
    *,
    observation: Observation,
    resolution: RoutingResolution,
    routing_taxonomy: dict[str, Any],
) -> RoutingResolution:
    """Set affected from unique author pole when the candidate is totally unclassified."""
    _ = routing_taxonomy  # call-site stable; author pole is membership-only (not taxonomy)
    if (
        resolution.affected_business_unit is not None
        or resolution.responsible_business_unit is not None
        or resolution.activity_subject is not None
    ):
        return resolution

    author_bu = _unique_reliable_author_business_unit(observation=observation)
    if author_bu is None:
        return resolution

    audit = dict(resolution.resolution_audit)
    audit["affected"] = build_dimension_audit(
        source="author_scope_fallback",
        proposed_key=None,
        resolved_key=author_bu.routing_key,
    )
    return RoutingResolution(
        affected_business_unit=author_bu,
        responsible_business_unit=None,
        activity_subject=None,
        operational_unit=resolution.operational_unit,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        resolution_audit=audit,
    )
