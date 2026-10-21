"""OpenAI tool-calling adapter. The client is mocked; nothing is sent."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from houston.brain.engine import metier_prompt
from houston.brain.errors import BrainWorkError
from houston.brain.models import BrainDossier
from houston.brain.openai_provider import OpenAIBrainProvider
from houston.brain.runtime import run_brain_analysis
from houston.brain.tests.test_support import allow_publish, prepare

pytestmark = pytest.mark.django_db(transaction=True)


def _provider():
    return OpenAIBrainProvider(
        api_key="test-key",
        model="gpt-test",
        timeout_seconds=5,
        max_output_tokens=32,
    )


def _response(*, content="{}", finish_reason="stop", tool_calls=None, refusal=None):
    message = MagicMock(content=content, refusal=refusal, tool_calls=tool_calls)
    return MagicMock(
        choices=[MagicMock(message=message, finish_reason=finish_reason)],
        usage=MagicMock(prompt_tokens=4, completion_tokens=3),
    )


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
            messages=[{"role": "user", "content": {"text": "FIXTURE_ONLY"}}],
            tools=[],
            timeout_seconds=5,
        )
    assert raised.value.code == "provider_not_allowed"
    constructed.assert_not_called()


def test_mocked_openai_sends_the_prompt_and_the_tools(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.return_value = _response(content='{"subjects": []}')
    monkeypatch.setattr("openai.OpenAI", MagicMock(return_value=client))
    tools = [
        {
            "name": "search_signals",
            "description": "Signaux scellés.",
            "parameters": {"text": "Texte facultatif."},
        }
    ]
    turn = _provider().complete(
        analysis_id="analysis",
        messages=[
            {"role": "system", "content": metier_prompt()},
            {"role": "user", "content": {"anchor": "FIXTURE_ONLY"}},
        ],
        tools=tools,
        timeout_seconds=5,
    )
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "gpt-test"
    assert kwargs["max_completion_tokens"] == 32
    assert "response_format" not in kwargs
    names = [tool["function"]["name"] for tool in kwargs["tools"]]
    assert names == ["search_signals"]
    assert kwargs["tools"][0]["function"]["parameters"]["additionalProperties"] is False
    assert kwargs["messages"][0]["content"] == metier_prompt()
    blob = json.dumps(kwargs["messages"], ensure_ascii=False)
    assert "FIXTURE_ONLY" in blob
    assert "storage_key" not in blob
    assert turn.restitution == {"subjects": []}
    assert turn.input_tokens == 4


def test_a_truncated_finish_is_not_a_restitution(monkeypatch):
    client = MagicMock()
    client.chat.completions.create.return_value = _response(content="{", finish_reason="length")
    monkeypatch.setattr("openai.OpenAI", MagicMock(return_value=client))
    with pytest.raises(BrainWorkError) as raised:
        _provider().complete(
            analysis_id="analysis",
            messages=[{"role": "user", "content": "FIXTURE_ONLY"}],
            tools=[],
            timeout_seconds=5,
        )
    assert raised.value.code == "response_invalid"


def test_openai_bad_request_fails_the_attempt_without_retry(monkeypatch, settings, caplog):
    import logging

    import httpx
    from openai import BadRequestError

    secret = "DOSSIER_SECRET_NOT_FOR_LOGS"
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
    settings.OPENAI_API_KEY = "sk-test-secret"
    allow_publish(monkeypatch)
    analysis = prepare(settings, ["Service lent en salle."])
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


@pytest.mark.parametrize(
    ("provider_name", "api_key", "model"),
    [
        pytest.param("openai", "", "gpt-frozen", id="openai-without-key"),
        pytest.param("openai", "   ", "gpt-frozen", id="openai-blank-key"),
        pytest.param("openai", "sk-test-secret", "", id="openai-without-model"),
        pytest.param("anthropic", "sk-test-secret", "gpt-frozen", id="unknown-provider"),
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
    allow_publish(monkeypatch)
    settings.OPENAI_API_KEY = api_key
    analysis = prepare(settings, ["Pas de document."])
    configuration = dict(analysis.configuration)
    configuration["provider"] = provider_name
    configuration["model"] = model
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()
    assert analysis.status == "failed"
    assert analysis.failure_code == "provider_not_allowed"
    assert analysis.provider_calls_used == 0
    assert not BrainDossier.objects.filter(analysis=analysis).exists()
    assert "sk-test-secret" not in json.dumps(analysis.configuration)
    constructed.assert_not_called()


def test_frozen_openai_uses_the_frozen_model_without_storing_the_key(monkeypatch, settings):
    settings.HOUSTON_BRAIN_PROVIDER = "openai"
    settings.HOUSTON_BRAIN_MODEL = "gpt-5-mini"
    settings.OPENAI_API_KEY = "sk-test-secret"
    allow_publish(monkeypatch)
    analysis = prepare(settings, ["Service lent en salle."])
    assert analysis.configuration["provider"] == "openai"
    assert analysis.configuration["model"] == "gpt-5-mini"
    assert "sk-test-secret" not in json.dumps(analysis.configuration)
    settings.HOUSTON_BRAIN_PROVIDER = "fake"
    settings.HOUSTON_BRAIN_MODEL = "gpt-live"
    client = MagicMock()
    client.chat.completions.create.return_value = _response(content="{}")
    constructed = MagicMock(return_value=client)
    monkeypatch.setattr("openai.OpenAI", constructed)
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()
    assert analysis.status == "completed"
    assert analysis.failure_code == ""
    assert analysis.provider_calls_used == 1
    assert constructed.call_args.kwargs["api_key"] == "sk-test-secret"
    assert constructed.call_args.kwargs["max_retries"] == 0
    first = client.chat.completions.create.call_args.kwargs
    assert first["model"] == "gpt-5-mini"
    assert {tool["function"]["name"] for tool in first["tools"]} >= {"search_signals"}
    blob = json.dumps(first["messages"], ensure_ascii=False)
    assert "sk-test-secret" not in blob
    assert "Service lent en salle." in blob


def test_frozen_fake_does_not_construct_openai(monkeypatch, settings):
    settings.HOUSTON_BRAIN_PROVIDER = "fake"
    settings.HOUSTON_BRAIN_MODEL = "fake"
    settings.OPENAI_API_KEY = ""
    allow_publish(monkeypatch)
    monkeypatch.setenv("HOUSTON_BRAIN_FAKE_MODE", "ok")
    monkeypatch.delenv("HOUSTON_BRAIN_FAKE_HOLD_SECONDS", raising=False)
    analysis = prepare(settings, ["Lecture locale."])
    settings.HOUSTON_BRAIN_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "sk-test-secret"
    settings.HOUSTON_BRAIN_MODEL = "gpt-live"
    constructed = MagicMock(side_effect=AssertionError("client"))
    monkeypatch.setattr("openai.OpenAI", constructed)
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=None)
    analysis.refresh_from_db()
    assert analysis.status == "completed"
    assert analysis.failure_code == ""
    assert analysis.configuration["provider"] == "fake"
    constructed.assert_not_called()
