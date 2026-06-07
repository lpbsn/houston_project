from __future__ import annotations

from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    MAX_CANDIDATES_PER_OBSERVATION,
)

AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME = "houston_observation_pipeline_output"

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
                "affected_business_unit_key",
                "responsible_business_unit_key",
                "activity_subject_key",
                "operational_unit_key",
                "location_text",
                "aggregate_into_signal_id",
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
                "affected_business_unit_key": {
                    "type": "string",
                    "description": (
                        "Business unit key where the issue is observed "
                        "(from establishment_taxonomy)."
                    ),
                },
                "responsible_business_unit_key": {
                    "type": "string",
                    "description": (
                        "Business unit responsible for treatment "
                        "(transversal when different from affected)."
                    ),
                },
                "activity_subject_key": {
                    "type": "string",
                    "description": (
                        "Activity subject normalized_name under responsible_business_unit."
                    ),
                },
                "operational_unit_key": {
                    "type": ["string", "null"],
                    "description": (
                        "Operational unit key when a known unit applies; otherwise null."
                    ),
                },
                "location_text": {
                    "type": ["string", "null"],
                    "description": (
                        "Short free-text location for display when no structured unit applies "
                        "(e.g. entrance, bar, room 104); never the full observation text."
                    ),
                },
                "aggregate_into_signal_id": {
                    "type": ["string", "null"],
                    "description": ("Optional UUID hint for aggregation only; otherwise null."),
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
