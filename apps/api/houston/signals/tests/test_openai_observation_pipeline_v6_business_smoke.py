"""Live OpenAI observation pipeline V6 *business* smoke — Lot 10, opt-in, not CI.

Validates prompt v6_2 quality signals: dual context present, no author scope in LLM
input, schema/prompt versions, segmentation 0/1/N capability, informational fields,
nullable routing keys, latency/tokens. Archives results under
.artifacts/pipeline-v6-smoke/.

Distinct from Lot 4 technical contract smoke.
Requires HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1 and OPENAI_API_KEY.
"""

from __future__ import annotations

import os
import time

import pytest
from django.conf import settings

from houston.ai.observation_pipeline import (
    OpenAIObservationPipelineProvider,
    build_pipeline_input,
    parse_pipeline_output,
)
from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
)
from houston.signals.pipeline_v6_smoke_archive import write_smoke_archive
from houston.signals.tests.conftest import create_observation, create_restaurant_v3_taxonomy
from houston.testing.factories import build_membership

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.openai_observation_smoke,
]

AUTHOR_SCOPE_FORBIDDEN_KEYS = frozenset(
    {
        "author_scope_business_unit_routing_keys",
        "author_scope",
        "author_membership_scopes",
    }
)


def _openai_smoke_enabled() -> bool:
    return os.environ.get("HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST") == "1"


def _skip_if_smoke_not_enabled() -> None:
    if not _openai_smoke_enabled():
        pytest.skip(
            "Set HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1 to run the live OpenAI "
            "observation pipeline V6 business smoke test."
        )
    if not settings.OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY is not configured.")


def test_live_openai_v6_business_smoke_prompt_context_and_archive():
    _skip_if_smoke_not_enabled()

    assert AI_OBSERVATION_PIPELINE_PROMPT_VERSION == "ai_observation_pipeline_v6_2"
    assert AI_OBSERVATION_PIPELINE_SCHEMA_VERSION == "ai_observation_pipeline_v6"

    membership = build_membership()
    create_restaurant_v3_taxonomy(membership.establishment)

    scenarios = [
        {
            "id": "segmentation_two_facts",
            "text": "Frigo chaud et sol trempé dans le restaurant.",
        },
        {
            "id": "informational_schedule",
            "text": "Les plannings sont disponibles, venez les demander.",
        },
        {
            "id": "empty_or_noise",
            "text": "Bon courage à tous pour le service.",
        },
    ]

    provider = OpenAIObservationPipelineProvider()
    scenario_results: list[dict] = []
    errors: list[str] = []

    for scenario in scenarios:
        observation = create_observation(membership=membership, text=scenario["text"])
        input_payload = build_pipeline_input(observation=observation)

        assert "establishment_context" in input_payload
        assert "active_business_units" in input_payload["establishment_context"]
        assert "routing_taxonomy" in input_payload
        assert AUTHOR_SCOPE_FORBIDDEN_KEYS.isdisjoint(input_payload.keys())
        assert "submission_context" not in input_payload

        started = time.monotonic()
        try:
            response = provider.propose(input_payload=input_payload)
            output = parse_pipeline_output(response.payload)
            latency_ms = int((time.monotonic() - started) * 1000)
            scenario_results.append(
                {
                    "id": scenario["id"],
                    "passed": True,
                    "candidate_count": len(output.candidates),
                    "schema_version": output.schema_version,
                    "latency_ms": latency_ms,
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "total_tokens": response.total_tokens,
                    "signal_kinds": [c.signal_kind for c in output.candidates],
                    "null_routing_keys_present": any(
                        c.affected_business_unit_routing_key is None
                        or c.responsible_business_unit_routing_key is None
                        or c.activity_subject_routing_key is None
                        for c in output.candidates
                    ),
                }
            )
            assert output.schema_version == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
            assert len(output.candidates) <= 5
            for candidate in output.candidates:
                assert candidate.issue_focus
                assert candidate.canonical_object
                assert candidate.signal_kind in {"actionable", "informational"}
                if candidate.signal_kind == "informational":
                    assert candidate.information_type
                else:
                    assert candidate.information_type is None
        except Exception as exc:  # noqa: BLE001 — archive failures
            errors.append(f"{scenario['id']}: {exc}")
            scenario_results.append(
                {
                    "id": scenario["id"],
                    "passed": False,
                    "error": str(exc),
                }
            )

    passed = not errors and all(item.get("passed") for item in scenario_results)
    archive_path = write_smoke_archive(
        kind="lot10-business",
        payload={
            "passed": passed,
            "prompt_version": AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
            "scenarios": scenario_results,
            "errors": errors,
            "summary": (
                "Lot 10 business smoke: dual context, no author scope, "
                f"prompt {AI_OBSERVATION_PIPELINE_PROMPT_VERSION}, "
                f"{len(scenario_results)} scenarios."
            ),
        },
    )
    assert archive_path.exists()
    assert passed, f"Business smoke failed: {errors}; archive={archive_path}"
