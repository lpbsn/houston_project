from __future__ import annotations

from houston.signals.constants import (
    AI_CANONICAL_OBJECT_MAX_LENGTH,
    AI_EXPECTED_ACTION_VALUES,
    AI_INFORMATION_TYPE_MAX_LENGTH,
    AI_ISSUE_FOCUS_MAX_LENGTH,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    AI_SIGNAL_KIND_VALUES,
    MAX_CANDIDATES_PER_OBSERVATION,
)

AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME = "houston_observation_pipeline_output"

_NULLABLE_STRING = {"type": ["string", "null"]}
_NULLABLE_ROUTING_KEY = {"type": ["string", "null"], "maxLength": 180}
_NULLABLE_SUBJECT_KEY = {"type": ["string", "null"], "maxLength": 150}

_OPENAI_STRICT_OBSERVATION_PIPELINE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "candidates"],
    "properties": {
        "schema_version": {
            "type": "string",
            "const": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "description": f"Must be {AI_OBSERVATION_PIPELINE_SCHEMA_VERSION}.",
        },
        "candidates": {
            "type": "array",
            "maxItems": MAX_CANDIDATES_PER_OBSERVATION,
            "items": {"$ref": "#/$defs/pipeline_candidate"},
            "description": (
                "Zero to five distinct operational problems extracted from the observation."
            ),
        },
    },
    "$defs": {
        "pipeline_candidate": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "title",
                "structured_summary",
                "issue_focus",
                "canonical_object",
                "signal_kind",
                "expected_action",
                "information_type",
                "affected_business_unit_routing_key",
                "responsible_business_unit_routing_key",
                "activity_subject_routing_key",
                "operational_unit_key",
                "location_text",
            ],
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short operational title.",
                },
                "structured_summary": {
                    "type": "string",
                    "description": "Structured summary without raw observation text.",
                },
                "issue_focus": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": AI_ISSUE_FOCUS_MAX_LENGTH,
                    "description": (
                        "Stable operational problem focus for aggregation "
                        "(include discriminant location when needed)."
                    ),
                },
                "canonical_object": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": AI_CANONICAL_OBJECT_MAX_LENGTH,
                    "description": "Canonical object/product/equipment identifier.",
                },
                "signal_kind": {
                    "type": "string",
                    "enum": list(AI_SIGNAL_KIND_VALUES),
                    "description": "actionable or informational.",
                },
                "expected_action": {
                    "type": ["string", "null"],
                    "enum": [*AI_EXPECTED_ACTION_VALUES, None],
                    "description": "Expected operational action, or null when unknown.",
                },
                "information_type": {
                    "type": ["string", "null"],
                    "maxLength": AI_INFORMATION_TYPE_MAX_LENGTH,
                    "description": (
                        "Null when signal_kind=actionable; non-empty free string when "
                        "signal_kind=informational (no closed enum)."
                    ),
                },
                "affected_business_unit_routing_key": {
                    **_NULLABLE_ROUTING_KEY,
                    "description": (
                        "Business unit routing_key where the issue is observed "
                        "(from routing_taxonomy only); null if unknown."
                    ),
                },
                "responsible_business_unit_routing_key": {
                    **_NULLABLE_ROUTING_KEY,
                    "description": (
                        "Business unit routing_key responsible for treatment "
                        "(from routing_taxonomy only); null if unknown."
                    ),
                },
                "activity_subject_routing_key": {
                    **_NULLABLE_SUBJECT_KEY,
                    "description": (
                        "Activity subject routing_key under responsible "
                        "(from routing_taxonomy only); null if unknown."
                    ),
                },
                "operational_unit_key": {
                    **_NULLABLE_STRING,
                    "description": (
                        "Operational unit key when a known unit applies; otherwise null."
                    ),
                },
                "location_text": {
                    "type": ["string", "null"],
                    "description": (
                        "Short free-text location for display when no structured unit applies; "
                        "never the full observation text."
                    ),
                },
            },
        },
    },
}


def openai_strict_response_format() -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME,
            "strict": True,
            "schema": _OPENAI_STRICT_OBSERVATION_PIPELINE_SCHEMA,
        },
    }
