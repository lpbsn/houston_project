"""Author-pole affected fallback after routing resolution (3-null gate)."""

from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.establishments.taxonomy_snapshot import build_routing_taxonomy
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
    create_membership_with_business_unit_scope,
)
from houston.signals.author_affected_fallback import apply_author_affected_fallback
from houston.signals.models import Signal
from houston.signals.routing_resolver import (
    AUDIT_SOURCES,
    RoutingProposal,
    RoutingResolution,
    resolve_candidate_routing,
)
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership, create_membership

pytestmark = pytest.mark.django_db


def _taxonomy_setup(membership: EstablishmentMembership):
    restaurant = create_business_unit(
        establishment=membership.establishment,
        key="restaurant",
        label="Restaurant",
    )
    bar = create_business_unit(
        establishment=membership.establishment,
        key="bar",
        label="Bar",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=restaurant,
        label="Service",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=bar,
        label="Service",
    )
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment.id)
    return restaurant, bar, taxonomy


def _blank_resolution() -> RoutingResolution:
    return RoutingResolution(
        affected_business_unit=None,
        responsible_business_unit=None,
        activity_subject=None,
        operational_unit=None,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        resolution_audit={
            "affected": {"source": "unresolved", "proposed_key": None, "resolved_key": None},
            "responsible": {
                "source": "unresolved",
                "proposed_key": None,
                "resolved_key": None,
            },
            "subject": {"source": "unresolved", "proposed_key": None, "resolved_key": None},
        },
    )


def test_author_scope_fallback_in_audit_sources():
    assert "author_scope_fallback" in AUDIT_SOURCES


def test_three_null_with_unique_author_pole_sets_affected_only():
    membership = build_membership(role=EstablishmentMembership.Role.STAFF)
    restaurant, _bar, taxonomy = _taxonomy_setup(membership)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=restaurant,
    )
    observation = create_observation(membership=membership)

    result = apply_author_affected_fallback(
        observation=observation,
        resolution=_blank_resolution(),
        routing_taxonomy=taxonomy,
    )

    assert result.affected_business_unit is not None
    assert result.affected_business_unit.id == restaurant.id
    assert result.responsible_business_unit is None
    assert result.activity_subject is None
    assert result.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert result.resolution_audit["affected"]["source"] == "author_scope_fallback"
    assert result.resolution_audit["affected"]["resolved_key"] == restaurant.routing_key


def test_resolved_affected_preserved_when_responsible_and_subject_null():
    membership = build_membership(role=EstablishmentMembership.Role.STAFF)
    restaurant, bar, taxonomy = _taxonomy_setup(membership)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=bar,
    )
    observation = create_observation(membership=membership)
    resolution = RoutingResolution(
        affected_business_unit=restaurant,
        responsible_business_unit=None,
        activity_subject=None,
        operational_unit=None,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        resolution_audit={
            "affected": {
                "source": "llm_validated",
                "proposed_key": restaurant.routing_key,
                "resolved_key": restaurant.routing_key,
            },
            "responsible": {
                "source": "unresolved",
                "proposed_key": None,
                "resolved_key": None,
            },
            "subject": {"source": "unresolved", "proposed_key": None, "resolved_key": None},
        },
    )

    result = apply_author_affected_fallback(
        observation=observation,
        resolution=resolution,
        routing_taxonomy=taxonomy,
    )

    assert result.affected_business_unit is not None
    assert result.affected_business_unit.id == restaurant.id
    assert result.responsible_business_unit is None
    assert result.activity_subject is None
    assert result.resolution_audit["affected"]["source"] == "llm_validated"


def test_no_author_pole_leaves_three_null():
    membership = build_membership(role=EstablishmentMembership.Role.STAFF)
    _restaurant, _bar, taxonomy = _taxonomy_setup(membership)
    observation = create_observation(membership=membership)

    result = apply_author_affected_fallback(
        observation=observation,
        resolution=_blank_resolution(),
        routing_taxonomy=taxonomy,
    )

    assert result.affected_business_unit is None
    assert result.responsible_business_unit is None
    assert result.activity_subject is None


def test_multi_author_poles_leave_three_null():
    membership = build_membership(role=EstablishmentMembership.Role.MANAGER)
    restaurant, bar, taxonomy = _taxonomy_setup(membership)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=restaurant,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=bar,
    )
    observation = create_observation(membership=membership)

    result = apply_author_affected_fallback(
        observation=observation,
        resolution=_blank_resolution(),
        routing_taxonomy=taxonomy,
    )

    assert result.affected_business_unit is None
    assert result.responsible_business_unit is None
    assert result.activity_subject is None


def test_inactive_author_pole_not_used():
    membership = build_membership(role=EstablishmentMembership.Role.STAFF)
    restaurant, _bar, taxonomy = _taxonomy_setup(membership)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=restaurant,
    )
    restaurant.active = False
    restaurant.save(update_fields=["active", "updated_at"])
    observation = create_observation(membership=membership)

    result = apply_author_affected_fallback(
        observation=observation,
        resolution=_blank_resolution(),
        routing_taxonomy=taxonomy,
    )

    assert result.affected_business_unit is None


def test_owner_author_without_scopes_leaves_three_null():
    membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    _restaurant, _bar, taxonomy = _taxonomy_setup(membership)
    observation = create_observation(membership=membership)

    result = apply_author_affected_fallback(
        observation=observation,
        resolution=_blank_resolution(),
        routing_taxonomy=taxonomy,
    )

    assert result.affected_business_unit is None


def test_pipeline_resolve_then_fallback_never_sets_responsible_from_author():
    membership = build_membership(role=EstablishmentMembership.Role.STAFF)
    restaurant, _bar, taxonomy = _taxonomy_setup(membership)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=restaurant,
    )
    observation = create_observation(membership=membership)
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment_id,
        proposal=RoutingProposal(),
        routing_taxonomy=taxonomy,
    )
    result = apply_author_affected_fallback(
        observation=observation,
        resolution=resolution,
        routing_taxonomy=taxonomy,
    )

    assert result.affected_business_unit is not None
    assert result.affected_business_unit.id == restaurant.id
    assert result.responsible_business_unit is None
    assert result.activity_subject is None


def test_director_author_without_scopes_leaves_three_null():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    _restaurant, _bar, taxonomy = _taxonomy_setup(owner)
    director = create_membership(
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    observation = create_observation(membership=director)

    result = apply_author_affected_fallback(
        observation=observation,
        resolution=_blank_resolution(),
        routing_taxonomy=taxonomy,
    )
    assert result.affected_business_unit is None


def test_unique_author_pole_without_subjects_sets_affected_only():
    """Author BU need not be in routing_taxonomy (no activity subjects)."""
    membership = build_membership(role=EstablishmentMembership.Role.MANAGER)
    communication = create_business_unit(
        establishment=membership.establishment,
        key="communication",
        label="Communication",
    )
    # No activity subjects → BU absent from build_routing_taxonomy.
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=communication,
    )
    observation = create_observation(membership=membership)
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment.id)
    assert taxonomy.get("business_units") == []

    result = apply_author_affected_fallback(
        observation=observation,
        resolution=_blank_resolution(),
        routing_taxonomy=taxonomy,
    )

    assert result.affected_business_unit is not None
    assert result.affected_business_unit.id == communication.id
    assert result.responsible_business_unit is None
    assert result.activity_subject is None
    assert result.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert result.resolution_audit["affected"]["source"] == "author_scope_fallback"
