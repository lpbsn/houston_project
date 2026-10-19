"""V3 investigation loop with a scripted provider. No paid call and no publication."""

from __future__ import annotations

import inspect
import json
import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from django.conf import settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from houston.brain import runtime
from houston.brain.admission import admit_brain_work
from houston.brain.capture import capture_period_dossier
from houston.brain.configuration import call_input_tokens, json_token_count
from houston.brain.dossier import reload_period_dossier
from houston.brain.investigation import (
    MAX_PROVIDER_CALLS,
    investigation_ceilings,
    investigation_engine,
    investigation_timing,
)
from houston.brain.investigation_contract import (
    investigation_call_tokens,
    investigation_prompt,
    investigation_response_schema,
)
from houston.brain.models import BrainAnalysis, BrainSearchRun
from houston.brain.orchestration import run_investigation
from houston.brain.period import (
    reading_allowance,
    reading_input_tokens,
    select_first_reading,
)
from houston.brain.provider import BrainProviderUnavailable, ProviderCallResult
from houston.brain.records import EXTRACTOR_ID, EXTRACTOR_VERSION
from houston.comments.models import Comment
from houston.establishments.models import EstablishmentMembership
from houston.observations.models import Observation
from houston.signals.models import Signal, SignalSourceObservation
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db(transaction=True)

PERIOD_START = date(2026, 3, 1)
PERIOD_END = date(2026, 3, 8)
SUBJECT_START = date(2026, 3, 5)
SUBJECT_END = date(2026, 3, 8)
PARIS = ZoneInfo("Europe/Paris")
RAW_OBSERVATION = "OBSERVATION-BRUTE au 04/03/2026"
COMMENT_BODY = "COMMENTAIRE-BRUT sur la salle"


def _ceilings(**overrides) -> dict:
    values = {
        **investigation_ceilings(),
        "lease_seconds": 240,
        "attempt_soft_seconds": MAX_PROVIDER_CALLS * 180,
        "attempt_hard_seconds": MAX_PROVIDER_CALLS * 180 + 60,
    }
    values.update(overrides)
    return values


def _at(day: date, hour: int = 12) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=PARIS)


def _reading(
    key: str = "frequentation",
    *,
    evidence: tuple[str, ...] = (),
    contradictions: list | None = None,
    deepening: dict | None = None,
    cause: str = "unknown",
    reported: list | None = None,
) -> dict:
    marks = contradictions or []
    return {
        "schema_version": "brain_investigation_v3",
        "subjects": [
            {
                "key": key,
                "statement": "Le reporting montre le sujet.",
                "examined": True,
                "cause": cause,
                "evidence_ids": list(evidence),
                "contradiction_ids": [row["item_id"] for row in marks],
                "reported_facts": reported or [],
                "hypotheses": [],
                "orientation": "INVESTIGATION",
                "limits": [],
                "calculation": None,
            }
        ],
        "contradictions": marks,
        "deepening": deepening,
    }


def _open(kind: str, source_id: str = "") -> dict:
    return {
        "kind": kind,
        "source_id": source_id,
        "subject_key": "frequentation",
        "activity_subject": "",
        "establishment_id": "",
        "target_at": "",
    }


class ScriptedProvider:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def complete(self, *, analysis_id, lot_key, payload, timeout_seconds):
        self.calls.append(
            {
                "step": lot_key,
                "payload": payload,
                "timeout": timeout_seconds,
                "analysis_id": analysis_id,
            }
        )
        output = self.handler(lot_key, payload, analysis_id)
        if output is None:
            raise BrainProviderUnavailable()
        return ProviderCallResult(
            output=output,
            truncated=False,
            input_tokens=None,
            output_tokens=1,
        )


def _signal(establishment, *, title, summary, created_at, business_unit):
    signal = Signal.objects.create(
        establishment=establishment,
        affected_business_unit=business_unit,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary=summary,
        issue_focus=f"focus-{uuid.uuid4().hex[:12]}",
        location_text="Salle",
        last_activity_at=created_at,
        status=Signal.Status.OPEN,
    )
    Signal.objects.filter(pk=signal.pk).update(
        created_at=created_at,
        updated_at=created_at,
        last_activity_at=created_at,
    )
    signal.refresh_from_db()
    return signal


def _world(
    settings,
    key: str,
    *,
    fillers: int = 0,
    filler_text: str = "REMPLISSAGE",
    filler_texts: list[str] | None = None,
    filler_rows: list[tuple[str, date]] | None = None,
):
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 30
    establishment = create_establishment(name=f"Orchestration {key}", timezone="Europe/Paris")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    restaurant = create_business_unit(
        establishment=establishment,
        key=f"restauration-{key}",
        label="Restauration",
    )
    housing = create_business_unit(
        establishment=establishment,
        key=f"hebergement-{key}",
        label="Hebergement",
    )
    reporting = _reporting(establishment, owner, key)
    room = _signal(
        establishment,
        title="Service salle",
        summary="PREUVE-SALLE",
        created_at=_at(SUBJECT_START),
        business_unit=restaurant,
    )
    housing_signal = _signal(
        establishment,
        title="Clients heberges",
        summary="PISTE-HEBERGEMENT",
        created_at=_at(SUBJECT_START),
        business_unit=housing,
    )
    if filler_rows is None:
        texts = filler_texts if filler_texts is not None else [filler_text] * fillers
        filler_rows = [(text, PERIOD_START) for text in texts]
    extras = []
    for index, (text, created_on) in enumerate(filler_rows):
        summary = (
            text
            if filler_texts is not None or text.startswith(("CONTRADICTION", "CANDIDAT-PETIT"))
            else f"CANDIDAT-{index}-{text}"
        )
        extras.append(
            _signal(
                establishment,
                title=f"Remplissage {index}",
                summary=summary,
                created_at=_at(created_on),
                business_unit=restaurant,
            )
        )
    observation = Observation.objects.create(
        establishment=establishment,
        submitted_by_membership=owner,
        raw_text=RAW_OBSERVATION,
        client_submission_id=uuid.uuid4(),
        submitted_at=timezone.now(),
    )
    SignalSourceObservation.objects.create(
        signal=room,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    Comment.objects.create(
        establishment=establishment,
        signal=room,
        author_membership=owner,
        body=COMMENT_BODY,
    )
    analysis = admit_brain_work(
        user=owner.user,
        establishment_id=establishment.id,
        reporting_id=reporting.id,
        idempotency_key=f"orchestration-{key}",
    )
    capture_period_dossier(analysis.id)
    return {
        "analysis": analysis,
        "room": room,
        "housing": housing_signal,
        "extras": extras,
    }


def _reporting(establishment, owner, key: str):
    from houston.brain.models import BrainExtraction, BrainReporting

    reporting = BrainReporting.objects.create(
        establishment=establishment,
        author=owner.user,
        original_filename="semaine.csv",
        content_type="text/csv",
        source_format=BrainReporting.SourceFormat.CSV,
        content_sha256=uuid.uuid4().hex + uuid.uuid4().hex[:32],
        storage_key=f"brain/reportings/{establishment.id}/{uuid.uuid4()}/original",
        byte_size=16,
        status=BrainReporting.Status.READY,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        period_confirmed_at=timezone.now(),
    )
    BrainExtraction.objects.create(
        reporting=reporting,
        extractor_id=EXTRACTOR_ID,
        extractor_version=EXTRACTOR_VERSION,
        source_sha256=reporting.content_sha256,
        payload={
            "measures": [
                {
                    "label": "frequentation",
                    "value": "-12",
                    "value_kind": "number",
                    "unit": "couverts",
                    "scope": "Restauration",
                    "raw_text": RAW_OBSERVATION,
                }
            ],
            "qualitative": [{"kind": "paragraph", "text": "Baisse de frequentation en salle."}],
        },
    )
    return reporting


def _run(analysis, provider, **ceilings):
    return run_investigation(
        analysis.id,
        provider=provider,
        subject_pole="Restauration",
        subject_start=SUBJECT_START,
        subject_end=SUBJECT_END,
        ceilings=_ceilings(**ceilings),
    )


def _blob(analysis) -> str:
    parts = [
        json.dumps(row.criteria, ensure_ascii=False)
        for row in BrainSearchRun.objects.filter(dossier__analysis=analysis)
    ]
    return "\n".join(parts)


def _payloads(provider: ScriptedProvider) -> list[dict]:
    return [call["payload"] for call in provider.calls]


def test_shipped_attempt_cannot_cover_four_provider_timeouts():
    verdict = investigation_timing(
        {
            "provider_timeout_seconds": settings.HOUSTON_BRAIN_PROVIDER_TIMEOUT_SECONDS,
            "lease_seconds": settings.HOUSTON_BRAIN_LEASE_SECONDS,
            "attempt_soft_seconds": settings.HOUSTON_BRAIN_ATTEMPT_SOFT_SECONDS,
            "attempt_hard_seconds": settings.HOUSTON_BRAIN_ATTEMPT_HARD_SECONDS,
            "max_provider_calls": MAX_PROVIDER_CALLS,
        }
    )

    assert settings.HOUSTON_BRAIN_LEASE_SECONDS > settings.HOUSTON_BRAIN_PROVIDER_TIMEOUT_SECONDS
    assert (
        verdict.needed_seconds
        == MAX_PROVIDER_CALLS * settings.HOUSTON_BRAIN_PROVIDER_TIMEOUT_SECONDS
    )
    assert verdict.coherent is False
    assert "lease_not_after_timeout" not in verdict.issues
    assert "attempt_shorter_than_calls" in verdict.issues
    assert "soft_shorter_than_calls" in verdict.issues


def test_prompt_and_schema_are_counted_apart_from_the_current_contract():
    allowance = reading_allowance(
        instructions=investigation_prompt(),
        schema=investigation_response_schema(),
    )
    payload = {"reading": 1}

    assert allowance.instruction_tokens > 0
    assert allowance.schema_tokens > 0
    assert investigation_call_tokens(payload) == allowance.overhead_tokens + json_token_count(
        payload
    )
    assert investigation_call_tokens(payload) != call_input_tokens(payload)


def test_current_worker_budget_does_not_start_a_call(settings):
    world = _world(settings, "budget-courant")
    provider = ScriptedProvider(lambda step, payload, analysis_id: _reading())

    outcome = run_investigation(
        world["analysis"].id,
        provider=provider,
        subject_pole="Restauration",
        subject_start=SUBJECT_START,
        subject_end=SUBJECT_END,
    )

    assert outcome.treatment == "failed"
    assert outcome.code == "timing_incoherent"
    assert outcome.published is False
    assert provider.calls == []
    assert investigation_engine(world["analysis"].configuration) is False
    assert "run_investigation" not in inspect.getsource(runtime)


def test_a_simple_reading_keeps_signal_text_and_does_not_publish(settings):
    world = _world(settings, "simple")
    provider = ScriptedProvider(
        lambda step, payload, analysis_id: _reading(
            reported=[
                {"item_id": str(world["room"].id), "declared_as": "reported"},
            ]
        )
    )

    with CaptureQueriesContext(connection) as queries:
        outcome = _run(world["analysis"], provider)
    sql = "\n".join(query["sql"] for query in queries.captured_queries)
    analysis = BrainAnalysis.objects.get(id=world["analysis"].id)

    assert outcome.treatment == "completed"
    assert outcome.qualification == "factual_reading"
    assert outcome.investigation_succeeded is False
    assert outcome.semantic_readings == 1
    assert outcome.provider_calls == 1
    assert outcome.published is False
    assert analysis.result is None
    assert analysis.status == BrainAnalysis.Status.QUEUED
    assert [call["step"] for call in provider.calls] == ["lecture:1"]
    assert provider.calls[0]["timeout"] == 180
    sent = json.dumps(provider.calls[0]["payload"], ensure_ascii=False)
    assert "PREUVE-SALLE" in sent
    assert "PISTE-HEBERGEMENT" in sent
    assert RAW_OBSERVATION not in sent
    assert COMMENT_BODY not in sent
    assert RAW_OBSERVATION not in _blob(world["analysis"])
    assert Signal._meta.db_table not in sql
    assert Observation._meta.db_table not in sql
    assert Comment._meta.db_table not in sql


def test_an_unexamined_candidate_is_opened_from_the_frozen_copy(settings):
    world = _world(settings, "piste", fillers=4, filler_text="x" * 30000)
    per_call = _per_call_for(world["analysis"])
    opened = {"id": None, "marker": ""}

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            discovered = payload["discovered_not_examined"]
            assert discovered
            opened["id"] = discovered[0]["source_id"]
            opened["marker"] = _frozen_summary(world["analysis"], opened["id"])[:24]
            housing = str(world["housing"].id)
            return _reading(
                contradictions=[
                    {
                        "subject_key": "frequentation",
                        "item_id": housing,
                        "note": "Autre pôle sur les mêmes dates.",
                    }
                ],
                deepening=_open("period_index_identifier", opened["id"]),
            )
        assert opened["id"] in {row.get("source_id") for row in payload["examined"]}
        return _reading(
            contradictions=[
                {
                    "subject_key": "frequentation",
                    "item_id": str(world["housing"].id),
                    "note": "La piste hébergement reste ouverte.",
                }
            ]
        )

    provider = ScriptedProvider(handle)
    with CaptureQueriesContext(connection) as queries:
        outcome = _run(world["analysis"], provider, per_call_input_tokens=per_call)
    sql = "\n".join(query["sql"] for query in queries.captured_queries)
    first, second = _payloads(provider)
    conclusion = json.dumps(second, ensure_ascii=False)

    assert outcome.semantic_readings == 2
    assert outcome.provider_calls == 2
    assert outcome.published is False
    assert opened["marker"] not in json.dumps(first, ensure_ascii=False)
    assert "PISTE-HEBERGEMENT" in json.dumps(first, ensure_ascii=False)
    assert "PISTE-HEBERGEMENT" in conclusion
    assert opened["marker"] in conclusion
    assert "previous_summary" not in conclusion
    assert RAW_OBSERVATION not in conclusion
    assert len(provider.calls) < 1 + len(world["extras"])
    assert Signal._meta.db_table not in sql
    assert Observation._meta.db_table not in sql
    world["room"].structured_summary = "APRES-CAPTURE"
    world["room"].save(update_fields=["structured_summary", "updated_at"])
    assert "APRES-CAPTURE" not in _blob(world["analysis"])
    assert "PREUVE-SALLE" in _blob(world["analysis"])


def test_a_contradiction_that_does_not_fit_blocks_the_finding(settings):
    large = "CONTRADICTION-LARGE " + ("L" * 40000)
    small = "CANDIDAT-PETIT " + ("s" * 20000)
    world = _world(
        settings,
        "trop-large",
        filler_rows=[(large, date(2026, 3, 4)), (small, PERIOD_START)],
    )
    large_id = next(
        str(signal.id)
        for signal in world["extras"]
        if signal.structured_summary.startswith("CONTRADICTION")
    )
    small_id = next(
        str(signal.id)
        for signal in world["extras"]
        if signal.structured_summary.startswith("CANDIDAT")
    )
    per_call = _per_call_between(world["analysis"], large_id, small_id)

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            return _reading(
                evidence=(str(world["room"].id),),
                contradictions=[
                    {
                        "subject_key": "frequentation",
                        "item_id": large_id,
                        "note": "Un texte long contredit le constat.",
                    }
                ],
                deepening=_open("period_index_identifier", small_id),
            )
        return _reading(evidence=(str(world["room"].id),))

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider, per_call_input_tokens=per_call)
    conclusion = json.dumps(provider.calls[-1]["payload"], ensure_ascii=False)

    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:2"]
    assert "CONTRADICTION-LARGE" in json.dumps(provider.calls[0]["payload"], ensure_ascii=False)
    assert "CONTRADICTION-LARGE" not in conclusion
    assert "CANDIDAT-PETIT" in conclusion
    assert "PISTE-HEBERGEMENT" in conclusion
    assert large_id in outcome.withheld_contradiction_ids
    assert outcome.qualification == "refused"
    assert outcome.investigation_succeeded is False
    assert outcome.published is False


def test_continuous_deepening_stops_after_two_openings(settings):
    world = _world(settings, "plafond", fillers=4, filler_text="x" * 30000)
    per_call = _per_call_for(world["analysis"])

    def handle(step, payload, analysis_id):
        discovered = payload["discovered_not_examined"]
        source_id = discovered[0]["source_id"] if discovered else "deja-ouvert"
        return _reading(deepening=_open("period_index_identifier", source_id))

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider, per_call_input_tokens=per_call)
    codes = {
        row.code: row.criteria.get("code")
        for row in BrainSearchRun.objects.filter(dossier__analysis=world["analysis"])
    }

    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:2", "lecture:3"]
    assert outcome.semantic_readings == 3
    assert outcome.provider_calls == 3
    assert outcome.code == "deepen_budget_exhausted"
    assert outcome.investigation_succeeded is False
    assert codes["decision:1"] == "accepted"
    assert codes["decision:2"] == "accepted"
    assert codes["decision:3"] == "deepen_budget_exhausted"
    assert "lecture:4" not in codes


def test_a_second_invalid_schema_fails_without_a_result(settings):
    world = _world(settings, "schema")
    provider = ScriptedProvider(lambda step, payload, analysis_id: {"schema_version": "nope"})

    outcome = _run(world["analysis"], provider)
    again = ScriptedProvider(lambda step, payload, analysis_id: _reading())
    replay = _run(world["analysis"], again)
    analysis = BrainAnalysis.objects.get(id=world["analysis"].id)

    assert [call["step"] for call in provider.calls] == ["lecture:1", "correction:1"]
    assert outcome.treatment == "failed"
    assert outcome.code == "response_invalid"
    assert outcome.qualification is None
    assert outcome.investigation_succeeded is False
    assert outcome.semantic_readings == 0
    assert outcome.provider_calls == 2
    assert outcome.published is False
    assert analysis.result is None
    assert again.calls == []
    assert replay.treatment == "failed"
    assert replay.provider_calls == 2


def test_a_signal_cannot_be_accepted_as_an_established_cause(settings):
    world = _world(settings, "cause")
    signal_id = str(world["room"].id)

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            return _reading(cause="established", evidence=(signal_id,))
        return _reading(
            cause="reported",
            reported=[{"item_id": signal_id, "declared_as": "reported"}],
        )

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider)
    stored = BrainSearchRun.objects.get(
        dossier__analysis=world["analysis"],
        code="lecture:1",
    ).criteria["output"]

    assert [call["step"] for call in provider.calls] == ["lecture:1", "correction:1"]
    assert outcome.treatment == "completed"
    assert outcome.semantic_readings == 1
    assert outcome.corrections == 1
    assert stored["subjects"][0]["cause"] == "reported"
    assert outcome.qualification == "factual_reading"
    assert outcome.investigation_succeeded is False


def test_a_timeout_replays_the_same_reading(settings):
    world = _world(settings, "reprise", fillers=4, filler_text="x" * 30000)
    per_call = _per_call_for(world["analysis"])
    failed = {"pending": True}

    def handle(step, payload, analysis_id):
        if step == "lecture:2" and failed["pending"]:
            failed["pending"] = False
            return None
        discovered = payload["discovered_not_examined"]
        if step == "lecture:1" and discovered:
            return _reading(deepening=_open("period_index_identifier", discovered[0]["source_id"]))
        return _reading()

    provider = ScriptedProvider(handle)
    interrupted = _run(world["analysis"], provider, per_call_input_tokens=per_call)
    resumed = _run(world["analysis"], provider, per_call_input_tokens=per_call)

    assert interrupted.treatment == "interrupted"
    assert interrupted.code == "provider_unavailable"
    assert interrupted.semantic_readings == 1
    assert interrupted.replay_step == "lecture:2"
    assert resumed.semantic_readings == 2
    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:2", "lecture:2"]
    assert provider.calls[1]["payload"] == provider.calls[2]["payload"]
    assert resumed.provider_calls == 2


def test_cancellation_before_the_next_call_publishes_nothing(settings):
    world = _world(settings, "annulation", fillers=4, filler_text="x" * 30000)
    per_call = _per_call_for(world["analysis"])

    def handle(step, payload, analysis_id):
        BrainAnalysis.objects.filter(id=analysis_id).update(cancel_requested_at=timezone.now())
        discovered = payload["discovered_not_examined"]
        return _reading(deepening=_open("period_index_identifier", discovered[0]["source_id"]))

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider, per_call_input_tokens=per_call)
    analysis = BrainAnalysis.objects.get(id=world["analysis"].id)

    assert [call["step"] for call in provider.calls] == ["lecture:1"]
    assert outcome.treatment == "canceled"
    assert outcome.code == "cancel_requested"
    assert outcome.published is False
    assert analysis.result is None


def test_outside_the_menu_and_a_historical_kind_do_not_query_the_database(settings):
    world = _world(settings, "menu")

    def handle(step, payload, analysis_id):
        return _reading(deepening=_open("seasonal_window"))

    provider = ScriptedProvider(handle)
    with CaptureQueriesContext(connection) as queries:
        outcome = _run(world["analysis"], provider)
    sql = "\n".join(query["sql"] for query in queries.captured_queries)

    assert [call["step"] for call in provider.calls] == ["lecture:1"]
    assert outcome.code == "not_in_frozen_dossier"
    assert outcome.semantic_readings == 1
    assert Signal._meta.db_table not in sql

    other = _world(settings, "hors-menu")
    outsider = ScriptedProvider(
        lambda step, payload, analysis_id: _reading(deepening=_open("sql_query"))
    )
    refused = _run(other["analysis"], outsider)
    assert [call["step"] for call in outsider.calls] == ["lecture:1"]
    assert refused.code == "outside_menu"


def test_the_attempt_stops_before_a_call_that_cannot_finish(settings):
    world = _world(settings, "delai", fillers=4, filler_text="x" * 30000)
    per_call = _per_call_for(world["analysis"])
    moments = iter((0, 0, 700))

    def handle(step, payload, analysis_id):
        discovered = payload["discovered_not_examined"]
        return _reading(deepening=_open("period_index_identifier", discovered[0]["source_id"]))

    provider = ScriptedProvider(handle)
    outcome = run_investigation(
        world["analysis"].id,
        provider=provider,
        subject_pole="Restauration",
        subject_start=SUBJECT_START,
        subject_end=SUBJECT_END,
        ceilings=_ceilings(per_call_input_tokens=per_call),
        clock=lambda: next(moments),
    )

    assert [call["step"] for call in provider.calls] == ["lecture:1"]
    assert outcome.treatment == "failed"
    assert outcome.code == "attempt_exceeded"
    assert outcome.semantic_readings == 1


def _per_call_between(analysis, kept_id: str, excluded_id: str) -> int:
    """Fits the representatives plus ``kept_id``, and not the next text."""
    snapshot = reload_period_dossier(analysis.id)
    allowance = reading_allowance(
        instructions=investigation_prompt(),
        schema=investigation_response_schema(),
        per_call_input_tokens=200_000,
    )
    reading = select_first_reading(
        snapshot,
        subject_pole="Restauration",
        subject_start=SUBJECT_START,
        subject_end=SUBJECT_END,
        allowance=allowance,
    )
    representatives = reading.representative_ids
    kept = reading_input_tokens(snapshot, representatives + (kept_id,))
    both = reading_input_tokens(snapshot, representatives + (kept_id, excluded_id))
    gap = max(2, both - kept)
    return allowance.overhead_tokens + kept + (gap // 2)


def _per_call_for(analysis, kept_extras: int = 2) -> int:
    """Room for the representatives and a few extras, not for every filler."""
    snapshot = reload_period_dossier(analysis.id)
    allowance = reading_allowance(
        instructions=investigation_prompt(),
        schema=investigation_response_schema(),
        per_call_input_tokens=80_000,
    )
    reading = select_first_reading(
        snapshot,
        subject_pole="Restauration",
        subject_start=SUBJECT_START,
        subject_end=SUBJECT_END,
        allowance=allowance,
    )
    representatives = reading.representative_ids
    mandatory = reading_input_tokens(snapshot, representatives)
    extras = [
        source_id for source_id in reading.examined_ids if source_id not in set(representatives)
    ]
    one = reading_input_tokens(snapshot, representatives + (extras[0],))
    increment = max(1, one - mandatory)
    return allowance.overhead_tokens + mandatory + (kept_extras * increment) + 3_000


def _frozen_summary(analysis, source_id: str) -> str:
    from houston.brain.models import BrainDossierItem

    payload = BrainDossierItem.objects.get(
        dossier__analysis=analysis,
        stable_key=f"signal:{source_id}",
    ).payload
    return str(payload["structured_summary"])
