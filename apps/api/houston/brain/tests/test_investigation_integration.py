"""V3 enters the real attempt only when the frozen engine says so.

The provider is scripted. These tests do not call OpenAI.
"""

from __future__ import annotations

import inspect
import json
import logging
from unittest.mock import MagicMock

import httpx
import pytest
from django.utils import timezone
from openai import BadRequestError
from rest_framework.test import APIClient

from houston.brain.integration import (
    _provider,
    freeze_investigation_configuration,
    project_public_result,
    resolve_investigation_ceilings,
)
from houston.brain.investigation import (
    ENGINE_VERSION,
    PER_CALL_OUTPUT_TOKENS,
    PROVIDER_TIMEOUT_SECONDS,
    investigation_engine,
    investigation_timing,
)
from houston.brain.investigation_contract import (
    SCHEMA_VERSION,
    investigation_prompt,
    investigation_response_schema,
)
from houston.brain.models import (
    BrainAnalysis,
    BrainDossier,
    BrainObjectiveEvaluation,
    BrainSearchRun,
    BrainSuggestion,
)
from houston.brain.openai_provider import OpenAIBrainProvider
from houston.brain.orchestration import STOP_CODE, InvestigationOutcome
from houston.brain.provider import BrainProviderUnavailable
from houston.brain.runtime import publish_brain_analysis, run_brain_analysis
from houston.brain.tasks import run_brain_analysis_task, run_brain_investigation_task
from houston.brain.tests.test_api import _url
from houston.brain.tests.test_investigation_orchestration import (
    RAW_OBSERVATION,
    ScriptedProvider,
    _gap,
    _open,
    _per_call_for,
    _reading,
    _replace_measures,
    _world,
)
from houston.establishments.models import Establishment
from houston.testing.auth import auth_headers, login

pytestmark = pytest.mark.django_db(transaction=True)


def _arm(settings, key: str, **world_kwargs):
    settings.HOUSTON_BRAIN_ENGINE_VERSION = ENGINE_VERSION
    world = _world(settings, key, **world_kwargs)
    analysis = world["analysis"]
    assert investigation_engine(analysis.configuration) is True
    assert investigation_timing(resolve_investigation_ceilings(analysis.configuration)).coherent
    return world


def _run(world, provider):
    analysis = world["analysis"]
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    return analysis


def _detail(world, analysis):
    client = APIClient()
    token = login(client, user=world["owner"].user)
    response = client.get(
        _url(world["establishment"].id, f"analyses/{analysis.id}/"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    return response.json()


def test_default_admission_stays_on_the_lot_executor(settings, monkeypatch):
    world = _world(settings, "lot")
    called = []
    monkeypatch.setattr(
        "houston.brain.integration.execute_investigation",
        lambda *args, **kwargs: called.append(1),
    )
    provider = ScriptedProvider(lambda step, payload, analysis_id: _reading())
    analysis = _run(world, provider)
    runtime = __import__("houston.brain.runtime", fromlist=["runtime"])
    source = inspect.getsource(runtime)

    assert provider.calls == []
    assert "engine_version" not in analysis.configuration
    assert analysis.configuration["schema_version"] == "brain_analysis_v1"
    assert analysis.configuration["ceilings"]["max_calls"] == 12
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.result is None
    assert called == []
    assert "execute_investigation" in source
    assert "run_investigation" not in source


def test_opt_in_freezes_applicable_budgets_and_routes_the_long_task(settings, monkeypatch):
    world = _arm(settings, "budgets")
    ceilings = world["analysis"].configuration["ceilings"]
    seen = {}

    def publish(task, *, args, queue):
        seen["task"] = task
        seen["args"] = args
        return True

    monkeypatch.setattr("houston.core.celery_publish.publish_celery_task", publish)
    published = publish_brain_analysis(world["analysis"].id, world["analysis"].attempt_token)

    assert published is True
    assert ceilings["max_calls"] == 4
    assert ceilings["total_input_tokens"] == 320_000
    assert ceilings["provider_timeout_seconds"] == 180
    assert ceilings["lease_seconds"] == 240
    assert ceilings["attempt_soft_seconds"] == 720
    assert ceilings["attempt_hard_seconds"] == 780
    assert ceilings["follow_up_max_calls"] == settings.HOUSTON_BRAIN_FOLLOW_UP_MAX_CALLS
    assert world["analysis"].configuration["schema_version"] == "brain_analysis_v1"
    assert seen["task"] is run_brain_investigation_task
    assert run_brain_analysis_task is not run_brain_investigation_task
    plain = freeze_investigation_configuration({})
    assert investigation_engine(plain) is True


def test_a_v1_configuration_still_publishes_on_the_short_task(settings, monkeypatch):
    world = _world(settings, "route-v1")
    seen = {}

    def publish(task, *, args, queue):
        seen["task"] = task
        return True

    monkeypatch.setattr("houston.core.celery_publish.publish_celery_task", publish)
    publish_brain_analysis(world["analysis"].id, world["analysis"].attempt_token)

    assert seen["task"] is run_brain_analysis_task


def test_incoherent_attempt_fails_before_a_call(settings):
    world = _world(settings, "temps")
    analysis = world["analysis"]
    configuration = dict(analysis.configuration)
    configuration["engine_version"] = ENGINE_VERSION
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])
    provider = ScriptedProvider(lambda step, payload, analysis_id: _reading())

    analysis = _run(world, provider)

    assert provider.calls == []
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "timing_incoherent"
    assert analysis.result is None


def test_factual_reading_is_completed_without_success(settings):
    world = _arm(settings, "factuel")
    BrainDossier.objects.filter(analysis=world["analysis"]).delete()
    provider = ScriptedProvider(
        lambda step, payload, analysis_id: _reading(
            reported=[{"item_id": str(world["room"].id), "declared_as": "reported"}]
        )
    )

    analysis = _run(world, provider)
    body = _detail(world, analysis)
    stored = json.dumps(body, ensure_ascii=False)

    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert body["qualification"] == "factual_reading"
    assert body["investigation_succeeded"] is False
    assert body["result"]["qualification"] == "factual_reading"
    assert body["result"]["schema_version"] == "brain_investigation_v3"
    assert body["result"]["investigation_succeeded"] is False
    assert all(not row["code"].startswith("lecture:") for row in body["searches"])
    assert RAW_OBSERVATION not in stored
    assert "raw_text" not in stored
    assert BrainSuggestion.objects.filter(analysis=analysis).count() == 0
    assert BrainObjectiveEvaluation.objects.filter(analysis=analysis).count() == 0
    assert provider.calls
    assert provider.calls[0]["timeout"] == 180
    listing = APIClient()
    token = login(listing, user=world["owner"].user)
    page = listing.get(
        _url(world["establishment"].id, "analyses/"),
        **auth_headers(token),
    )
    assert page.status_code == 200
    row = next(item for item in page.json()["results"] if item["id"] == str(analysis.id))
    assert row["qualification"] == "factual_reading"
    assert row["investigation_succeeded"] is False


def test_a_verified_gap_is_not_a_factual_reading(settings):
    def prepare(context):
        _replace_measures(context["reporting"])

    world = _arm(settings, "ecart", before_capture=prepare)
    provider = ScriptedProvider(lambda step, payload, analysis_id: _gap())

    analysis = _run(world, provider)

    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert analysis.result["qualification"] in {"partial", "complete"}
    assert analysis.result["investigation_succeeded"] is True
    assert analysis.result["qualification"] != "factual_reading"
    calculations = analysis.result["subjects"][0]["calculations"]
    assert calculations
    assert all(row["verified"] is True for row in calculations)


def test_cancellation_before_the_next_call_publishes_nothing(settings):
    world = _arm(settings, "annule")

    def handle(step, payload, analysis_id):
        BrainAnalysis.objects.filter(pk=analysis_id).update(cancel_requested_at=timezone.now())
        return _reading(deepening=_open("seasonal_window"))

    provider = ScriptedProvider(handle)
    analysis = _run(world, provider)

    assert [call["step"] for call in provider.calls] == ["lecture:1"]
    assert analysis.status == BrainAnalysis.Status.CANCELED
    assert analysis.result is None


def test_a_second_invalid_schema_fails_without_publishing(settings):
    world = _arm(settings, "schema")
    provider = ScriptedProvider(lambda step, payload, analysis_id: {"schema_version": "nope"})

    analysis = _run(world, provider)

    assert len(provider.calls) <= 4
    assert [call["step"] for call in provider.calls] == ["lecture:1", "correction:1"]
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.result is None
    assert analysis.failure_code == "response_invalid"


def test_a_provider_outage_replays_the_same_reading_once(settings, monkeypatch):
    world = _arm(settings, "reprise")
    monkeypatch.setattr(
        "houston.brain.runtime.publish_brain_analysis",
        lambda *args, **kwargs: True,
    )
    state = {"down": True}

    def handle(step, payload, analysis_id):
        if state["down"]:
            state["down"] = False
            raise BrainProviderUnavailable()
        return _reading()

    provider = ScriptedProvider(handle)
    analysis = world["analysis"]
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.QUEUED
    assert analysis.failure_code == ""
    assert analysis.transient_retries_used == 1
    assert analysis.result is None
    assert [call["step"] for call in provider.calls] == ["lecture:1"]

    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()

    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:1"]
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert analysis.result["qualification"] == "factual_reading"
    assert BrainSearchRun.objects.filter(
        dossier__analysis=analysis,
        code="lecture:2",
    ).count() == 0
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:1"]
    assert analysis.result["investigation_succeeded"] is False


def test_deepening_requests_stop_without_a_fourth_call(settings):
    world = _arm(settings, "plafond", fillers=4, filler_text="x" * 30000)
    analysis = world["analysis"]
    per_call = _per_call_for(analysis, kept_extras=2)
    configuration = dict(analysis.configuration)
    ceilings = dict(configuration["ceilings"])
    ceilings["per_call_input_tokens"] = per_call
    configuration["ceilings"] = ceilings
    analysis.configuration = configuration
    analysis.save(update_fields=["configuration", "updated_at"])

    def handle(step, payload, analysis_id):
        examined = {row.get("source_id") for row in payload.get("examined") or []}
        discovered = [
            row["source_id"]
            for row in payload.get("discovered_not_examined") or []
            if row.get("source_id") not in examined
        ]
        source_id = discovered[0] if discovered else "deja-ouvert"
        return _reading(deepening=_open("period_index_identifier", source_id))

    provider = ScriptedProvider(handle)

    analysis = _run(world, provider)
    codes = set(
        BrainSearchRun.objects.filter(dossier__analysis=analysis).values_list("code", flat=True)
    )

    assert len(provider.calls) <= 3
    assert "lecture:4" not in codes
    assert analysis.provider_calls_used == len(provider.calls)
    assert analysis.provider_calls_used <= 3
    assert analysis.result["code"] in {"deepen_budget_exhausted", "budget_exceeded"}
    assert analysis.result["investigation_succeeded"] is False


def test_projection_hides_unread_copies_and_unverified_identities():
    outcome = InvestigationOutcome(
        treatment="completed",
        code="",
        qualification="factual_reading",
        investigation_succeeded=False,
        semantic_readings=1,
        provider_calls=1,
        corrections=0,
        examined_ids=("s-01", "s-03"),
        discovered_not_examined=("s-02",),
        contradictions=(),
        full_text_ids=("s-01",),
        withheld_contradiction_ids=(),
    )
    lecture = {
        "output": {
            "subjects": [
                {
                    "key": "frequentation",
                    "statement": "Le chiffre est rapporté.",
                    "examined": True,
                    "cause": "established",
                    "evidence_ids": ["s-02", "s-01"],
                    "reported_facts": [{"item_id": "measure:0", "text": "chiffre"}],
                    "contradiction_ids": [],
                    "orientation": "NO_ACTION",
                    "justification": "Contrôle.",
                    "limits": [],
                    "calculations": [
                        {
                            "operation": "product",
                            "role": "identity",
                            "label": "montant",
                            "published_value": "10",
                            "verified": False,
                        }
                    ],
                }
            ]
        },
        "payload": {
            "examined": [
                {"source_id": "s-01", "title": "Service midi", "pole": "Restauration"},
                {"source_id": "s-03", "title": "Plan salle", "pole": "Restauration"},
            ]
        },
        "discovered_not_examined": [
            {"source_id": "s-02", "pole": "Hebergement", "category": "signal"}
        ],
    }

    result = project_public_result(outcome, None, lecture)

    assert result["examined_ids"] == ["s-01", "s-03"]
    assert result["cited_ids"] == ["s-01"]
    assert [row["source_id"] for row in result["examined_not_cited"]] == ["s-03"]
    assert result["cited"][0]["label"] == "Service midi"
    assert result["cited"][0]["disposition"] == "cited"
    assert result["examined_not_cited"][0]["disposition"] == "examined_not_cited"
    assert "s-02" not in result["cited_ids"]
    assert "measure:0" not in result["cited_ids"]
    assert result["subjects"][0]["cited_ids"] == ["s-01"]
    assert result["subjects"][0]["examined"] is False
    assert result["subjects"][0]["cause"] == "unknown"
    assert result["subjects"][0]["calculations"] == []
    assert result["discovered_not_examined"][0]["disposition"] == "discovered_not_examined"
    assert result["investigation_succeeded"] is False


def _bad_request(secret: str) -> BadRequestError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(400, request=request)
    return BadRequestError(secret, response=response, body={"error": {"message": secret}})


def _stop_published(analysis) -> bool:
    stop = BrainSearchRun.objects.filter(dossier__analysis=analysis, code=STOP_CODE).first()
    if stop is None or not isinstance(stop.criteria, dict):
        return False
    return stop.criteria.get("published") is True


def test_provider_http_400_ends_without_retry_or_publication(settings, monkeypatch, caplog):
    world = _arm(settings, "http-400")
    secret = "DOSSIER_SECRET_NOT_FOR_LOGS"
    client = MagicMock()
    client.chat.completions.create.side_effect = _bad_request(secret)
    monkeypatch.setattr("openai.OpenAI", MagicMock(return_value=client))
    provider = OpenAIBrainProvider(
        api_key="test-key",
        model="gpt-test",
        timeout_seconds=30,
        max_output_tokens=32,
    )
    analysis = world["analysis"]
    with caplog.at_level(logging.INFO):
        run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()

    assert client.chat.completions.create.call_count == 1
    assert analysis.status == BrainAnalysis.Status.FAILED
    assert analysis.failure_code == "response_invalid"
    assert analysis.result is None
    assert analysis.transient_retries_used == 0
    assert analysis.provider_calls_used == 0
    assert _stop_published(analysis) is False
    rejected = [
        record
        for record in caplog.records
        if record.message == "brain_investigation_provider_rejected"
    ]
    assert rejected
    assert rejected[0].provider_error == "BadRequestError"
    assert rejected[0].failure_code == "response_invalid"
    assert secret not in caplog.text

    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert client.chat.completions.create.call_count == 1
    assert analysis.result is None


def test_rights_lost_during_the_call_cancel_without_publication(settings):
    world = _arm(settings, "droits")

    def handle(step, payload, analysis_id):
        Establishment.objects.filter(id=world["establishment"].id).update(
            status=Establishment.Status.DEACTIVATED
        )
        return _reading()

    provider = ScriptedProvider(handle)
    analysis = _run(world, provider)

    assert [call["step"] for call in provider.calls] == ["lecture:1"]
    assert analysis.status == BrainAnalysis.Status.CANCELED
    assert analysis.failure_code == "author_rights_lost"
    assert analysis.result is None
    assert _stop_published(analysis) is False
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert [call["step"] for call in provider.calls] == ["lecture:1"]
    assert analysis.result is None


def test_the_openai_adapter_carries_the_v3_schema(settings):
    settings.OPENAI_API_KEY = "sk-readiness-not-a-call"
    provider = _provider(
        {"provider": "openai", "model": "gpt-5-mini"},
        {
            "provider_timeout_seconds": PROVIDER_TIMEOUT_SECONDS,
            "per_call_output_tokens": PER_CALL_OUTPUT_TOKENS,
        },
    )

    assert isinstance(provider, OpenAIBrainProvider)
    assert provider.model == "gpt-5-mini"
    assert provider.timeout_seconds == PROVIDER_TIMEOUT_SECONDS
    assert provider.max_output_tokens == PER_CALL_OUTPUT_TOKENS
    assert provider._system_text == investigation_prompt()
    assert provider._accepted_schema == SCHEMA_VERSION
    assert provider._response_format == investigation_response_schema()
    assert provider._client is None


def test_a_published_v1_result_keeps_an_empty_qualification(settings):
    world = _world(settings, "historique-v1")
    analysis = world["analysis"]
    analysis.status = BrainAnalysis.Status.COMPLETED
    analysis.result = {"schema_version": "brain_analysis_v1", "subjects": []}
    analysis.save(update_fields=["status", "result", "updated_at"])

    body = _detail(world, analysis)

    assert body["status"] == "completed"
    assert body["qualification"] is None
    assert body["investigation_succeeded"] is None
    assert body["result"]["schema_version"] == "brain_analysis_v1"
