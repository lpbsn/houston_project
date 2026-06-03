from __future__ import annotations

import json

from pydantic import ValidationError as PydanticValidationError

from houston.ai.observation_pipeline import ObservationPipelineInvalidOutputError
from houston.ai.observation_pipeline_diagnostics import (
    build_invalid_output_error_context,
    build_provider_bad_request_error_context,
    sanitize_observation_pipeline_error_context,
)
from houston.ai.observation_pipeline_provider_schema import (
    AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME,
)
from houston.ai.observation_pipeline_schema import ObservationPipelineOutput


def test_build_invalid_output_error_context_summarizes_validation_without_sensitive_data():
    try:
        ObservationPipelineOutput.model_validate({"schema_version": "x", "signals": []})
    except PydanticValidationError as exc:
        wrapped = ObservationPipelineInvalidOutputError(
            "Structured output failed validation.",
            payload={"signals": [], "schema_version": "x"},
        )
        wrapped.__cause__ = exc
        context = build_invalid_output_error_context(
            payload=wrapped.payload,
            exc=wrapped,
            provider_request_id="req_test",
            response_format_mode="json_schema_strict",
        )

    assert context["validation_error_count"] >= 1
    assert context["top_level_keys"] == ["schema_version", "signals"]
    assert context["has_candidates"] is False
    assert context["candidate_count"] == 0
    assert context["provider_request_id"] == "req_test"
    assert context["response_format_mode"] == "json_schema_strict"
    serialized = json.dumps(context)
    assert "sirop mojito" not in serialized
    assert "validated_text" not in serialized


def test_sanitize_observation_pipeline_error_context_rejects_disallowed_keys():
    context = sanitize_observation_pipeline_error_context(
        {
            "validation_error_count": 1,
            "first_error_path": "candidates.0.operational_subject_key",
            "first_error_type": "missing",
            "validated_text": "secret observation",
            "prompt": "full prompt",
            "unexpected": "value",
        }
    )

    assert context["validation_error_count"] == 1
    assert context["first_error_path"] == "candidates.0.operational_subject_key"
    assert "validated_text" not in context
    assert "prompt" not in context
    assert "unexpected" not in context


def test_build_provider_bad_request_error_context_is_safe():
    class _FakeBadRequest(Exception):
        param = "response_format"
        code = "invalid_request_error"

    exc = _FakeBadRequest(
        "Invalid schema for response_format 'houston_observation_pipeline_output': "
        "$ref cannot have keywords {'description'}."
    )
    context = build_provider_bad_request_error_context(
        exc=exc,
        response_format_mode="json_schema_strict",
    )

    assert context["provider_error_type"] == "_FakeBadRequest"
    assert context["provider_error_param"] == "response_format"
    assert context["provider_error_code"] == "invalid_request_error"
    assert "Invalid schema" in context["message_excerpt"]
    assert context["response_format_name"] == AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME
    assert context["response_format_mode"] == "json_schema_strict"
    serialized = json.dumps(context)
    assert "raw_text" not in serialized
    assert "validated_text" not in serialized


def test_error_context_does_not_include_raw_text_substrings():
    context = build_invalid_output_error_context(
        payload={
            "candidates": [
                {
                    "title": "Lumière clignote à l'entrée du restaurant",
                    "structured_summary": "Plus de sirop mojito disponible au bar.",
                }
            ]
        },
        exc=ObservationPipelineInvalidOutputError("fail"),
    )
    serialized = json.dumps(context).lower()
    assert "lumière clignote" not in serialized
    assert "sirop mojito" not in serialized
