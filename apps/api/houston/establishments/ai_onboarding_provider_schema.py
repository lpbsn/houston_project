from __future__ import annotations

from houston.establishments.services import PROPOSAL_SCHEMA_VERSION

AI_ONBOARDING_PROVIDER_SCHEMA_NAME = "houston_ai_onboarding_proposal"

_OPENAI_STRICT_ONBOARDING_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema_version",
        "operational_modules",
    ],
    "properties": {
        "schema_version": {
            "type": "string",
            "const": PROPOSAL_SCHEMA_VERSION,
            "description": f"Must be {PROPOSAL_SCHEMA_VERSION}.",
        },
        "operational_modules": {
            "type": "array",
            "items": {"$ref": "#/$defs/catalog_item"},
        },
    },
    "$defs": {
        "nullable_confidence": {
            "type": ["number", "null"],
            "description": "Confidence between 0 and 1, or null.",
        },
        "catalog_item": {
            "type": "object",
            "additionalProperties": False,
            "required": ["key", "label", "reason", "confidence_score"],
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Catalog module key from active_module_catalog only.",
                },
                "label": {"type": "string"},
                "reason": {"type": "string"},
                "confidence_score": {"$ref": "#/$defs/nullable_confidence"},
            },
        },
    },
}


def openai_strict_response_format() -> dict:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": AI_ONBOARDING_PROVIDER_SCHEMA_NAME,
            "strict": True,
            "schema": _OPENAI_STRICT_ONBOARDING_SCHEMA,
        },
    }
