from __future__ import annotations

import pytest

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import OperationalUnit
from houston.establishments.tests.test_permissions import build_membership
from houston.signals.constants import (
    AI_LOCATION_TEXT_MAX_LENGTH,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
)
from houston.signals.models import Signal
from houston.signals.services import (
    apply_pipeline_output,
    normalize_location_text,
    resolve_signal_location_text,
    resolve_taxonomy_from_candidate,
)
from houston.signals.tests.conftest import create_observation, create_taxonomy

pytestmark = pytest.mark.django_db


def _candidate(**overrides) -> PipelineCandidateOutput:
    module, domain, subject = overrides.pop("_taxonomy")
    base = {
        "title": "Issue",
        "structured_summary": "Structured summary for tests.",
        "operational_module_key": module.key,
        "operational_domain_key": domain.key,
        "operational_subject_key": subject.key,
        "operational_unit_key": None,
        "location_text": None,
        "aggregate_into_signal_id": None,
    }
    base.update(overrides)
    return PipelineCandidateOutput(**base)


def test_normalize_location_text_strips_and_truncates():
    assert normalize_location_text(None) == ""
    assert normalize_location_text("  bar  ") == "bar"
    long_text = "x" * (AI_LOCATION_TEXT_MAX_LENGTH + 10)
    assert len(normalize_location_text(long_text)) == AI_LOCATION_TEXT_MAX_LENGTH


def test_resolve_signal_location_text_uses_unit_label_when_unit_present():
    membership = build_membership()
    module, domain, subject = create_taxonomy(membership.establishment)
    unit = OperationalUnit.objects.create(
        establishment=membership.establishment,
        key="rooms",
        label="Chambres",
        active=True,
    )
    observation = create_observation(membership=membership, text="Chambre 312 sale.")
    candidate = _candidate(
        _taxonomy=(module, domain, subject),
        operational_unit_key=unit.key,
        location_text="chambre 312",
    )
    resolved = resolve_taxonomy_from_candidate(
        establishment_id=membership.establishment_id,
        candidate=candidate,
    )
    assert resolve_signal_location_text(
        candidate=candidate,
        resolved=resolved,
        observation=observation,
    ) == "Chambres"


def test_resolve_signal_location_text_uses_candidate_when_no_unit():
    membership = build_membership()
    module, domain, subject = create_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text="Problème à l'entrée.")
    candidate = _candidate(
        _taxonomy=(module, domain, subject),
        location_text="Entrée restaurant",
    )
    resolved = resolve_taxonomy_from_candidate(
        establishment_id=membership.establishment_id,
        candidate=candidate,
    )
    assert resolve_signal_location_text(
        candidate=candidate,
        resolved=resolved,
        observation=observation,
    ) == "Entrée restaurant"


def test_resolve_signal_location_text_clears_exact_raw_text_match():
    membership = build_membership()
    module, domain, subject = create_taxonomy(membership.establishment)
    raw = "La lumière clignote à l'entrée."
    observation = create_observation(membership=membership, text=raw)
    candidate = _candidate(_taxonomy=(module, domain, subject), location_text=raw)
    resolved = resolve_taxonomy_from_candidate(
        establishment_id=membership.establishment_id,
        candidate=candidate,
    )
    assert (
        resolve_signal_location_text(
            candidate=candidate,
            resolved=resolved,
            observation=observation,
        )
        == ""
    )


def test_apply_pipeline_output_stores_unit_label_when_unit_key_valid():
    membership = build_membership()
    module, domain, subject = create_taxonomy(membership.establishment)
    unit = OperationalUnit.objects.create(
        establishment=membership.establishment,
        key="rooms",
        label="Chambres",
        active=True,
    )
    observation = create_observation(membership=membership, text="Chambre 312.")
    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            _candidate(
                _taxonomy=(module, domain, subject),
                operational_unit_key=unit.key,
                location_text="chambre 312",
            )
        ],
    )
    apply_pipeline_output(observation=observation, output=output)
    signal = Signal.objects.get()
    assert signal.operational_unit_id == unit.id
    assert signal.location_text == "Chambres"


def test_apply_pipeline_output_stores_candidate_location_when_no_unit():
    membership = build_membership()
    module, domain, subject = create_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text="Problème bar.")
    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            _candidate(_taxonomy=(module, domain, subject), location_text="Bar")
        ],
    )
    apply_pipeline_output(observation=observation, output=output)
    assert Signal.objects.get().location_text == "Bar"
