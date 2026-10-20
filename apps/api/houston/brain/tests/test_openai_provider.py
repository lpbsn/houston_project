"""OpenAI adapter prepared for brain_analysis_v1. The client is mocked; nothing is sent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from houston.brain.configuration import (
    CALL_FRAMING_TOKENS,
    call_input_tokens,
    canonical_json,
    json_token_count,
)
from houston.brain.contract import (
    SCHEMA_VERSION,
    BrainAnalysisV1,
    minimal_analysis,
    openai_strict_response_format,
)
from houston.brain.errors import BrainWorkError
from houston.brain.models import BrainDossier
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
    provider = OpenAIBrainProvider(
        api_key="",
        model="gpt-test",
        timeout_seconds=5,
        max_output_tokens=32,
    )
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
    provider = OpenAIBrainProvider(
        api_key="test-key",
        model="gpt-test",
        timeout_seconds=5,
        max_output_tokens=32,
    )
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
    assert kwargs["max_completion_tokens"] == 32
    content = kwargs["messages"][1]["content"]
    assert content == canonical_json(payload)
    assert json_token_count(payload) > 0
    assert call_input_tokens(payload) >= json_token_count(payload) + CALL_FRAMING_TOKENS
    blob = json.dumps(kwargs["messages"], ensure_ascii=False)
    assert "FIXTURE_ONLY" in blob
    assert "storage_key" not in blob
    assert result.truncated is False
    assert result.output["schema_version"] == SCHEMA_VERSION
    assert result.input_tokens == 4


def test_openai_bad_request_fails_the_v1_attempt_without_retry(monkeypatch, settings, caplog):
    import logging

    import httpx
    from openai import BadRequestError

    secret = "V1_DOSSIER_SECRET_NOT_FOR_LOGS"
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    client = MagicMock()
    client.chat.completions.create.side_effect = BadRequestError(
        secret,
        response=response,
        body={"error": {"message": secret}},
    )
    monkeypatch.setattr("openai.OpenAI", MagicMock(return_value=client))
    settings.HOUSTON_BRAIN_PROVIDER = "openai"
    settings.HOUSTON_BRAIN_MODEL = "gpt-5-mini"
    settings.OPENAI_API_KEY = "sk-lot4-secret"
    settings.HOUSTON_BRAIN_ENGINE_VERSION = ""
    _allow_publish(monkeypatch)
    analysis = _prepare(settings, ["Service lent en salle."])
    assert "engine_version" not in analysis.configuration
    with caplog.at_level(logging.INFO):
        run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()

    assert client.chat.completions.create.call_count == 1
    assert analysis.status == "failed"
    assert analysis.failure_code == "response_invalid"
    assert analysis.result is None
    assert analysis.transient_retries_used == 0
    assert analysis.provider_calls_used == 0
    assert secret not in caplog.text
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()
    assert client.chat.completions.create.call_count == 1
    assert analysis.status == "failed"
    assert analysis.result is None


def test_a_truncated_openai_response_is_not_a_result(monkeypatch):
    client = MagicMock()
    message = MagicMock(content="{", refusal=None)
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=message, finish_reason="length")],
        usage=MagicMock(prompt_tokens=1, completion_tokens=1),
    )
    monkeypatch.setattr("openai.OpenAI", MagicMock(return_value=client))
    provider = OpenAIBrainProvider(
        api_key="test-key",
        model="gpt-test",
        timeout_seconds=5,
        max_output_tokens=32,
    )
    result = provider.complete(
        analysis_id="analysis",
        lot_key="lot-0001",
        payload={"required_piece_ids": ["s0000"]},
        timeout_seconds=5,
    )
    assert result.truncated is True
    assert result.output == {}


@pytest.mark.parametrize(
    ("provider_name", "api_key", "model"),
    [
        pytest.param("openai", "", "gpt-frozen", id="openai-without-key"),
        pytest.param("openai", "   ", "gpt-frozen", id="openai-blank-key"),
        pytest.param("openai", "sk-lot4-secret", "", id="openai-without-model"),
        pytest.param(None, "sk-lot4-secret", "gpt-frozen", id="absent-provider"),
        pytest.param("", "sk-lot4-secret", "gpt-frozen", id="blank-provider"),
        pytest.param("anthropic", "sk-lot4-secret", "gpt-frozen", id="unknown-provider"),
    ],
)
def test_refused_provider_does_not_open_a_client_or_capture(
    monkeypatch,
    settings,
    provider_name,
    api_key,
    model,
):
    constructed = MagicMock(side_effect=AssertionError("client"))
    monkeypatch.setattr("openai.OpenAI", constructed)
    _allow_publish(monkeypatch)
    settings.OPENAI_API_KEY = api_key
    settings.HOUSTON_BRAIN_MODEL = "gpt-live-not-frozen"
    analysis = _prepare(settings, ["Pas de document."])
    configuration = dict(analysis.configuration)
    configuration["api_key"] = "sk-from-configuration"
    if provider_name is None:
        configuration.pop("provider", None)
    else:
        configuration["provider"] = provider_name
    configuration["model"] = model
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()
    assert analysis.status == "failed"
    assert analysis.failure_code == "provider_not_allowed"
    assert analysis.reserved_input_tokens == 0
    assert analysis.consumed_input_tokens == 0
    assert analysis.provider_calls_used == 0
    assert analysis.transient_retries_used == 0
    assert not BrainDossier.objects.filter(analysis=analysis).exists()
    assert "sk-lot4-secret" not in json.dumps(analysis.configuration)
    constructed.assert_not_called()


def test_frozen_openai_uses_the_frozen_model_without_storing_the_key(monkeypatch, settings):
    settings.HOUSTON_BRAIN_PROVIDER = "openai"
    settings.HOUSTON_BRAIN_MODEL = "gpt-5-mini"
    settings.OPENAI_API_KEY = "sk-lot4-secret"
    _allow_publish(monkeypatch)
    analysis = _prepare(settings, ["Service lent en salle."])
    assert analysis.configuration["provider"] == "openai"
    assert analysis.configuration["model"] == "gpt-5-mini"
    assert "sk-lot4-secret" not in json.dumps(analysis.configuration)
    settings.HOUSTON_BRAIN_PROVIDER = "fake"
    settings.HOUSTON_BRAIN_MODEL = "gpt-live"
    client = MagicMock()
    message = MagicMock(content=json.dumps(minimal_analysis(["s0000"])), refusal=None)
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=message, finish_reason="stop")],
        usage=MagicMock(prompt_tokens=4, completion_tokens=3),
    )
    constructed = MagicMock(return_value=client)
    monkeypatch.setattr("openai.OpenAI", constructed)
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()
    assert analysis.status == "completed"
    assert analysis.failure_code == ""
    assert analysis.reserved_input_tokens > 0
    assert analysis.provider_calls_used == 1
    assert constructed.call_args.kwargs["api_key"] == "sk-lot4-secret"
    assert constructed.call_args.kwargs["max_retries"] == 0
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-5-mini"
    assert kwargs["response_format"] == openai_strict_response_format()
    assert (
        kwargs["max_completion_tokens"]
        == analysis.configuration["ceilings"]["per_call_output_tokens"]
    )
    content = kwargs["messages"][1]["content"]
    assert content == canonical_json(json.loads(content))
    blob = json.dumps(kwargs["messages"], ensure_ascii=False)
    assert "sk-lot4-secret" not in blob
    assert "sk-lot4-secret" not in json.dumps(analysis.configuration)
    assert "Service lent en salle." in blob


def test_frozen_fake_does_not_construct_openai(monkeypatch, settings):
    settings.HOUSTON_BRAIN_PROVIDER = "fake"
    settings.HOUSTON_BRAIN_MODEL = "fake"
    settings.OPENAI_API_KEY = ""
    _allow_publish(monkeypatch)
    monkeypatch.setenv("HOUSTON_BRAIN_FAKE_MODE", "ok")
    monkeypatch.delenv("HOUSTON_BRAIN_FAKE_HOLD_SECONDS", raising=False)
    analysis = _prepare(settings, ["Lecture locale."])
    assert analysis.configuration["provider"] == "fake"
    settings.HOUSTON_BRAIN_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "sk-lot4-secret"
    settings.HOUSTON_BRAIN_MODEL = "gpt-live"
    constructed = MagicMock(side_effect=AssertionError("client"))
    monkeypatch.setattr("openai.OpenAI", constructed)
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()
    assert analysis.status == "completed"
    assert analysis.failure_code == ""
    assert analysis.configuration["provider"] == "fake"
    assert "sk-lot4-secret" not in json.dumps(analysis.configuration)
    constructed.assert_not_called()


def pytest_settings():
    from django.conf import settings

    return settings
