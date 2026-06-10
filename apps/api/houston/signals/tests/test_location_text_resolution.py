from __future__ import annotations

import pytest

from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import OperationalUnit
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
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
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def _setup_hotel(establishment):
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    return hotel


def _candidate(**overrides) -> PipelineCandidateOutput:
    base = {
        "title": "Issue",
        "structured_summary": "Structured summary for tests.",
        "affected_business_unit_key": "hotel",
        "responsible_business_unit_key": "hotel",
        "activity_subject_key": "maintenance",
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
    _setup_hotel(membership.establishment)
    unit = OperationalUnit.objects.create(
        establishment=membership.establishment,
        key="rooms",
        label="Chambres",
        active=True,
    )
    observation = create_observation(membership=membership, text="Chambre 312 sale.")
    candidate = _candidate(
        operational_unit_key=unit.key,
        location_text="chambre 312",
    )
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
        == "Chambres"
    )


def test_resolve_signal_location_text_uses_candidate_when_no_unit():
    membership = build_membership()
    _setup_hotel(membership.establishment)
    observation = create_observation(membership=membership, text="Problème à l'entrée.")
    candidate = _candidate(location_text="Entrée")
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
        == "Entrée"
    )


def test_resolve_signal_location_text_clears_when_equals_raw_observation():
    membership = build_membership()
    _setup_hotel(membership.establishment)
    raw = "Problème à l'entrée du restaurant."
    observation = create_observation(membership=membership, text=raw)
    candidate = _candidate(location_text=raw)
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


def test_apply_pipeline_output_persists_location_text():
    membership = build_membership()
    _setup_hotel(membership.establishment)
    observation = create_observation(membership=membership, text="Fuite bar.")

    apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                _candidate(
                    title="Fuite",
                    structured_summary="Fuite au bar.",
                    location_text="Bar",
                )
            ],
        ),
    )

    signal = Signal.objects.get()
    assert signal.location_text == "Bar"
