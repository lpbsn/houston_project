from __future__ import annotations

import copy
import os
import uuid

import pytest
import rest_framework.throttling as drf_throttling
from django.conf import settings
from django.core.cache import caches
from django.test import override_settings
from rest_framework.settings import api_settings as drf_api_settings

_RELAXED_AUTH_THROTTLE_RATE = "1000/minute"

_RELAXED_AUTH_THROTTLE_RATES = {
    settings.AUTH_THROTTLE_SCOPE_LOGIN: _RELAXED_AUTH_THROTTLE_RATE,
    settings.AUTH_THROTTLE_SCOPE_REFRESH: _RELAXED_AUTH_THROTTLE_RATE,
    settings.AUTH_THROTTLE_SCOPE_REGISTER: _RELAXED_AUTH_THROTTLE_RATE,
    settings.AUTH_THROTTLE_SCOPE_REGISTER_VALIDATE: _RELAXED_AUTH_THROTTLE_RATE,
    settings.AUTH_THROTTLE_SCOPE_INVITATION_ACCEPT: _RELAXED_AUTH_THROTTLE_RATE,
    settings.CHAT_THROTTLE_SCOPE_WS_TICKET: _RELAXED_AUTH_THROTTLE_RATE,
}


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


@pytest.fixture(autouse=True)
def relaxed_auth_throttling_for_standard_tests(request, monkeypatch):
    """Relax auth throttle quotas for standard tests; skip @pytest.mark.auth_throttle tests."""
    if request.node.get_closest_marker("auth_throttle"):
        yield
        return

    cache_location = f"auth-throttle-relaxed-{uuid.uuid4()}"
    relaxed_rates = dict(_RELAXED_AUTH_THROTTLE_RATES)

    monkeypatch.setattr(
        drf_throttling.SimpleRateThrottle,
        "THROTTLE_RATES",
        relaxed_rates,
    )
    rest_framework = copy.deepcopy(settings.REST_FRAMEWORK)
    rest_framework["DEFAULT_THROTTLE_RATES"] = relaxed_rates

    throttle_caches = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": cache_location,
        }
    }
    with override_settings(CACHES=throttle_caches, REST_FRAMEWORK=rest_framework):
        drf_api_settings.reload()
        caches["default"].clear()
        try:
            yield
        finally:
            caches["default"].clear()
            drf_api_settings.reload()


@pytest.fixture(autouse=True)
def reset_channel_layers_between_tests():
    from channels.layers import channel_layers

    channel_layers.backends.clear()
    yield
    channel_layers.backends.clear()
