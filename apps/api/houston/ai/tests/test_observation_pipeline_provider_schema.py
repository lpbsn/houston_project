from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from houston.ai.observation_pipeline_provider_schema import (
    AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME,
    openai_strict_response_format,
)
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION


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

    candidate = schema["$defs"]["pipeline_candidate"]
    assert candidate["additionalProperties"] is False
    assert "affected_business_unit_key" in candidate["required"]
    assert "responsible_business_unit_key" in candidate["required"]
    assert "activity_subject_key" in candidate["required"]
    assert "issue_focus" in candidate["required"]
    assert "operational_unit_key" in candidate["required"]
    assert "location_text" in candidate["required"]
    assert "aggregate_into_signal_id" in candidate["required"]


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
