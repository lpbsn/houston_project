from __future__ import annotations

import pytest
from pydantic import ValidationError

from houston.ai.observation_pipeline_schema import ObservationPipelineOutput
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION


def _valid_candidate(**overrides):
    base = {
        "title": "Clim en panne",
        "structured_summary": "La climatisation ne fonctionne plus.",
        "operational_module_key": "hotel",
        "operational_domain_key": "hotel__hebergement",
        "operational_subject_key": "hotel__hebergement__maintenance",
        "operational_unit_key": None,
        "location_text": None,
        "aggregate_into_signal_id": None,
    }
    base.update(overrides)
    return base


def test_accepts_valid_payload():
    output = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [_valid_candidate()],
        }
    )

    assert output.schema_version == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
    assert len(output.candidates) == 1
    assert output.candidates[0].operational_subject_key.endswith("maintenance")


def test_rejects_wrong_top_level_shape():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "signals": [],
            }
        )


def test_accepts_location_text_string_and_null():
    with_null = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [_valid_candidate(location_text=None)],
        }
    )
    assert with_null.candidates[0].location_text is None

    with_text = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [_valid_candidate(location_text="Entrée restaurant")],
        }
    )
    assert with_text.candidates[0].location_text == "Entrée restaurant"


def test_rejects_location_text_longer_than_120():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [_valid_candidate(location_text="x" * 121)],
            }
        )


def test_rejects_more_than_five_candidates():
    candidates = [_valid_candidate(title=f"Issue {index}") for index in range(6)]
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": candidates,
            }
        )
