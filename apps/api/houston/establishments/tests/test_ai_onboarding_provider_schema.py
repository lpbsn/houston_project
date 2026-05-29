from __future__ import annotations

import pytest

from houston.establishments.ai_onboarding_provider_schema import (
    AI_ONBOARDING_PROVIDER_SCHEMA_NAME,
    openai_strict_response_format,
)
from houston.establishments.services import PROPOSAL_SCHEMA_VERSION


def test_openai_strict_response_format_shape():
    response_format = openai_strict_response_format()

    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == AI_ONBOARDING_PROVIDER_SCHEMA_NAME
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["properties"]["schema_version"]["const"] == PROPOSAL_SCHEMA_VERSION
    assert schema["additionalProperties"] is False


def test_valid_ai_payload_includes_modules_only_sections():
    from houston.establishments.tests.conftest import valid_ai_modules_payload

    payload = valid_ai_modules_payload()
    assert set(payload) == {"schema_version", "operational_modules"}
    assert payload["schema_version"] == PROPOSAL_SCHEMA_VERSION
