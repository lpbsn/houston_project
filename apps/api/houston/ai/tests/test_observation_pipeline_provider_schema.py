from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from houston.ai.observation_pipeline_provider_schema import (
    AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME,
    openai_strict_response_format,
)
from houston.signals.constants import (
    AI_INFORMATION_TYPE_MAX_LENGTH,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    MAX_CANDIDATES_PER_OBSERVATION,
)

BACKEND_ONLY_FIELDS = frozenset(
    {
        "routing_status",
        "resolution_audit",
        "rejection_code",
        "aggregate_into_signal_id",
        "ai_aggregate_hint_signal_id",
        "priority",
        "urgency",
        "detected_domains",
    }
)


def assert_no_ref_siblings(schema: Any) -> None:
    if isinstance(schema, dict):
        if "$ref" in schema:
            assert set(schema.keys()) == {"$ref"}
        for value in schema.values():
            assert_no_ref_siblings(value)
    elif isinstance(schema, list):
        for item in schema:
            assert_no_ref_siblings(item)


def iter_schema_objects(schema: Any) -> Iterator[dict[str, Any]]:
    if isinstance(schema, dict):
        if schema.get("type") == "object" or "properties" in schema:
            yield schema
        for value in schema.values():
            yield from iter_schema_objects(value)
    elif isinstance(schema, list):
        for item in schema:
            yield from iter_schema_objects(item)


@pytest.fixture
def openai_schema() -> dict[str, Any]:
    return openai_strict_response_format()["json_schema"]["schema"]


def test_openai_response_format_uses_json_schema_strict():
    response_format = openai_strict_response_format()

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME
    assert response_format["json_schema"]["strict"] is True

    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["schema_version", "candidates"]
    assert schema["properties"]["schema_version"]["const"] == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
    assert schema["properties"]["candidates"]["maxItems"] == MAX_CANDIDATES_PER_OBSERVATION

    candidate = schema["$defs"]["pipeline_candidate"]
    assert candidate["additionalProperties"] is False
    assert set(candidate["required"]) == set(candidate["properties"].keys())
    assert "aggregate_into_signal_id" not in candidate["properties"]
    assert "issue_focus" in candidate["required"]
    assert "canonical_object" in candidate["required"]
    assert "signal_kind" in candidate["required"]
    assert "expected_action" in candidate["required"]
    assert "information_type" in candidate["required"]
    for key in (
        "affected_business_unit_routing_key",
        "responsible_business_unit_routing_key",
        "activity_subject_routing_key",
        "operational_unit_key",
        "location_text",
        "expected_action",
        "information_type",
    ):
        assert "null" in candidate["properties"][key]["type"]


def test_openai_schema_has_no_ref_sibling_keywords(openai_schema):
    assert_no_ref_siblings(openai_schema)
    assert "nullable_string" not in openai_schema.get("$defs", {})


def test_openai_schema_required_fields_are_required(openai_schema):
    for obj in iter_schema_objects(openai_schema):
        properties = obj.get("properties")
        if not properties:
            continue
        required = obj.get("required")
        assert required is not None, f"Object missing required: {obj}"
        assert set(required) == set(properties.keys())


def test_openai_schema_objects_have_additional_properties_false(openai_schema):
    for obj in iter_schema_objects(openai_schema):
        assert obj.get("additionalProperties") is False, (
            f"Object missing additionalProperties: {obj}"
        )


def test_openai_schema_issue_focus_has_min_length(openai_schema):
    candidate = openai_schema["$defs"]["pipeline_candidate"]
    assert candidate["properties"]["issue_focus"]["minLength"] == 1


def test_openai_schema_excludes_backend_only_fields(openai_schema):
    candidate_props = set(openai_schema["$defs"]["pipeline_candidate"]["properties"])
    root_props = set(openai_schema["properties"])
    assert BACKEND_ONLY_FIELDS.isdisjoint(candidate_props)
    assert BACKEND_ONLY_FIELDS.isdisjoint(root_props)


def test_openai_schema_information_type_max_length(openai_schema):
    info = openai_schema["$defs"]["pipeline_candidate"]["properties"]["information_type"]
    assert info["maxLength"] == AI_INFORMATION_TYPE_MAX_LENGTH
