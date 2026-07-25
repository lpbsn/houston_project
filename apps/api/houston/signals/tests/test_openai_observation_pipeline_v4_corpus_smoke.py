"""Live OpenAI observation pipeline v4 corpus smoke — opt-in only, not CI standard.

Requires HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1 and OPENAI_API_KEY.
Runs 6 golden corpus cases (G01, G03–G07) through the real provider and checks
structural alignment with expected routing keys and issue_focus presence.
"""

from __future__ import annotations

import os

import pytest
from django.conf import settings

from houston.ai.observation_pipeline import (
    OpenAIObservationPipelineProvider,
    build_pipeline_input,
    call_observation_pipeline,
)
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership
from houston.testing.pipeline_golden_v4 import (
    get_pipeline_golden_v4_case,
    remap_expected_candidates_to_routing_keys,
    setup_active_signals_from_fixture,
    setup_taxonomy_from_fixture,
)

CORPUS_SMOKE_CASE_IDS = ("G01", "G03", "G04", "G05", "G06", "G07")

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.openai_observation_smoke,
]


def _openai_smoke_enabled() -> bool:
    return os.environ.get("HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST") == "1"


def _skip_if_smoke_not_enabled() -> None:
    if not _openai_smoke_enabled():
        pytest.skip(
            "Set HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1 to run the live OpenAI "
            "observation pipeline v4 corpus smoke tests."
        )
    if not settings.OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY is not configured.")


def _routing_tuple(candidate) -> tuple[str, str, str]:
    if hasattr(candidate, "affected_business_unit_routing_key"):
        return (
            candidate.affected_business_unit_routing_key,
            candidate.responsible_business_unit_routing_key,
            candidate.activity_subject_routing_key,
        )
    return (
        candidate["affected_business_unit_routing_key"],
        candidate["responsible_business_unit_routing_key"],
        candidate["activity_subject_routing_key"],
    )


def _assert_live_output_matches_corpus(
    *,
    output,
    case: dict,
    expected_candidates: list[dict],
) -> None:
    assert output.schema_version == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
    assert len(output.candidates) == len(expected_candidates), (
        f"{case['id']}: expected {len(expected_candidates)} candidates, "
        f"got {len(output.candidates)}"
    )

    expected_routing = {_routing_tuple(raw) for raw in expected_candidates}
    actual_routing = {_routing_tuple(candidate) for candidate in output.candidates}
    assert actual_routing == expected_routing, (
        f"{case['id']}: routing mismatch expected={expected_routing} actual={actual_routing}"
    )

    for candidate in output.candidates:
        assert candidate.issue_focus.strip(), f"{case['id']}: empty issue_focus"
        assert len(candidate.issue_focus) <= 80


@pytest.mark.parametrize("case_id", CORPUS_SMOKE_CASE_IDS)
def test_live_openai_v4_corpus_case(case_id: str):
    _skip_if_smoke_not_enabled()

    case = get_pipeline_golden_v4_case(case_id)
    membership = build_membership()
    establishment = membership.establishment
    business_units, activity_subjects = setup_taxonomy_from_fixture(
        establishment=establishment,
        fixture=case["taxonomy_fixture"],
    )
    setup_active_signals_from_fixture(
        establishment=establishment,
        setup=case.get("active_signals_setup", []),
        business_units=business_units,
        activity_subjects=activity_subjects,
    )
    expected_candidates = remap_expected_candidates_to_routing_keys(
        expected_candidates=case["expected_candidates"],
        business_units=business_units,
        activity_subjects=activity_subjects,
    )
    observation = create_observation(
        membership=membership,
        text=case["observation_text"],
    )

    input_payload = build_pipeline_input(observation=observation)
    assert "routing_taxonomy" in input_payload
    assert "active_signals_context" not in input_payload

    output = call_observation_pipeline(
        observation=observation,
        provider=OpenAIObservationPipelineProvider(),
    )
    _assert_live_output_matches_corpus(
        output=output,
        case=case,
        expected_candidates=expected_candidates,
    )
