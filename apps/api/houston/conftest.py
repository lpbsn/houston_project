from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def force_fake_observation_pipeline_provider(settings):
    """Runtime default is openai; pytest/CI must use fake only (no live OpenAI)."""
    settings.HOUSTON_AI_OBSERVATION_PROVIDER = "fake"


@pytest.fixture(autouse=True)
def forbid_live_openai_observation_propose(request, monkeypatch):
    """Fail standard tests if OpenAI propose is invoked accidentally."""
    if request.node.get_closest_marker("openai_observation_smoke"):
        return
    if request.node.get_closest_marker("allow_openai_observation_propose"):
        return
    if os.environ.get("HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST") == "1":
        return

    def _forbidden(*args, **kwargs):
        pytest.fail(
            "OpenAIObservationPipelineProvider.propose was called during standard tests. "
            "Use FakeObservationPipelineProvider or mock propose."
        )

    monkeypatch.setattr(
        "houston.ai.observation_pipeline.OpenAIObservationPipelineProvider.propose",
        _forbidden,
    )
