"""Live OpenAI Lot4b prompt v6.1 smoke — opt-in, not CI.

Validates understanding rules for informational facts, anti-over-segmentation,
and legitimate empty candidates. Distinct from the V6 technical contract smoke
and from Lot 10 full business smoke.

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
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
)
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership

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
            "observation pipeline v6.1 prompt smoke test."
        )
    if not settings.OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY is not configured.")


def _setup_hotel_org_plumbing_taxonomy(establishment):
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Organisation",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Plomberie",
    )
    return hotel


def _propose(text: str):
    membership = build_membership()
    _setup_hotel_org_plumbing_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text=text)
    input_payload = build_pipeline_input(observation=observation)
    assert input_payload["prompt_version"] == AI_OBSERVATION_PIPELINE_PROMPT_VERSION
    assert input_payload["schema_version"] == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
    provider = OpenAIObservationPipelineProvider()
    response = provider.propose(input_payload=input_payload)
    return parse_pipeline_output(response.payload)


def test_live_openai_v6_1_planning_announcement_exactly_one_informational():
    _skip_if_smoke_not_enabled()
    output = _propose("Les plannings sont disponibles, venez les demander")
    assert len(output.candidates) == 1
    assert output.candidates[0].signal_kind == "informational"


def test_live_openai_v6_1_schedule_or_policy_one_informational():
    _skip_if_smoke_not_enabled()
    output = _propose("Nouveau brief service à 17h au lieu de 16h")
    assert len(output.candidates) == 1
    assert output.candidates[0].signal_kind == "informational"


def test_live_openai_v6_1_mixed_actionable_and_informational():
    _skip_if_smoke_not_enabled()
    output = _propose("Fuite couloir nord et planning étages disponible")
    kinds = {c.signal_kind for c in output.candidates}
    assert "actionable" in kinds
    assert "informational" in kinds
    assert len(output.candidates) == 2


def test_live_openai_v6_1_politeness_empty_candidates():
    _skip_if_smoke_not_enabled()
    output = _propose("Bon courage à tous")
    assert output.candidates == []


def test_live_openai_v6_1_false_alert_empty_candidates():
    _skip_if_smoke_not_enabled()
    output = _propose("Fausse alerte, pas de fuite")
    assert output.candidates == []
