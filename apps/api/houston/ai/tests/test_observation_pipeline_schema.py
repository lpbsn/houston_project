from __future__ import annotations

import pytest
from pydantic import ValidationError

from houston.ai.observation_pipeline_schema import ObservationPipelineOutput
from houston.signals.constants import (
    AI_ISSUE_FOCUS_MAX_LENGTH,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
)


def _valid_candidate(**overrides):
    base = {
        "title": "Clim en panne",
        "structured_summary": "La climatisation ne fonctionne plus.",
        "issue_focus": "clim chambre 104",
        "affected_business_unit_key": "hotel",
        "responsible_business_unit_key": "maintenance",
        "activity_subject_key": "climatisation",
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
    assert output.candidates[0].activity_subject_key == "climatisation"


def test_rejects_wrong_top_level_shape():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "signals": [],
            }
        )


def test_rejects_legacy_operational_keys():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [
                    {
                        **_valid_candidate(),
                        "operational_module_key": "hotel",
                    }
                ],
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


def test_rejects_missing_issue_focus():
    payload = _valid_candidate()
    del payload["issue_focus"]
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [payload],
            }
        )


def test_rejects_issue_focus_longer_than_80():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [_valid_candidate(issue_focus="x" * (AI_ISSUE_FOCUS_MAX_LENGTH + 1))],
            }
        )


def test_accepts_issue_focus_up_to_80_chars():
    focus = "x" * AI_ISSUE_FOCUS_MAX_LENGTH
    output = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [_valid_candidate(issue_focus=focus)],
        }
    )
    assert output.candidates[0].issue_focus == focus


def test_rejects_more_than_five_candidates():
    candidates = [_valid_candidate(title=f"Issue {index}") for index in range(6)]
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": candidates,
            }
        )
