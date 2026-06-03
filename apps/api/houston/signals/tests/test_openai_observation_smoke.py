"""Live OpenAI observation pipeline smoke — opt-in only, not CI standard.

Requires HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1 and OPENAI_API_KEY.
Potentially costly, slow, and non-deterministic. Bypasses pytest fake settings
by injecting OpenAIObservationPipelineProvider explicitly.
"""

from __future__ import annotations

import os

import pytest
from django.conf import settings

from houston.ai.observation_pipeline import OpenAIObservationPipelineProvider
from houston.establishments.tests.test_permissions import build_membership
from houston.observations.models import ObservationProcessing
from houston.signals.models import Signal
from houston.signals.services import run_observation_pipeline
from houston.signals.tests.conftest import create_observation, create_taxonomy

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
            "observation pipeline smoke test."
        )
    if not settings.OPENAI_API_KEY:
        pytest.skip("OPENAI_API_KEY is not configured.")


def test_live_openai_observation_pipeline_smoke():
    _skip_if_smoke_not_enabled()

    membership = build_membership()
    create_taxonomy(membership.establishment)
    observation = create_observation(
        membership=membership,
        text="La climatisation du couloir nord ne refroidit plus depuis ce matin.",
    )

    run_observation_pipeline(
        observation.id,
        provider=OpenAIObservationPipelineProvider(),
    )

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED
    assert Signal.objects.filter(establishment=membership.establishment).exists()
