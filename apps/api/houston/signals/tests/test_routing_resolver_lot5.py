"""Lot 5 — resolver matrix, purity, cross-establishment, create validation."""

from __future__ import annotations

import json
import uuid

import pytest

from houston.ai.observation_pipeline_schema import PipelineCandidateOutput
from houston.establishments.models import ActivitySubject
from houston.establishments.taxonomy_normalization import normalize_activity_subject_name
from houston.establishments.taxonomy_snapshot import build_routing_taxonomy
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.exceptions import SignalValidationError
from houston.signals.models import Signal
from houston.signals.routing_resolver import (
    AUDIT_SOURCES,
    RoutingProposal,
    index_routing_taxonomy,
    materialize_routing_fks,
    resolve_candidate_routing,
    resolve_routing_keys,
    routing_proposal_from_pipeline_candidate,
)
from houston.signals.services import ResolvedTaxonomy, create_signal_from_candidate
from houston.signals.signal_classification import (
    InvalidSignalClassificationError,
    validate_partial_signal_routing,
)
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership, create_establishment

pytestmark = pytest.mark.django_db

SHARED_SUBJECT_ROUTING_KEY = "custom--shared-stock"


def _create_subject_with_routing_key(
    *,
    establishment,
    business_unit,
    label: str,
    routing_key: str,
) -> ActivitySubject:
    subject_id = uuid.uuid4()
    return ActivitySubject.objects.create(
        id=subject_id,
        establishment=establishment,
        business_unit=business_unit,
        normalized_name=normalize_activity_subject_name(label),
        label=label,
        routing_key=routing_key,
        source=ActivitySubject.Source.MANUAL,
        active=True,
    )


def _duplicate_subject_setup(membership):
    """Two poles sharing one subject routing_key, plus a third BU without it."""
    pole_a = create_business_unit(
        establishment=membership.establishment,
        key="restaurant",
        label="Restaurant A",
    )
    pole_b = create_business_unit(
        establishment=membership.establishment,
        key="restaurant",
        label="Restaurant B",
    )
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
        unit_type="transversal",
    )
    # Distinct subject so maintenance appears in routing_taxonomy (BU-with-subjects only).
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label="Plomberie",
    )
    subject_a = _create_subject_with_routing_key(
        establishment=membership.establishment,
        business_unit=pole_a,
        label="Stock",
        routing_key=SHARED_SUBJECT_ROUTING_KEY,
    )
    subject_b = _create_subject_with_routing_key(
        establishment=membership.establishment,
        business_unit=pole_b,
        label="Stock",
        routing_key=SHARED_SUBJECT_ROUTING_KEY,
    )
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment.id)
    return pole_a, pole_b, maintenance, subject_a, subject_b, taxonomy


def _candidate(**kwargs) -> PipelineCandidateOutput:
    base = {
        "title": "Issue",
        "structured_summary": "Structured summary for Lot 5.",
        "issue_focus": "focus",
        "canonical_object": "object",
        "signal_kind": "actionable",
        "expected_action": "inspect",
        "information_type": None,
        "operational_unit_key": None,
        "location_text": None,
    }
    base.update(kwargs)
    return PipelineCandidateOutput(**base)


def test_resolve_routing_keys_is_pure_no_db_hits(django_assert_num_queries):
    index = index_routing_taxonomy(
        {
            "business_units": [
                {
                    "routing_key": "hotel",
                    "activity_subjects": [{"routing_key": "menage"}],
                }
            ],
            "operational_units": [],
        }
    )
    proposal = RoutingProposal(
        affected_business_unit_routing_key="hotel",
        responsible_business_unit_routing_key="maintenance",
        activity_subject_routing_key="menage",
    )
    with django_assert_num_queries(0):
        result = resolve_routing_keys(proposal, index)
    assert result.activity_subject_routing_key == "menage"
    assert result.responsible_business_unit_routing_key == "hotel"
    assert result.resolution_audit["responsible"]["source"] == "responsible_corrected"


def test_resolve_candidate_routing_requires_taxonomy():
    membership = build_membership()
    with pytest.raises(ValueError, match="routing_taxonomy is required"):
        resolve_candidate_routing(
            establishment_id=membership.establishment_id,
            proposal=RoutingProposal(),
            routing_taxonomy=None,  # type: ignore[arg-type]
        )


def test_subject_valid_responsible_wrong_pole_corrected():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment, key="hotel", label="Hôtel"
    )
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
        unit_type="transversal",
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Ménage",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label="Plomberie",
    )
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment.id)
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment.id,
        proposal=routing_proposal_from_pipeline_candidate(
            _candidate(
                affected_business_unit_routing_key=hotel.routing_key,
                responsible_business_unit_routing_key=maintenance.routing_key,
                activity_subject_routing_key=subject.routing_key,
            )
        ),
        routing_taxonomy=taxonomy,
    )
    assert resolution.routing_status == Signal.RoutingStatus.RESOLVED
    assert resolution.responsible_business_unit is not None
    assert resolution.responsible_business_unit.id == hotel.id
    assert resolution.resolution_audit["responsible"]["source"] == "responsible_corrected"


def test_responsible_alone_is_unassigned_with_null_subject():
    membership = build_membership()
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
        unit_type="transversal",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label="Plomberie",
    )
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment.id)
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment.id,
        proposal=RoutingProposal(
            responsible_business_unit_routing_key=maintenance.routing_key,
        ),
        routing_taxonomy=taxonomy,
    )
    assert resolution.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert resolution.responsible_business_unit is not None
    assert resolution.responsible_business_unit.id == maintenance.id
    assert resolution.activity_subject is None


def test_incoherent_subject_responsible_rejected_by_partial_validation():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment, key="hotel", label="Hôtel"
    )
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
        unit_type="transversal",
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Ménage",
    )
    with pytest.raises(InvalidSignalClassificationError):
        validate_partial_signal_routing(
            establishment=membership.establishment,
            affected_business_unit=hotel,
            responsible_business_unit=maintenance,
            activity_subject=subject,
        )


def test_custom_subject_explicit_accepted_without_capability_autocomplete():
    membership = build_membership()
    bar = create_business_unit(
        establishment=membership.establishment, key="bar", label="Bar"
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=bar,
        label="Machine à café",
    )
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment.id)
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment.id,
        proposal=routing_proposal_from_pipeline_candidate(
            _candidate(
                affected_business_unit_routing_key=bar.routing_key,
                responsible_business_unit_routing_key=bar.routing_key,
                activity_subject_routing_key=subject.routing_key,
            )
        ),
        routing_taxonomy=taxonomy,
    )
    assert resolution.routing_status == Signal.RoutingStatus.RESOLVED
    assert resolution.activity_subject is not None
    assert resolution.activity_subject.id == subject.id
    assert "unique_capability_match" not in {
        resolution.resolution_audit["subject"]["source"],
        resolution.resolution_audit["responsible"]["source"],
    }


def test_cross_establishment_keys_do_not_materialize():
    membership_a = build_membership()
    membership_b = build_membership()
    hotel_b = create_business_unit(
        establishment=membership_b.establishment, key="hotel", label="Hôtel B"
    )
    subject_b = create_activity_subject(
        establishment=membership_b.establishment,
        business_unit=hotel_b,
        label="Ménage",
    )
    # Establishment A has its own routable taxonomy with different keys.
    hotel_a = create_business_unit(
        establishment=membership_a.establishment, key="spa", label="Spa A"
    )
    create_activity_subject(
        establishment=membership_a.establishment,
        business_unit=hotel_a,
        label="Accueil",
    )
    taxonomy_a = build_routing_taxonomy(establishment_id=membership_a.establishment.id)
    resolution = resolve_candidate_routing(
        establishment_id=membership_a.establishment.id,
        proposal=RoutingProposal(
            affected_business_unit_routing_key=hotel_b.routing_key,
            responsible_business_unit_routing_key=hotel_b.routing_key,
            activity_subject_routing_key=subject_b.routing_key,
        ),
        routing_taxonomy=taxonomy_a,
    )
    assert resolution.affected_business_unit is None
    assert resolution.responsible_business_unit is None
    assert resolution.activity_subject is None
    assert resolution.routing_status == Signal.RoutingStatus.UNASSIGNED


def test_create_signal_rejects_inconsistent_routing_status():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment, key="hotel", label="Hôtel"
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Ménage",
    )
    observation = create_observation(membership=membership)
    resolved = ResolvedTaxonomy(
        operational_unit=None,
        affected_business_unit=hotel,
        responsible_business_unit=None,
        activity_subject=None,
    )
    with pytest.raises(SignalValidationError) as exc_info:
        create_signal_from_candidate(
            observation=observation,
            candidate=_candidate(
                affected_business_unit_routing_key=hotel.routing_key,
                responsible_business_unit_routing_key=hotel.routing_key,
                activity_subject_routing_key=subject.routing_key,
            ),
            resolved=resolved,
            title="Issue",
            structured_summary="Summary",
            routing_status=Signal.RoutingStatus.RESOLVED,
        )
    assert exc_info.value.code == "inconsistent_routing_status"


def test_materialize_routing_fks_filters_by_establishment():
    membership = build_membership()
    other = create_establishment()
    hotel = create_business_unit(
        establishment=membership.establishment, key="hotel", label="Hôtel"
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Ménage",
    )
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment.id)
    keys = resolve_routing_keys(
        RoutingProposal(
            affected_business_unit_routing_key=hotel.routing_key,
            responsible_business_unit_routing_key=hotel.routing_key,
            activity_subject_routing_key=subject.routing_key,
        ),
        index_routing_taxonomy(taxonomy),
    )
    materialized = materialize_routing_fks(
        establishment_id=other.id,
        key_resolution=keys,
    )
    assert materialized.affected_business_unit is None
    assert materialized.responsible_business_unit is None
    assert materialized.activity_subject is None


def test_index_aggregates_duplicate_subject_keys_across_business_units():
    index = index_routing_taxonomy(
        {
            "business_units": [
                {
                    "routing_key": "pole_a",
                    "activity_subjects": [{"routing_key": SHARED_SUBJECT_ROUTING_KEY}],
                },
                {
                    "routing_key": "pole_b",
                    "activity_subjects": [{"routing_key": SHARED_SUBJECT_ROUTING_KEY}],
                },
                {"routing_key": "maintenance", "activity_subjects": []},
            ],
            "operational_units": [],
        }
    )
    assert index.subject_to_business_units[SHARED_SUBJECT_ROUTING_KEY] == frozenset(
        {"pole_a", "pole_b"}
    )
    assert "ambiguous_key" in AUDIT_SOURCES


def test_duplicate_subject_alone_is_unassigned_with_ambiguous_audit():
    membership = build_membership()
    _pole_a, _pole_b, _maintenance, _subject_a, _subject_b, taxonomy = (
        _duplicate_subject_setup(membership)
    )
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment.id,
        proposal=RoutingProposal(
            activity_subject_routing_key=SHARED_SUBJECT_ROUTING_KEY,
        ),
        routing_taxonomy=taxonomy,
    )
    assert resolution.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert resolution.activity_subject is None
    assert resolution.responsible_business_unit is None
    assert resolution.resolution_audit["subject"]["source"] == "ambiguous_key"
    assert resolution.resolution_audit["responsible"]["source"] == "unresolved"
    assert resolution.resolution_audit["subject"]["candidate_business_unit_keys"] == sorted(
        resolution.resolution_audit["subject"]["candidate_business_unit_keys"]
    )
    json.dumps(resolution.resolution_audit)


def test_duplicate_subject_disambiguated_by_responsible_in_set():
    membership = build_membership()
    pole_a, pole_b, _maintenance, subject_a, subject_b, taxonomy = _duplicate_subject_setup(
        membership
    )
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment.id,
        proposal=RoutingProposal(
            affected_business_unit_routing_key=pole_a.routing_key,
            responsible_business_unit_routing_key=pole_a.routing_key,
            activity_subject_routing_key=SHARED_SUBJECT_ROUTING_KEY,
        ),
        routing_taxonomy=taxonomy,
    )
    assert resolution.routing_status == Signal.RoutingStatus.RESOLVED
    assert resolution.responsible_business_unit is not None
    assert resolution.responsible_business_unit.id == pole_a.id
    assert resolution.activity_subject is not None
    assert resolution.activity_subject.id == subject_a.id
    assert resolution.activity_subject.id != subject_b.id
    assert resolution.activity_subject.business_unit_id == pole_a.id
    assert resolution.activity_subject.business_unit_id != pole_b.id
    assert resolution.resolution_audit["subject"]["source"] == "llm_validated"
    assert resolution.resolution_audit["responsible"]["source"] == "llm_validated"


def test_duplicate_subject_with_responsible_outside_set_keeps_responsible():
    membership = build_membership()
    _pole_a, _pole_b, maintenance, _subject_a, _subject_b, taxonomy = (
        _duplicate_subject_setup(membership)
    )
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment.id,
        proposal=RoutingProposal(
            responsible_business_unit_routing_key=maintenance.routing_key,
            activity_subject_routing_key=SHARED_SUBJECT_ROUTING_KEY,
        ),
        routing_taxonomy=taxonomy,
    )
    assert resolution.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert resolution.responsible_business_unit is not None
    assert resolution.responsible_business_unit.id == maintenance.id
    assert resolution.activity_subject is None
    assert resolution.resolution_audit["subject"]["source"] == "ambiguous_key"
    assert resolution.resolution_audit["responsible"]["source"] == "llm_validated"
    json.dumps(resolution.resolution_audit)


def test_duplicate_subject_with_invalid_responsible_clears_both():
    membership = build_membership()
    _pole_a, _pole_b, _maintenance, _subject_a, _subject_b, taxonomy = (
        _duplicate_subject_setup(membership)
    )
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment.id,
        proposal=RoutingProposal(
            responsible_business_unit_routing_key="unknown_pole",
            activity_subject_routing_key=SHARED_SUBJECT_ROUTING_KEY,
        ),
        routing_taxonomy=taxonomy,
    )
    assert resolution.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert resolution.responsible_business_unit is None
    assert resolution.activity_subject is None
    assert resolution.resolution_audit["subject"]["source"] == "ambiguous_key"
    assert resolution.resolution_audit["responsible"]["source"] == "invalid_key"
    json.dumps(resolution.resolution_audit)
