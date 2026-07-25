from __future__ import annotations

import pytest
from pydantic import ValidationError

from houston.ai.observation_pipeline_schema import ObservationPipelineOutput
from houston.signals.constants import (
    AI_INFORMATION_TYPE_MAX_LENGTH,
    AI_ISSUE_FOCUS_MAX_LENGTH,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
)


def _valid_candidate(**overrides):
    base = {
        "title": "Clim en panne",
        "structured_summary": "La climatisation ne fonctionne plus.",
        "issue_focus": "clim chambre 104",
        "canonical_object": "clim",
        "signal_kind": "actionable",
        "expected_action": "repair",
        "information_type": None,
        "affected_business_unit_routing_key": "hotel",
        "responsible_business_unit_routing_key": "maintenance",
        "activity_subject_routing_key": "climatisation",
        "operational_unit_key": None,
        "location_text": None,
    }
    base.update(overrides)
    return base


def test_schema_version_is_v6():
    assert AI_OBSERVATION_PIPELINE_SCHEMA_VERSION == "ai_observation_pipeline_v6"


def test_rejects_wrong_schema_version():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": "ai_observation_pipeline_v5",
                "candidates": [_valid_candidate()],
            }
        )


def test_accepts_valid_payload():
    output = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [_valid_candidate()],
        }
    )

    assert output.schema_version == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
    assert len(output.candidates) == 1
    assert output.candidates[0].activity_subject_routing_key == "climatisation"
    assert output.candidates[0].canonical_object == "clim"
    assert output.candidates[0].signal_kind == "actionable"
    assert output.candidates[0].information_type is None


def test_accepts_null_routing_keys():
    output = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [
                _valid_candidate(
                    affected_business_unit_routing_key=None,
                    responsible_business_unit_routing_key=None,
                    activity_subject_routing_key=None,
                )
            ],
        }
    )
    candidate = output.candidates[0]
    assert candidate.affected_business_unit_routing_key is None
    assert candidate.responsible_business_unit_routing_key is None
    assert candidate.activity_subject_routing_key is None


def test_accepts_zero_one_and_multiple_candidates():
    empty = ObservationPipelineOutput.model_validate(
        {"schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION, "candidates": []}
    )
    assert empty.candidates == []

    one = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [_valid_candidate()],
        }
    )
    assert len(one.candidates) == 1

    many = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [
                _valid_candidate(title=f"Issue {index}", issue_focus=f"focus {index}")
                for index in range(3)
            ],
        }
    )
    assert len(many.candidates) == 3


def test_rejects_more_than_five_candidates():
    candidates = [_valid_candidate(title=f"Issue {index}") for index in range(6)]
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": candidates,
            }
        )


def test_rejects_invalid_signal_kind_and_expected_action():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [_valid_candidate(signal_kind="unknown")],
            }
        )
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [_valid_candidate(expected_action="fly")],
            }
        )


def test_accepts_null_expected_action():
    output = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [_valid_candidate(expected_action=None)],
        }
    )
    assert output.candidates[0].expected_action is None


def test_information_type_null_for_actionable():
    output = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [_valid_candidate(signal_kind="actionable", information_type=None)],
        }
    )
    assert output.candidates[0].information_type is None


def test_information_type_rejects_empty_string_for_actionable():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [_valid_candidate(signal_kind="actionable", information_type="")],
            }
        )


def test_information_type_required_non_empty_for_informational():
    output = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [
                _valid_candidate(
                    signal_kind="informational",
                    expected_action="inform",
                    information_type="schedule_update",
                )
            ],
        }
    )
    assert output.candidates[0].information_type == "schedule_update"

    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [
                    _valid_candidate(
                        signal_kind="informational",
                        expected_action="inform",
                        information_type=None,
                    )
                ],
            }
        )

    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [
                    _valid_candidate(
                        signal_kind="informational",
                        expected_action="inform",
                        information_type="   ",
                    )
                ],
            }
        )


def test_information_type_max_length_and_no_silent_normalize():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [
                    _valid_candidate(
                        signal_kind="informational",
                        expected_action="monitor",
                        information_type="x" * (AI_INFORMATION_TYPE_MAX_LENGTH + 1),
                    )
                ],
            }
        )

    spaced = "  schedule_update  "
    output = ObservationPipelineOutput.model_validate(
        {
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "candidates": [
                _valid_candidate(
                    signal_kind="informational",
                    expected_action="inform",
                    information_type=spaced,
                )
            ],
        }
    )
    # No silent trim: original string preserved when strip()-non-empty.
    assert output.candidates[0].information_type == spaced


def test_rejects_wrong_top_level_shape():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "signals": [],
            }
        )


def test_rejects_legacy_and_backend_only_fields():
    for extra in (
        "operational_module_key",
        "routing_status",
        "resolution_audit",
        "rejection_code",
        "aggregate_into_signal_id",
    ):
        with pytest.raises(ValidationError):
            ObservationPipelineOutput.model_validate(
                {
                    "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                    "candidates": [{**_valid_candidate(), extra: "x"}],
                }
            )


def test_rejects_missing_required_fields():
    for field in ("issue_focus", "canonical_object", "signal_kind", "information_type"):
        payload = _valid_candidate()
        del payload[field]
        with pytest.raises(ValidationError):
            ObservationPipelineOutput.model_validate(
                {
                    "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                    "candidates": [payload],
                }
            )


def test_rejects_null_issue_focus_at_parse():
    with pytest.raises(ValidationError):
        ObservationPipelineOutput.model_validate(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [_valid_candidate(issue_focus=None)],
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


def test_rejects_whitespace_only_issue_focus_after_normalize():
    from houston.signals.exceptions import SignalPipelineCandidateError
    from houston.signals.services import require_normalized_issue_focus

    with pytest.raises(SignalPipelineCandidateError):
        require_normalized_issue_focus("   ")
