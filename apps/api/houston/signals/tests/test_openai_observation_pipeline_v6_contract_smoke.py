"""Live OpenAI observation pipeline V6 *technical* contract smoke — opt-in, not CI.

Validates that the provider accepts the strict nullable V6 JSON schema and that
the returned payload parses as ObservationPipelineOutput.

Does NOT require the live response to contain null routing keys (covered by CI
fake/unit parse tests). Distinct from Lot 10 business smoke.

Requires HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1 and OPENAI_API_KEY.
"""

from __future__ import annotations

import os

import pytest
from django.conf import settings

from houston.ai.observation_pipeline import (
    OpenAIObservationPipelineProvider,
    build_pipeline_input,
    parse_pipeline_output,
)
from houston.ai.observation_pipeline_provider_schema import openai_strict_response_format
from houston.ai.observation_pipeline_schema import ObservationPipelineOutput
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.tests.conftest import create_observation, create_restaurant_v3_taxonomy
from houston.testing.factories import build_membership

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.openai_observation_smoke,
]

BACKEND_ONLY_FIELDS = frozenset(
    {
        "routing_status",
        "resolution_audit",
        "rejection_code",
        "aggregate_into_signal_id",
        "ai_aggregate_hint_signal_id",
    }
)


def _openai_smoke_enabled() -> bool:
    return os.environ.get("HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST") == "1"


def _skip_if_smoke_not_enabled() -> None:
    if not _openai_smoke_enabled():
        pytest.skip(
            "Set HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1 to run the live OpenAI "
            "observation pipeline V6 technical contract smoke test."
        )
    if not settings.OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY is not configured.")


def test_live_openai_accepts_v6_strict_nullable_schema_and_parses():
    _skip_if_smoke_not_enabled()

    schema = openai_strict_response_format()["json_schema"]["schema"]
    candidate = schema["$defs"]["pipeline_candidate"]
    assert schema["additionalProperties"] is False
    assert candidate["additionalProperties"] is False
    assert set(candidate["required"]) == set(candidate["properties"].keys())
    assert candidate["properties"]["affected_business_unit_routing_key"]["type"] == [
        "string",
        "null",
    ]
    assert "aggregate_into_signal_id" not in candidate["properties"]

    membership = build_membership()
    create_restaurant_v3_taxonomy(membership.establishment)
    observation = create_observation(
        membership=membership,
        text="La climatisation du couloir nord ne refroidit plus depuis ce matin.",
    )
    input_payload = build_pipeline_input(observation=observation)
    assert input_payload["schema_version"] == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION

    provider = OpenAIObservationPipelineProvider()
    response = provider.propose(input_payload=input_payload)
    output = parse_pipeline_output(response.payload)

    assert isinstance(output, ObservationPipelineOutput)
    assert output.schema_version == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
    assert len(output.candidates) <= 5

    for candidate_out in output.candidates:
        payload = candidate_out.model_dump()
        assert BACKEND_ONLY_FIELDS.isdisjoint(payload.keys())
        assert candidate_out.issue_focus
        assert candidate_out.canonical_object
        assert candidate_out.signal_kind in {"actionable", "informational"}
        assert "affected_business_unit_routing_key" in payload
        assert "responsible_business_unit_routing_key" in payload
        assert "activity_subject_routing_key" in payload
        assert "information_type" in payload
        # Null routing keys are allowed by schema but not required in a live response.
