"""OpenAI adapter prepared for brain_analysis_v1. The client is mocked; nothing is sent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from houston.brain.contract import (
    SCHEMA_VERSION,
    BrainAnalysisV1,
    minimal_analysis,
    openai_strict_response_format,
)
from houston.brain.errors import BrainWorkError
from houston.brain.openai_provider import OpenAIBrainProvider
from houston.brain.runtime import run_brain_analysis
from houston.brain.tests.test_runtime import _allow_publish, _prepare

pytestmark = pytest.mark.django_db(transaction=True)


def test_openai_schema_is_strict_and_matches_the_model():
    response_format = openai_strict_response_format()
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["name"] == SCHEMA_VERSION
    schema = response_format["json_schema"]["schema"]
    assert set(schema["properties"]) == set(BrainAnalysisV1.model_fields)

    def walk(node) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)


def test_missing_api_key_does_not_build_a_client(monkeypatch):
    constructed = MagicMock(side_effect=AssertionError("client"))
    monkeypatch.setattr("openai.OpenAI", constructed)
    provider = OpenAIBrainProvider(api_key="", model="gpt-test", timeout_seconds=5)
    with pytest.raises(BrainWorkError) as raised:
        provider.complete(
            analysis_id="analysis",
            lot_key="lot-0001",
            payload={"sections": [{"text": "FIXTURE_ONLY", "piece_id": "s0000"}]},
            timeout_seconds=5,
        )
    assert raised.value.code == "provider_not_allowed"
    constructed.assert_not_called()


def test_mocked_openai_sends_the_fixture_payload_and_not_a_stored_file(monkeypatch):
    client = MagicMock()
    message = MagicMock(content=json.dumps(minimal_analysis(["s0000"])), refusal=None)
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=message, finish_reason="stop")],
        usage=MagicMock(prompt_tokens=4, completion_tokens=3),
    )
    constructed = MagicMock(return_value=client)
    monkeypatch.setattr("openai.OpenAI", constructed)
    payload = {
        "sections": [{"text": "FIXTURE_ONLY", "piece_id": "s0000"}],
        "required_piece_ids": ["s0000"],
    }
    provider = OpenAIBrainProvider(api_key="test-key", model="gpt-test", timeout_seconds=5)
    result = provider.complete(
        analysis_id="analysis",
        lot_key="lot-0001",
        payload=payload,
        timeout_seconds=5,
    )
    assert constructed.call_args.kwargs["max_retries"] == 0
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == openai_strict_response_format()
    assert kwargs["model"] == "gpt-test"
    blob = json.dumps(kwargs["messages"], ensure_ascii=False)
    assert "FIXTURE_ONLY" in blob
    assert "storage_key" not in blob
    assert result.truncated is False
    assert result.output["schema_version"] == SCHEMA_VERSION
    assert result.input_tokens == 4


def test_a_truncated_openai_response_is_not_a_result(monkeypatch):
    client = MagicMock()
    message = MagicMock(content="{", refusal=None)
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=message, finish_reason="length")],
        usage=MagicMock(prompt_tokens=1, completion_tokens=1),
    )
    monkeypatch.setattr("openai.OpenAI", MagicMock(return_value=client))
    provider = OpenAIBrainProvider(api_key="test-key", model="gpt-test", timeout_seconds=5)
    result = provider.complete(
        analysis_id="analysis",
        lot_key="lot-0001",
        payload={"required_piece_ids": ["s0000"]},
        timeout_seconds=5,
    )
    assert result.truncated is True
    assert result.output == {}


def test_runtime_does_not_call_openai_for_a_configured_provider(monkeypatch):
    constructed = MagicMock()
    monkeypatch.setattr("openai.OpenAI", constructed)
    _allow_publish(monkeypatch)
    analysis = _prepare(pytest_settings(), ["Pas de document."])
    configuration = dict(analysis.configuration)
    configuration["provider"] = "openai"
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()
    assert analysis.status == "failed"
    assert analysis.failure_code == "provider_not_allowed"
    constructed.assert_not_called()


def pytest_settings():
    from django.conf import settings

    return settings
