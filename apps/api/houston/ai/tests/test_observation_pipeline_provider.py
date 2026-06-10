from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from pydantic import ValidationError

from houston.ai.models import AIUsageLog
from houston.ai.observation_pipeline import (
    FakeObservationPipelineProvider,
    ObservationPipelineInvalidOutputError,
    ObservationPipelineSchemaError,
    ObservationPipelineUnavailableError,
    OpenAIObservationPipelineProvider,
    call_observation_pipeline,
    get_observation_pipeline_provider,
    parse_pipeline_output,
)
from houston.ai.observation_pipeline_provider_schema import (
    AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME,
    openai_strict_response_format,
)
from houston.ai.observation_pipeline_schema import ObservationPipelineOutput
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
)
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import run_observation_pipeline
from houston.signals.tasks import process_observation_task
from houston.signals.tests.conftest import (
    GOLDEN_OBSERVATION_TEXT,
    RESTAURANT_MODULE_KEY,
    create_observation,
    create_restaurant_v3_taxonomy,
)
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def _setup_hotel_pipeline_taxonomy(establishment):
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    return hotel


def _single_candidate_openai_payload(
    *,
    affected_key: str = "hotel",
    responsible_key: str = "hotel",
    subject_key: str = "maintenance",
) -> dict:
    return {
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "candidates": [
            {
                "title": "Lumière clignote à l'entrée du restaurant",
                "structured_summary": (
                    "Éclairage instable signalé à l'entrée du restaurant, "
                    "intervention maintenance requise."
                ),
                "affected_business_unit_key": affected_key,
                "responsible_business_unit_key": responsible_key,
                "activity_subject_key": subject_key,
                "operational_unit_key": None,
                "location_text": None,
                "aggregate_into_signal_id": None,
            }
        ],
    }


def _openai_invalid_schema_bad_request_error():
    from openai import BadRequestError

    response = MagicMock()
    response.status_code = 400
    return BadRequestError(
        (
            "Invalid schema for response_format "
            f"'{AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME}': "
            "context=('properties', 'activity_subject_key'), "
            "$ref cannot have keywords {'description'}."
        ),
        response=response,
        body=None,
    )


def _mock_openai_completion(*, content: str, request_id: str = "chatcmpl-test"):
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30)
    return SimpleNamespace(id=request_id, choices=[choice], usage=usage)


@pytest.fixture
def mock_openai_client():
    with patch("openai.OpenAI") as mock_openai_cls:
        client = MagicMock()
        mock_openai_cls.return_value = client
        yield client


def test_get_observation_pipeline_provider_uses_fake_under_pytest():
    provider = get_observation_pipeline_provider()
    assert isinstance(provider, FakeObservationPipelineProvider)


@override_settings(HOUSTON_AI_OBSERVATION_PROVIDER="openai")
def test_runtime_provider_can_be_openai_when_setting_is_openai_without_calling_openai():
    provider = get_observation_pipeline_provider()
    assert isinstance(provider, OpenAIObservationPipelineProvider)


@override_settings(HOUSTON_AI_OBSERVATION_PROVIDER="invalid")
def test_unknown_observation_provider_fails_clearly():
    with pytest.raises(
        ObservationPipelineUnavailableError,
        match="Unknown observation pipeline provider",
    ):
        get_observation_pipeline_provider()


@pytest.mark.allow_openai_observation_propose
@override_settings(HOUSTON_AI_OBSERVATION_PROVIDER="openai", OPENAI_API_KEY="")
@patch.object(FakeObservationPipelineProvider, "propose")
def test_openai_provider_without_api_key_does_not_fallback_to_fake(mock_fake_propose):
    membership = build_membership()
    _setup_hotel_pipeline_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    with pytest.raises(ObservationPipelineUnavailableError):
        run_observation_pipeline(observation.id)

    mock_fake_propose.assert_not_called()
    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status in {
        ObservationProcessing.Status.RETRYING,
        ObservationProcessing.Status.FAILED,
    }
    assert not Signal.objects.filter(establishment=membership.establishment).exists()


@patch.object(OpenAIObservationPipelineProvider, "propose")
def test_run_observation_pipeline_does_not_call_openai_in_standard_tests(mock_openai_propose):
    membership = build_membership()
    _setup_hotel_pipeline_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    run_observation_pipeline(observation.id)

    mock_openai_propose.assert_not_called()
    assert isinstance(get_observation_pipeline_provider(), FakeObservationPipelineProvider)
    log = AIUsageLog.objects.get(observation=observation)
    assert log.prompt_version == AI_OBSERVATION_PIPELINE_PROMPT_VERSION
    assert log.schema_version == AI_OBSERVATION_PIPELINE_SCHEMA_VERSION


@pytest.mark.allow_openai_observation_propose
def test_openai_provider_sends_json_schema_strict_response_format(mock_openai_client):
    provider = OpenAIObservationPipelineProvider(api_key="test-key")
    mock_openai_client.chat.completions.create.return_value = _mock_openai_completion(
        content=json.dumps(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "candidates": [],
            }
        )
    )

    provider.propose(
        input_payload={
            "observation_id": "00000000-0000-0000-0000-000000000001",
            "establishment_taxonomy": {"business_units": [], "operational_units": []},
            "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            "prompt_version": AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
        }
    )

    kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == openai_strict_response_format()
    assert kwargs["response_format"]["type"] == "json_schema"
    assert kwargs["response_format"]["json_schema"]["strict"] is True
    assert kwargs["response_format"]["type"] != "json_object"

    messages = kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert "Tu es un analyste qualité opérationnel" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    user_payload = json.loads(messages[1]["content"])
    assert user_payload["prompt_version"] == AI_OBSERVATION_PIPELINE_PROMPT_VERSION
    assert "Tu es un analyste qualité opérationnel" not in messages[1]["content"]


@pytest.mark.allow_openai_observation_propose
def test_openai_provider_parses_valid_mocked_response(mock_openai_client):
    provider = OpenAIObservationPipelineProvider(api_key="test-key")
    payload = _single_candidate_openai_payload()
    mock_openai_client.chat.completions.create.return_value = _mock_openai_completion(
        content=json.dumps(payload)
    )

    response = provider.propose(
        input_payload={
            "observation_id": "00000000-0000-0000-0000-000000000001",
            "establishment_taxonomy": {"business_units": [], "operational_units": []},
        }
    )

    output = parse_pipeline_output(response.payload)
    assert isinstance(output, ObservationPipelineOutput)
    assert len(output.candidates) == 1


@pytest.mark.allow_openai_observation_propose
def test_openai_provider_invalid_payload_writes_safe_error_context(mock_openai_client):
    membership = build_membership()
    _setup_hotel_pipeline_taxonomy(membership.establishment)
    observation = create_observation(
        membership=membership,
        text=GOLDEN_OBSERVATION_TEXT,
    )
    provider = OpenAIObservationPipelineProvider(api_key="test-key")
    mock_openai_client.chat.completions.create.return_value = _mock_openai_completion(
        content=json.dumps(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "signals": [],
            }
        ),
        request_id="chatcmpl-invalid",
    )

    with pytest.raises(ObservationPipelineInvalidOutputError):
        call_observation_pipeline(observation=observation, provider=provider)

    log = AIUsageLog.objects.get(observation=observation)
    assert log.error_code == "invalid_structured_output"
    assert log.error_context["validation_error_count"] >= 1
    assert log.error_context["has_candidates"] is False
    assert "signals" in log.error_context["top_level_keys"]
    assert log.error_context["response_format_mode"] == "json_schema_strict"
    serialized = json.dumps(log.error_context)
    assert GOLDEN_OBSERVATION_TEXT not in serialized
    assert observation.raw_text not in serialized


@pytest.mark.allow_openai_observation_propose
@patch.object(FakeObservationPipelineProvider, "propose")
def test_invalid_openai_output_does_not_fallback_to_fake(
    mock_fake_propose,
    mock_openai_client,
):
    membership = build_membership()
    _setup_hotel_pipeline_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    provider = OpenAIObservationPipelineProvider(api_key="test-key")
    invalid_payload = {
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "signals": [],
    }
    mock_openai_client.chat.completions.create.return_value = _mock_openai_completion(
        content=json.dumps(invalid_payload)
    )

    run_observation_pipeline(
        observation.id,
        provider=provider,
    )

    mock_fake_propose.assert_not_called()
    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
    assert processing.last_error_code == "invalid_structured_output"
    assert not Signal.objects.filter(establishment=membership.establishment).exists()


@pytest.mark.allow_openai_observation_propose
@patch.object(FakeObservationPipelineProvider, "propose")
def test_openai_invalid_schema_bad_request_fails_pipeline_without_fake_fallback(
    mock_fake_propose,
    mock_openai_client,
):
    membership = build_membership()
    _setup_hotel_pipeline_taxonomy(membership.establishment)
    observation = create_observation(
        membership=membership,
        text=GOLDEN_OBSERVATION_TEXT,
    )
    provider = OpenAIObservationPipelineProvider(api_key="test-key")
    schema_error = _openai_invalid_schema_bad_request_error()
    mock_openai_client.chat.completions.create.side_effect = schema_error

    run_observation_pipeline(observation.id, provider=provider)

    mock_fake_propose.assert_not_called()
    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
    assert processing.last_error_code == "invalid_response_schema"
    assert not CandidateSignal.objects.filter(observation=observation).exists()
    assert not Signal.objects.filter(establishment=membership.establishment).exists()

    log = AIUsageLog.objects.get(observation=observation)
    assert log.provider == "openai"
    assert log.status == AIUsageLog.Status.FAILED
    assert log.error_code == "invalid_response_schema"
    assert log.error_context.get("provider_error_param", "") == ""
    assert "Invalid schema" in log.error_context["message_excerpt"]
    assert log.error_context["response_format_name"] == AI_OBSERVATION_PIPELINE_PROVIDER_SCHEMA_NAME
    serialized = json.dumps(log.error_context)
    assert GOLDEN_OBSERVATION_TEXT not in serialized
    assert observation.raw_text not in serialized


@pytest.mark.allow_openai_observation_propose
def test_openai_invalid_schema_bad_request_raises_schema_error_from_call_pipeline(
    mock_openai_client,
):
    membership = build_membership()
    _setup_hotel_pipeline_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    provider = OpenAIObservationPipelineProvider(api_key="test-key")
    schema_error = _openai_invalid_schema_bad_request_error()
    mock_openai_client.chat.completions.create.side_effect = schema_error

    with pytest.raises(ObservationPipelineSchemaError):
        call_observation_pipeline(observation=observation, provider=provider)


@pytest.mark.allow_openai_observation_propose
@override_settings(HOUSTON_AI_OBSERVATION_PROVIDER="openai", OPENAI_API_KEY="test-key")
@patch.object(FakeObservationPipelineProvider, "propose")
def test_celery_task_does_not_raise_on_invalid_schema_bad_request(
    mock_fake_propose,
    mock_openai_client,
):
    membership = build_membership()
    _setup_hotel_pipeline_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    schema_error = _openai_invalid_schema_bad_request_error()
    mock_openai_client.chat.completions.create.side_effect = schema_error

    process_observation_task.run(str(observation.id))

    mock_fake_propose.assert_not_called()
    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
    assert processing.last_error_code == "invalid_response_schema"


@pytest.mark.allow_openai_observation_propose
def test_golden_observation_with_mocked_openai_creates_candidate_and_signal(
    mock_openai_client,
):
    membership = build_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.lighting_subject is not None
    observation = create_observation(
        membership=membership,
        text=GOLDEN_OBSERVATION_TEXT,
    )
    provider = OpenAIObservationPipelineProvider(api_key="test-key")
    mock_openai_client.chat.completions.create.return_value = _mock_openai_completion(
        content=json.dumps(
            _single_candidate_openai_payload(
                affected_key=RESTAURANT_MODULE_KEY,
                responsible_key="maintenance",
                subject_key=taxonomy.lighting_subject.normalized_name,
            )
        )
    )

    run_observation_pipeline(observation.id, provider=provider)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED
    assert CandidateSignal.objects.filter(
        observation=observation,
        outcome=CandidateSignal.Outcome.CREATED_SIGNAL,
    ).exists()
    assert Signal.objects.filter(establishment=membership.establishment).exists()
    log = AIUsageLog.objects.get(observation=observation)
    assert log.provider == "openai"
    assert log.status == AIUsageLog.Status.SUCCEEDED
    assert log.error_code == ""
    assert log.prompt_version == AI_OBSERVATION_PIPELINE_PROMPT_VERSION


def test_parse_pipeline_output_rejects_invalid_shape():
    with pytest.raises(ObservationPipelineInvalidOutputError) as exc_info:
        parse_pipeline_output(
            {
                "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                "signals": [],
            }
        )

    assert isinstance(exc_info.value.__cause__, ValidationError)
    assert exc_info.value.payload["signals"] == []
