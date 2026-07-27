"""Deterministic lexical anchoring for responsible-without-subject proposals."""

from __future__ import annotations

import pytest

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.taxonomy_snapshot import build_routing_taxonomy
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
    create_membership_with_business_unit_scope,
)
from houston.signals.author_affected_fallback import apply_author_affected_fallback
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.models import CandidateSignal, Signal
from houston.signals.responsible_text_anchoring import (
    anchor_tokens,
    business_unit_anchor_phrases,
    is_responsible_textually_anchored,
    sanitize_unanchored_responsible_without_subject,
    sequence_in,
)
from houston.signals.routing_resolver import (
    AUDIT_SOURCES,
    RoutingProposal,
    resolve_candidate_routing,
)
from houston.signals.services import apply_pipeline_output
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def _candidate(
    *,
    text_focus: str = "situation inhabituelle",
    affected_key: str | None = None,
    responsible_key: str | None = None,
    subject_key: str | None = None,
) -> PipelineCandidateOutput:
    return PipelineCandidateOutput(
        title="Signalement",
        structured_summary="Description factuelle du signalement.",
        issue_focus=text_focus,
        canonical_object="situation",
        signal_kind="informational",
        expected_action="inform",
        information_type="status_update",
        affected_business_unit_routing_key=affected_key,
        responsible_business_unit_routing_key=responsible_key,
        activity_subject_routing_key=subject_key,
        operational_unit_key=None,
        location_text=None,
    )


def test_audit_sources_include_anchoring_outcomes():
    assert "responsible_text_anchored" in AUDIT_SOURCES
    assert "responsible_unanchored_rejected" in AUDIT_SOURCES


def test_case_insensitive_anchor():
    membership = build_membership()
    communication = create_business_unit(
        establishment=membership.establishment,
        key="communication",
        label="Communication",
    )
    assert is_responsible_textually_anchored(
        validated_text="Merci de prévenir COMMUNICATION demain.",
        responsible_bu=communication,
    )


def test_accent_insensitive_anchor():
    membership = build_membership()
    events = create_business_unit(
        establishment=membership.establishment,
        key="evenements",
        label="Événements",
    )
    assert is_responsible_textually_anchored(
        validated_text="À transmettre aux Evenements du site.",
        responsible_bu=events,
    )


def test_punctuation_and_hyphen_normalization():
    membership = build_membership()
    food = create_business_unit(
        establishment=membership.establishment,
        key="food_court",
        label="Food Court",
    )
    assert is_responsible_textually_anchored(
        validated_text="Incident au food-court ce matin.",
        responsible_bu=food,
    )


def test_compound_label_requires_contiguous_token_sequence():
    membership = build_membership()
    food = create_business_unit(
        establishment=membership.establishment,
        key="food_court",
        label="Food Court",
    )
    assert is_responsible_textually_anchored(
        validated_text="Fuite food court nord.",
        responsible_bu=food,
    )
    assert not is_responsible_textually_anchored(
        validated_text="Food disponible près du court de tennis.",
        responsible_bu=food,
    )


def test_generic_label_alias_anchors_when_distinct():
    membership = build_membership()
    grill = create_business_unit(
        establishment=membership.establishment,
        key="restaurant",
        label="Yakinuku Grill",
    )
    catalog = grill.catalog_business_unit
    assert catalog is not None
    catalog.label = "Restaurant"
    catalog.save(update_fields=["label", "updated_at"])
    grill.refresh_from_db()

    phrases = business_unit_anchor_phrases(grill)
    assert "Yakinuku Grill" in phrases
    assert "Restaurant" in phrases
    assert is_responsible_textually_anchored(
        validated_text="À traiter par le Restaurant ce soir.",
        responsible_bu=grill,
    )


def test_substring_does_not_match_longer_token():
    membership = build_membership()
    bar = create_business_unit(
        establishment=membership.establishment,
        key="bar",
        label="Bar",
    )
    assert not is_responsible_textually_anchored(
        validated_text="Réparer la barrière du parking.",
        responsible_bu=bar,
    )
    assert not sequence_in(
        haystack=anchor_tokens("Reparer la barriere du parking."),
        needle=anchor_tokens("Bar"),
    )


def test_routing_key_is_not_used_as_anchor_phrase():
    membership = build_membership()
    communication = create_business_unit(
        establishment=membership.establishment,
        key="communication",
        label="Communication",
    )
    phrases = business_unit_anchor_phrases(communication)
    assert communication.routing_key not in phrases
    # Hex suffix alone (technical fragment) must not anchor via routing_key.
    hex_part = communication.routing_key.rsplit("--", 1)[-1]
    assert not is_responsible_textually_anchored(
        validated_text=f"Référence technique {hex_part} uniquement.",
        responsible_bu=communication,
    )


def test_semantic_suggestion_without_label_is_rejected():
    membership = build_membership()
    communication = create_business_unit(
        establishment=membership.establishment,
        key="communication",
        label="Communication",
    )
    assert not is_responsible_textually_anchored(
        validated_text="Ça relève clairement de la com pour diffusion.",
        responsible_bu=communication,
    )


def test_fortuitous_label_mention_is_anchored():
    """Lexical anchor proves mention only — not business responsibility."""
    membership = build_membership()
    communication = create_business_unit(
        establishment=membership.establishment,
        key="communication",
        label="Communication",
    )
    assert is_responsible_textually_anchored(
        validated_text="Passage près du bureau Communication sans action demandée.",
        responsible_bu=communication,
    )


def test_sanitize_rejects_unanchored_then_author_fallback_sets_affected_only():
    membership = build_membership(role=EstablishmentMembership.Role.MANAGER)
    communication = create_business_unit(
        establishment=membership.establishment,
        key="communication",
        label="Communication",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=communication,
        label="Contenu",
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=communication,
    )
    observation = create_observation(
        membership=membership,
        text=(
            "Une situation inhabituelle a été signalée sans information permettant "
            "d'identifier la zone, le service ou l'origine concernés."
        ),
    )
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment_id)
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment_id,
        proposal=RoutingProposal(
            responsible_business_unit_routing_key=communication.routing_key,
        ),
        routing_taxonomy=taxonomy,
    )
    assert resolution.responsible_business_unit is not None
    assert resolution.responsible_business_unit.id == communication.id

    sanitized = sanitize_unanchored_responsible_without_subject(
        observation=observation,
        resolution=resolution,
    )
    assert sanitized.responsible_business_unit is None
    assert sanitized.resolution_audit["responsible"]["source"] == (
        "responsible_unanchored_rejected"
    )
    assert sanitized.affected_business_unit is None

    fallback = apply_author_affected_fallback(
        observation=observation,
        resolution=sanitized,
        routing_taxonomy=taxonomy,
    )
    assert fallback.affected_business_unit is not None
    assert fallback.affected_business_unit.id == communication.id
    assert fallback.responsible_business_unit is None
    assert fallback.activity_subject is None
    assert fallback.resolution_audit["affected"]["source"] == "author_scope_fallback"


def test_sanitize_keeps_anchored_responsible_without_subject():
    membership = build_membership()
    communication = create_business_unit(
        establishment=membership.establishment,
        key="communication",
        label="Communication",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=communication,
        label="Contenu",
    )
    observation = create_observation(
        membership=membership,
        text="Merci de transmettre ça à Communication pour diffusion.",
    )
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment_id)
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment_id,
        proposal=RoutingProposal(
            responsible_business_unit_routing_key=communication.routing_key,
        ),
        routing_taxonomy=taxonomy,
    )
    sanitized = sanitize_unanchored_responsible_without_subject(
        observation=observation,
        resolution=resolution,
    )
    assert sanitized.responsible_business_unit is not None
    assert sanitized.responsible_business_unit.id == communication.id
    assert sanitized.resolution_audit["responsible"]["source"] == "responsible_text_anchored"


def test_sanitize_does_not_overwrite_existing_affected():
    membership = build_membership()
    hotel = create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=hotel,
        label="Accueil",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label="Plomberie",
    )
    observation = create_observation(
        membership=membership,
        text="Situation inhabituelle sans précision métier.",
    )
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment_id)
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment_id,
        proposal=RoutingProposal(
            affected_business_unit_routing_key=hotel.routing_key,
            responsible_business_unit_routing_key=maintenance.routing_key,
        ),
        routing_taxonomy=taxonomy,
    )
    sanitized = sanitize_unanchored_responsible_without_subject(
        observation=observation,
        resolution=resolution,
    )
    assert sanitized.affected_business_unit is not None
    assert sanitized.affected_business_unit.id == hotel.id
    assert sanitized.responsible_business_unit is None
    assert sanitized.resolution_audit["responsible"]["source"] == (
        "responsible_unanchored_rejected"
    )


def test_sanitize_noop_when_subject_present():
    membership = build_membership()
    communication = create_business_unit(
        establishment=membership.establishment,
        key="communication",
        label="Communication",
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=communication,
        label="Contenu",
    )
    observation = create_observation(
        membership=membership,
        text="Situation sans nom de pôle.",
    )
    taxonomy = build_routing_taxonomy(establishment_id=membership.establishment_id)
    resolution = resolve_candidate_routing(
        establishment_id=membership.establishment_id,
        proposal=RoutingProposal(
            responsible_business_unit_routing_key=communication.routing_key,
            activity_subject_routing_key=subject.routing_key,
        ),
        routing_taxonomy=taxonomy,
    )
    sanitized = sanitize_unanchored_responsible_without_subject(
        observation=observation,
        resolution=resolution,
    )
    assert sanitized.responsible_business_unit is not None
    assert sanitized.responsible_business_unit.id == communication.id
    assert sanitized.activity_subject is not None
    assert sanitized.activity_subject.id == subject.id
    assert sanitized.resolution_audit["responsible"]["source"] in {
        "llm_validated",
        "subject_derived",
    }


def test_apply_pipeline_rejects_unanchored_responsible_and_applies_author_fallback():
    membership = build_membership(role=EstablishmentMembership.Role.MANAGER)
    communication = create_business_unit(
        establishment=membership.establishment,
        key="communication",
        label="Communication",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=communication,
        label="Contenu",
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=communication,
    )
    observation = create_observation(
        membership=membership,
        text=(
            "Une situation inhabituelle a été signalée sans information permettant "
            "d'identifier la zone, le service ou l'origine concernés."
        ),
    )
    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            _candidate(responsible_key=communication.routing_key),
        ],
    )
    apply_pipeline_output(observation=observation, output=output)

    signal = Signal.objects.get(establishment=membership.establishment)
    assert signal.affected_business_unit_id == communication.id
    assert signal.responsible_business_unit_id is None
    assert signal.activity_subject_id is None
    assert signal.routing_status == Signal.RoutingStatus.UNASSIGNED

    candidate = CandidateSignal.objects.get(observation=observation)
    assert candidate.proposed_responsible_business_unit_routing_key == (
        communication.routing_key
    )
    assert candidate.resolution_audit["responsible"]["source"] == (
        "responsible_unanchored_rejected"
    )
    assert candidate.resolution_audit["affected"]["source"] == "author_scope_fallback"


def test_apply_pipeline_three_null_manager_communication_sets_affected_only():
    membership = build_membership(role=EstablishmentMembership.Role.MANAGER)
    communication = create_business_unit(
        establishment=membership.establishment,
        key="communication",
        label="Communication",
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=communication,
    )
    observation = create_observation(
        membership=membership,
        text=(
            "Une situation inhabituelle a été signalée sans information permettant "
            "d'identifier la zone, le service ou l'origine concernés."
        ),
    )
    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[_candidate()],
    )
    apply_pipeline_output(observation=observation, output=output)

    signal = Signal.objects.get(establishment=membership.establishment)
    assert signal.affected_business_unit_id == communication.id
    assert signal.responsible_business_unit_id is None
    assert signal.activity_subject_id is None
    assert signal.routing_status == Signal.RoutingStatus.UNASSIGNED
    candidate = CandidateSignal.objects.get(observation=observation)
    assert candidate.resolution_audit["affected"]["source"] == "author_scope_fallback"


def test_apply_pipeline_three_null_staff_restaurant_sets_affected_only():
    membership = build_membership(role=EstablishmentMembership.Role.STAFF)
    restaurant = create_business_unit(
        establishment=membership.establishment,
        key="restaurant",
        label="Restaurant",
    )
    create_activity_subject(
        establishment=membership.establishment,
        business_unit=restaurant,
        label="Service",
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=restaurant,
    )
    observation = create_observation(
        membership=membership,
        text=(
            "Une situation inhabituelle a été signalée sans information permettant "
            "d'identifier la zone, le service ou l'origine concernés."
        ),
    )
    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[_candidate()],
    )
    apply_pipeline_output(observation=observation, output=output)

    signal = Signal.objects.get(establishment=membership.establishment)
    assert signal.affected_business_unit_id == restaurant.id
    assert signal.responsible_business_unit_id is None
    assert signal.activity_subject_id is None
    assert signal.routing_status == Signal.RoutingStatus.UNASSIGNED
    candidate = CandidateSignal.objects.get(observation=observation)
    assert candidate.resolution_audit["affected"]["source"] == "author_scope_fallback"
