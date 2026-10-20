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
    retained_execution_budget,
)
from houston.brain.investigation_contract import (
    investigation_call_tokens,
    investigation_prompt,
    investigation_response_schema,
)
from houston.brain.models import BrainAnalysis, BrainDossier, BrainExtraction, BrainSearchRun
from houston.brain.orchestration import _fit_call, run_investigation
from houston.brain.period import (
    PeriodCopy,
    PeriodSnapshot,
    reading_allowance,
    reading_input_tokens,
    select_first_reading,
)
from houston.brain.provider import BrainProviderUnavailable, ProviderCallResult
from houston.brain.records import EXTRACTOR_ID, EXTRACTOR_VERSION
from houston.comments.models import Comment
from houston.establishments.models import EstablishmentMembership
from houston.observations.models import Observation
from houston.signals.models import Signal, SignalLifecycleEvent, SignalSourceObservation
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
                "movement": "qualitative",
                "statement": "Le reporting montre le sujet.",
                "examined": True,
                "cause": cause,
                "evidence_ids": list(evidence),
                "contradiction_ids": [row["item_id"] for row in marks],
                "reported_facts": reported or [],
                "explanations": [],
                "decisive_checks": [],
                "findings": [],
                "calculations": [],
                "breakdowns": [],
                "tradeoffs": [],
                "orientation": "NO_ACTION",
                "justification": "Ce contrôle ne décide pas d'une action.",
                "does_not_promise": "",
                "limits": [
                    {
                        "text": "Contrôle du moteur.",
                        "effect": "coverage",
                        "item_ids": [],
                    }
                ],
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
    before_capture=None,
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
    if before_capture is not None:
        before_capture(
            {
                "establishment": establishment,
                "owner": owner,
                "reporting": reporting,
                "analysis": analysis,
                "room": room,
                "housing": housing_signal,
            }
        )
    capture_period_dossier(analysis.id)
    return {
        "analysis": analysis,
        "establishment": establishment,
        "owner": owner,
        "reporting": reporting,
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
    retained = retained_execution_budget()
    assert investigation_timing(retained).coherent is True
    assert settings.HOUSTON_BRAIN_ATTEMPT_SOFT_SECONDS < retained["attempt_soft_seconds"]
    assert settings.HOUSTON_BRAIN_ATTEMPT_HARD_SECONDS < retained["attempt_hard_seconds"]
    assert settings.HOUSTON_BRAIN_LEASE_SECONDS == retained["lease_seconds"]
    assert settings.HOUSTON_BRAIN_ATTEMPT_SOFT_SECONDS == 600
    assert settings.HOUSTON_BRAIN_ATTEMPT_HARD_SECONDS == 660


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
    examined = provider.calls[-1]["payload"]["examined"]
    assert large_id not in {row.get("source_id") for row in examined}
    assert not any(row.get("reduced") or row.get("text_withheld") for row in examined)
    assert large_id in outcome.withheld_contradiction_ids
    assert outcome.qualification == "refused"
    assert outcome.investigation_succeeded is False
    assert outcome.published is False


def test_a_text_left_out_of_the_call_is_not_presented_as_examined(monkeypatch):
    def cost(payload):
        examined = payload.get("examined") or []
        if any("LONG-TEXT" in json.dumps(row, ensure_ascii=False) for row in examined):
            return 100
        return 10 if len(examined) <= 1 else 100

    monkeypatch.setattr("houston.brain.orchestration.investigation_call_tokens", cost)
    kept = _copy("kept", "TEXTE-COURT")
    dropped = _copy("dropped", "TEXTE-ECARTE")
    large = _copy("large", "LONG-TEXT " + ("L" * 20))
    small = _copy("small", "PETIT-TEXTE")
    snapshot = _snapshot((kept, dropped, large, small))

    fitted = _fit_call(
        snapshot,
        examined_ids=("kept", "dropped"),
        protected_ids={"kept"},
        contradictions=[],
        discovered=(),
        representative_ids=("kept",),
        competing=False,
        reading_index=2,
        deepenings_remaining=1,
        per_call=10,
        limits=[],
    )
    examined = fitted.payload["examined"]
    discovered = fitted.payload["discovered_not_examined"]

    assert [row["source_id"] for row in examined] == ["kept"]
    assert "TEXTE-ECARTE" not in json.dumps(fitted.payload, ensure_ascii=False)
    assert discovered[0]["source_id"] == "dropped"
    assert discovered[0]["disposition"] == "discovered_not_examined"
    assert fitted.omitted_ids == ("dropped",)
    assert not any(row.get("reduced") or row.get("text_withheld") for row in examined)

    withheld = _fit_call(
        snapshot,
        examined_ids=("small", "large"),
        protected_ids={"small", "large"},
        contradictions=[{"subject_key": "frequentation", "item_id": "large"}],
        discovered=(),
        representative_ids=("small",),
        competing=False,
        reading_index=2,
        deepenings_remaining=1,
        per_call=10,
        limits=[],
    )
    sent = json.dumps(withheld.payload, ensure_ascii=False)

    assert "LONG-TEXT" not in sent
    assert "PETIT-TEXTE" in sent
    assert "large" not in {row.get("source_id") for row in withheld.payload["examined"]}
    assert withheld.withheld_ids == ("large",)
    assert "large" in withheld.omitted_ids
    assert not any(row.get("reduced") for row in withheld.payload["examined"])


def _copy(source_id: str, text: str) -> PeriodCopy:
    return PeriodCopy(
        source_id=source_id,
        category="signal",
        pole="frequentation",
        role="periode",
        title=source_id,
        start=PERIOD_START,
        end=PERIOD_END,
        payload={"source_id": source_id, "title": source_id, "structured_summary": text},
    )


def _snapshot(copies: tuple[PeriodCopy, ...]) -> PeriodSnapshot:
    return PeriodSnapshot(
        capture_at=datetime(2026, 4, 1, 12, tzinfo=PARIS),
        period_start=PERIOD_START,
        period_end=PERIOD_END,
        reporting={"source_id": "reporting-1", "measures": []},
        series=(),
        objectives=(),
        copies=copies,
        index=(),
        omissions=(),
    )


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


def test_outside_the_menu_does_not_query_the_database(settings):
    world = _world(settings, "hors-menu")
    provider = ScriptedProvider(
        lambda step, payload, analysis_id: _reading(deepening=_open("sql_query"))
    )
    with CaptureQueriesContext(connection) as queries:
        refused = _run(world["analysis"], provider)
    sql = "\n".join(query["sql"] for query in queries.captured_queries)

    assert [call["step"] for call in provider.calls] == ["lecture:1"]
    assert refused.code == "outside_menu"
    assert refused.semantic_readings == 1
    assert Signal._meta.db_table not in sql


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


def test_seasonal_window_copies_the_subject_year_and_keeps_the_contradiction(settings):
    kept = {}

    def prepare(context):
        kept["signal"] = _historical_signal(
            context["establishment"],
            title="Saison passée",
            summary="SAISON-CONSERVE",
            created_at=_at(date(2025, 3, 6)),
            business_unit=context["room"].affected_business_unit,
        )
        kept["outside"] = _historical_signal(
            context["establishment"],
            title="Hors fenêtre",
            summary="HORS-FENETRE",
            created_at=_at(date(2025, 3, 2)),
            business_unit=context["room"].affected_business_unit,
        )
        other = create_establishment(name="Autre saison", timezone="Europe/Paris")
        other_unit = create_business_unit(
            establishment=other,
            key="autre-saison",
            label="Restauration",
        )
        kept["foreign"] = _historical_signal(
            other,
            title="Autre établissement",
            summary="AUTRE-ETABLISSEMENT",
            created_at=_at(date(2025, 3, 6)),
            business_unit=other_unit,
        )

    world = _world(settings, "saison", before_capture=prepare)
    housing_id = str(world["housing"].id)

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            return _reading(
                contradictions=[
                    {
                        "subject_key": "frequentation",
                        "item_id": housing_id,
                        "note": "Autre pôle sur les mêmes dates.",
                    }
                ],
                deepening=_open("seasonal_window"),
            )
        sent = json.dumps(payload, ensure_ascii=False)
        assert "SAISON-CONSERVE" in sent
        assert "HORS-FENETRE" not in sent
        assert "AUTRE-ETABLISSEMENT" not in sent
        assert "PISTE-HEBERGEMENT" in sent
        assert any(row["item_id"] == housing_id for row in payload["contradictions"])
        opened = next(
            row for row in payload["examined"] if row.get("source_id") == str(kept["signal"].id)
        )
        assert opened["role"] == "saison"
        return _reading(
            contradictions=[
                {
                    "subject_key": "frequentation",
                    "item_id": housing_id,
                    "note": "La contradiction reste jusqu'à la conclusion.",
                }
            ]
        )

    provider = ScriptedProvider(handle)
    with CaptureQueriesContext(connection) as queries:
        outcome = _run(world["analysis"], provider)
    sql = "\n".join(query["sql"] for query in queries.captured_queries)
    conclusion = json.dumps(provider.calls[-1]["payload"], ensure_ascii=False)

    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:2"]
    assert outcome.semantic_readings == 2
    assert outcome.published is False
    assert "PISTE-HEBERGEMENT" in conclusion
    assert any(row["item_id"] == housing_id for row in outcome.contradictions)
    assert "SAISON-CONSERVE" in _blob(world["analysis"])
    assert "HORS-FENETRE" not in _blob(world["analysis"])
    assert Observation._meta.db_table not in sql
    assert Comment._meta.db_table not in sql


def test_a_modified_historical_signal_is_excluded_and_blocks_the_affirmative(settings):
    def prepare(context):
        _historical_signal(
            context["establishment"],
            title="Saison modifiée",
            summary="SAISON-AVANT",
            created_at=_at(date(2025, 3, 6)),
            business_unit=context["room"].affected_business_unit,
        )

    world = _world(settings, "saison-modifiee", before_capture=prepare)
    historical = Signal.objects.get(structured_summary="SAISON-AVANT")
    historical.structured_summary = "APRES-SAISON-MODIFIEE"
    historical.save(update_fields=["structured_summary", "updated_at"])
    world["room"].structured_summary = "APRES-PERIODE"
    world["room"].save(update_fields=["structured_summary", "updated_at"])

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            return _reading(deepening=_open("seasonal_window"))
        if step == "lecture:2":
            reporting_id = payload["reporting"]["source_id"]
            return _reading(cause="established", evidence=(reporting_id,))
        return _reading()

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider)
    sent = json.dumps([call["payload"] for call in provider.calls], ensure_ascii=False)
    stored = BrainSearchRun.objects.get(
        dossier__analysis=world["analysis"],
        code="lecture:2",
    ).criteria["output"]

    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:2", "correction:1"]
    assert "reporting_not_cause" in provider.calls[-1]["payload"]["correction"]["errors"]
    assert stored["subjects"][0]["cause"] == "unknown"
    assert "APRES-SAISON-MODIFIEE" not in sent
    assert "APRES-SAISON-MODIFIEE" not in _blob(world["analysis"])
    assert "SAISON-AVANT" not in sent
    assert "PREUVE-SALLE" in _blob(world["analysis"])
    assert "APRES-PERIODE" not in _blob(world["analysis"])
    assert any(row["code"] == "modified_after_capture" for row in outcome.limits)
    assert outcome.qualification == "factual_reading"
    assert outcome.investigation_succeeded is False
    assert outcome.published is False


def test_activity_sample_stays_on_the_named_subject(settings):
    box = {}

    def prepare(context):
        from houston.testing.taxonomy import create_activity_subject

        restaurant = context["room"].affected_business_unit
        lunch = create_activity_subject(
            establishment=context["establishment"],
            business_unit=restaurant,
            label="Déjeuner",
        )
        spa = create_activity_subject(
            establishment=context["establishment"],
            business_unit=restaurant,
            label="Spa",
        )
        context["room"].activity_subject = lunch
        context["room"].save(update_fields=["activity_subject", "updated_at"])
        box["same"] = _historical_signal(
            context["establishment"],
            title="Même sujet",
            summary="MEME-SUJET",
            created_at=_at(date(2025, 6, 2)),
            business_unit=restaurant,
            activity_subject=lunch,
        )
        box["other"] = _historical_signal(
            context["establishment"],
            title="Autre sujet",
            summary="AUTRE-SUJET",
            created_at=_at(date(2025, 6, 3)),
            business_unit=restaurant,
            activity_subject=spa,
        )

    world = _world(settings, "activite", before_capture=prepare)

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            request = _open("activity_subject_sample")
            request["activity_subject"] = "Déjeuner"
            return _reading(deepening=request)
        sent = json.dumps(payload, ensure_ascii=False)
        assert "MEME-SUJET" in sent
        assert "AUTRE-SUJET" not in sent
        opened = next(
            row for row in payload["examined"] if row.get("source_id") == str(box["same"].id)
        )
        assert opened["role"] == "echantillon_activite"
        return _reading()

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider)

    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:2"]
    assert outcome.treatment == "completed"
    assert "AUTRE-SUJET" not in _blob(world["analysis"])

    unknown = _world(settings, "activite-inconnue")
    outsider = ScriptedProvider(
        lambda step, payload, analysis_id: _reading(
            deepening={**_open("activity_subject_sample"), "activity_subject": "Inconnu"}
        )
    )
    with CaptureQueriesContext(connection) as queries:
        refused = _run(unknown["analysis"], outsider)
    sql = "\n".join(query["sql"] for query in queries.captured_queries)
    assert refused.code == "unknown_activity_subject"
    assert [call["step"] for call in outsider.calls] == ["lecture:1"]
    assert Signal._meta.db_table not in sql


def test_completed_analysis_memory_is_not_evidence(settings):
    box = {}

    def prepare(context):
        box["prior"] = _prior_analysis(
            context["establishment"],
            context["owner"],
            context["reporting"],
            key=f"memoire-{context['analysis'].id}",
            created_at=_at(date(2025, 1, 15)),
            result={
                "schema_version": "brain_analysis_v1",
                "subjects": [
                    {
                        "key": "frequentation",
                        "statement": "HYPOTHESE-ANCIENNE sur la fréquentation.",
                        "interpretation": "HYPOTHESE-ANCIENNE reste une hypothèse.",
                        "orientation": "INVESTIGATION",
                        "limits": ["LIMITE-ANCIENNE"],
                        "raw_text": RAW_OBSERVATION,
                    }
                ],
                "limits": [{"code": "ancien", "message": "LIMITE-DOSSIER"}],
            },
        )
        box["edited"] = _prior_analysis(
            context["establishment"],
            context["owner"],
            context["reporting"],
            key=f"memoire-modifiee-{context['analysis'].id}",
            created_at=_at(date(2025, 2, 15)),
            result={
                "schema_version": "brain_analysis_v1",
                "subjects": [
                    {
                        "key": "frequentation",
                        "statement": "ANCIEN-MODIFIE",
                        "interpretation": "ANCIEN-MODIFIE",
                        "orientation": "NO_ACTION",
                        "limits": [],
                    }
                ],
            },
        )
        _prior_analysis(
            context["establishment"],
            context["owner"],
            context["reporting"],
            key=f"memoire-echouee-{context['analysis'].id}",
            created_at=_at(date(2025, 2, 20)),
            status=BrainAnalysis.Status.FAILED,
            result={
                "schema_version": "brain_analysis_v1",
                "subjects": [{"statement": "MEMOIRE-ECHOUEE", "key": "x"}],
            },
        )
        other = create_establishment(name="Autre mémoire", timezone="Europe/Paris")
        other_owner = create_membership(
            establishment=other,
            role=EstablishmentMembership.Role.OWNER,
        )
        other_reporting = _reporting(other, other_owner, f"autre-{context['analysis'].id}")
        _prior_analysis(
            other,
            other_owner,
            other_reporting,
            key="memoire-autre",
            created_at=_at(date(2025, 1, 20)),
            result={
                "schema_version": "brain_analysis_v1",
                "subjects": [{"statement": "MEMOIRE-AUTRE", "key": "x"}],
            },
        )

    world = _world(settings, "memoire", before_capture=prepare)
    box["edited"].result = {
        "schema_version": "brain_analysis_v1",
        "subjects": [{"key": "frequentation", "statement": "APRES-MEMOIRE"}],
    }
    box["edited"].save(update_fields=["result", "updated_at"])

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            return _reading(deepening=_open("completed_analysis_memory"))
        if step == "lecture:2":
            sent = json.dumps(payload, ensure_ascii=False)
            memory = payload["memory"]
            assert any(row["source_id"] == str(box["prior"].id) for row in memory)
            assert all(row["not_evidence"] is True for row in memory)
            assert "HYPOTHESE-ANCIENNE" in sent
            assert "LIMITE-ANCIENNE" in sent
            assert "APRES-MEMOIRE" not in sent
            assert "ANCIEN-MODIFIE" not in sent
            assert "MEMOIRE-AUTRE" not in sent
            assert "MEMOIRE-ECHOUEE" not in sent
            assert "raw_text" not in sent
            assert RAW_OBSERVATION not in sent
            assert str(box["prior"].id) not in {row.get("source_id") for row in payload["examined"]}
            return _reading(cause="established", evidence=(str(box["prior"].id),))
        return _reading()

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider)
    stored = BrainSearchRun.objects.get(
        dossier__analysis=world["analysis"],
        code="lecture:2",
    ).criteria["output"]

    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:2", "correction:1"]
    assert "memory_not_evidence" in provider.calls[2]["payload"]["correction"]["errors"]
    assert outcome.treatment == "completed"
    assert outcome.corrections == 1
    assert str(box["prior"].id) not in stored["subjects"][0]["evidence_ids"]
    assert "APRES-MEMOIRE" not in _blob(world["analysis"])
    assert outcome.published is False


def test_a_recorded_search_reloads_without_the_live_row(settings):
    def prepare(context):
        _historical_signal(
            context["establishment"],
            title="Saison reprise",
            summary="SAISON-REPRISE",
            created_at=_at(date(2025, 3, 6)),
            business_unit=context["room"].affected_business_unit,
        )

    world = _world(settings, "reprise-saison", before_capture=prepare)
    failed = {"pending": True}

    def handle(step, payload, analysis_id):
        if step == "lecture:2" and failed["pending"]:
            failed["pending"] = False
            return None
        if step == "lecture:1":
            return _reading(deepening=_open("seasonal_window"))
        return _reading()

    provider = ScriptedProvider(handle)
    interrupted = _run(world["analysis"], provider)
    historical = Signal.objects.get(structured_summary="SAISON-REPRISE")
    historical.structured_summary = "APRES-REPRISE"
    historical.save(update_fields=["structured_summary", "updated_at"])
    with CaptureQueriesContext(connection) as queries:
        resumed = _run(world["analysis"], provider)
    sql = "\n".join(query["sql"] for query in queries.captured_queries)
    searches = BrainSearchRun.objects.filter(
        dossier__analysis=world["analysis"],
        code="approfondissement:1:seasonal_window",
    )

    assert interrupted.treatment == "interrupted"
    assert interrupted.replay_step == "lecture:2"
    assert interrupted.semantic_readings == 1
    assert resumed.semantic_readings == 2
    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:2", "lecture:2"]
    assert "SAISON-REPRISE" in json.dumps(provider.calls[-1]["payload"], ensure_ascii=False)
    assert "APRES-REPRISE" not in json.dumps(provider.calls[-1]["payload"], ensure_ascii=False)
    assert searches.count() == 1
    assert Signal._meta.db_table not in sql
    assert Observation._meta.db_table not in sql


def test_sample_ceilings_leave_the_extra_row_out(settings, monkeypatch):
    def prepare(context):
        unit = context["room"].affected_business_unit
        _historical_signal(
            context["establishment"],
            title="Saison une",
            summary="SAISON-GARDER",
            created_at=_at(date(2025, 3, 5)),
            business_unit=unit,
        )
        _historical_signal(
            context["establishment"],
            title="Saison deux",
            summary="SAISON-ECARTER",
            created_at=_at(date(2025, 3, 6)),
            business_unit=unit,
        )

    world = _world(settings, "plafond-saison", before_capture=prepare)
    configuration = dict(world["analysis"].configuration)
    ceilings = dict(configuration["ceilings"])
    ceilings["max_candidates_per_category"] = 1
    configuration["ceilings"] = ceilings
    world["analysis"].configuration = configuration
    world["analysis"].save(update_fields=["configuration", "updated_at"])

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            return _reading(deepening=_open("seasonal_window"))
        sent = json.dumps(payload, ensure_ascii=False)
        assert "SAISON-GARDER" in sent
        assert "SAISON-ECARTER" not in sent
        assert any(row["code"] == "seasonal_truncated" for row in payload["limits"])
        return _reading()

    outcome = _run(world["analysis"], ScriptedProvider(handle))
    assert outcome.semantic_readings == 2
    assert any(row["code"] == "seasonal_truncated" for row in outcome.limits)

    box = {}

    def prepare_activity(context):
        from houston.testing.taxonomy import create_activity_subject

        unit = context["room"].affected_business_unit
        subject = create_activity_subject(
            establishment=context["establishment"],
            business_unit=unit,
            label="Déjeuner",
        )
        context["room"].activity_subject = subject
        context["room"].save(update_fields=["activity_subject", "updated_at"])
        box["older"] = _historical_signal(
            context["establishment"],
            title="Ancien déjeuner",
            summary="ECHANTILLON-ANCIEN",
            created_at=_at(date(2025, 5, 1)),
            business_unit=unit,
            activity_subject=subject,
        )
        box["newer"] = _historical_signal(
            context["establishment"],
            title="Récent déjeuner",
            summary="ECHANTILLON-RECENT",
            created_at=_at(date(2025, 6, 1)),
            business_unit=unit,
            activity_subject=subject,
        )

    monkeypatch.setattr("houston.brain.deepening.ACTIVITY_SAMPLE_LIMIT", 1)
    sampled = _world(settings, "plafond-activite", before_capture=prepare_activity)

    def handle_activity(step, payload, analysis_id):
        if step == "lecture:1":
            request = _open("activity_subject_sample")
            request["activity_subject"] = "Déjeuner"
            return _reading(deepening=request)
        sent = json.dumps(payload, ensure_ascii=False)
        assert "ECHANTILLON-RECENT" in sent
        assert "ECHANTILLON-ANCIEN" not in sent
        assert any(row["code"] == "sample_truncated" for row in payload["limits"])
        return _reading()

    sampled_outcome = _run(sampled["analysis"], ScriptedProvider(handle_activity))
    assert sampled_outcome.semantic_readings == 2
    assert any(row["code"] == "sample_truncated" for row in sampled_outcome.limits)


def test_continuous_seasonal_requests_stop_after_two_openings(settings):
    world = _world(settings, "plafond-saison-boucle")

    def handle(step, payload, analysis_id):
        return _reading(deepening=_open("seasonal_window"))

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider)
    codes = {
        row.code: row.criteria.get("code")
        for row in BrainSearchRun.objects.filter(dossier__analysis=world["analysis"])
    }
    searches = [
        row.code
        for row in BrainSearchRun.objects.filter(dossier__analysis=world["analysis"])
        if row.code.startswith("approfondissement:")
    ]

    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:2", "lecture:3"]
    assert outcome.semantic_readings == 3
    assert outcome.provider_calls == 3
    assert outcome.code == "deepen_budget_exhausted"
    assert codes["decision:3"] == "deepen_budget_exhausted"
    assert sorted(searches) == [
        "approfondissement:1:seasonal_window",
        "approfondissement:2:seasonal_window",
    ]
    assert any(row["code"] == "seasonal_window_empty" for row in outcome.limits)


def _historical_signal(
    establishment,
    *,
    title,
    summary,
    created_at,
    business_unit,
    activity_subject=None,
):
    signal = _signal(
        establishment,
        title=title,
        summary=summary,
        created_at=created_at,
        business_unit=business_unit,
    )
    signal.status = Signal.Status.RESOLVED
    signal.resolved_at = created_at
    if activity_subject is not None:
        signal.activity_subject = activity_subject
    signal.save(update_fields=["status", "resolved_at", "activity_subject", "updated_at"])
    Signal.objects.filter(pk=signal.pk).update(
        created_at=created_at,
        updated_at=created_at,
        resolved_at=created_at,
        last_activity_at=created_at,
    )
    signal.refresh_from_db()
    return signal


def _prior_analysis(
    establishment,
    owner,
    reporting,
    *,
    key,
    created_at,
    result,
    status=BrainAnalysis.Status.COMPLETED,
):
    row = BrainAnalysis.objects.create(
        establishment=establishment,
        reporting=reporting,
        author=owner.user,
        idempotency_key=key,
        status=status,
        configuration={"schema_version": "brain_analysis_v1"},
        result=result,
        published_at=created_at,
    )
    BrainAnalysis.objects.filter(pk=row.pk).update(
        created_at=created_at,
        updated_at=created_at,
        published_at=created_at,
    )
    row.refresh_from_db()
    return row


def _replace_measures(reporting) -> None:
    extraction = BrainExtraction.objects.get(reporting=reporting)
    extraction.payload = {
        "measures": [
            {
                "label": "frequentation",
                "value": "100",
                "value_kind": "number",
                "unit": "couvert",
                "scope": "Restauration",
            },
            {
                "label": "frequentation",
                "value": "80",
                "value_kind": "number",
                "unit": "couvert",
                "scope": "Restauration",
                "period": "N-1",
            },
        ],
        "qualitative": [{"kind": "paragraph", "text": "Baisse de frequentation en salle."}],
    }
    extraction.save(update_fields=["payload", "updated_at"])


def _gap(cause: str = "unknown", evidence: tuple[str, ...] = ()) -> dict:
    return {
        "schema_version": "brain_investigation_v3",
        "subjects": [
            {
                "key": "frequentation",
                "movement": "degradation",
                "statement": "La fréquentation passe de 100 à 80 couverts.",
                "examined": True,
                "cause": cause,
                "evidence_ids": list(evidence),
                "contradiction_ids": [],
                "reported_facts": [],
                "explanations": [],
                "decisive_checks": [],
                "findings": [
                    {
                        "kind": "arithmetic",
                        "text": "Écart mesuré sur la même définition.",
                        "item_ids": ["measure:0", "measure:1"],
                    }
                ],
                "calculations": [
                    {
                        "operation": "variation",
                        "role": "gap",
                        "comparison": "temporal",
                        "label": "frequentation",
                        "operands": [
                            {"item_id": "measure:0", "value": "100", "unit": "couvert"},
                            {"item_id": "measure:1", "value": "80", "unit": "couvert"},
                        ],
                        "published_value": "-0.2",
                        "unit": "",
                    }
                ],
                "breakdowns": [],
                "tradeoffs": [],
                "orientation": "NO_ACTION",
                "justification": "L'écart est mesuré. Aucune cause opérationnelle ne l'est.",
                "does_not_promise": "",
                "limits": [
                    {
                        "text": "La cause opérationnelle n'est pas établie.",
                        "effect": "blocks_cause",
                        "item_ids": [],
                    }
                ],
            }
        ],
        "contradictions": [],
        "deepening": None,
    }


def test_an_unread_seasonal_copy_keeps_its_period_and_an_independent_gap(settings, monkeypatch):
    def prepare(context):
        _replace_measures(context["reporting"])
        created_at = _at(date(2025, 3, 6))
        signal = _signal(
            context["establishment"],
            title="Saison ouverte",
            summary="SAISON-OUVERTE",
            created_at=created_at,
            business_unit=context["room"].affected_business_unit,
        )
        signal.status = Signal.Status.RESOLVED
        signal.save(update_fields=["status", "updated_at"])
        Signal.objects.filter(pk=signal.pk).update(updated_at=created_at)
        SignalLifecycleEvent.objects.create(
            signal=signal,
            establishment=context["establishment"],
            event_type=SignalLifecycleEvent.EventType.CREATED,
            occurred_at=_at(date(2025, 3, 6)),
            metadata_safe={},
        )

    world = _world(settings, "saison-non-lue", before_capture=prepare)

    def costly(payload):
        examined = payload.get("examined") or []
        if any(row.get("role") == "saison" for row in examined):
            return 10**9
        return 100

    monkeypatch.setattr("houston.brain.orchestration.investigation_call_tokens", costly)

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            return {**_gap(), "deepening": _open("seasonal_window")}
        return _gap()

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider)
    snapshot = reload_period_dossier(world["analysis"].id)
    seasonal = next(item for item in snapshot.copies if item.role == "saison")
    capture_on = snapshot.capture_at.astimezone(PARIS).date()

    assert [call["step"] for call in provider.calls] == ["lecture:1"]
    assert seasonal.source_id in outcome.discovered_not_examined
    assert outcome.qualification == "partial"
    assert outcome.investigation_succeeded is True
    assert outcome.code == "budget_exceeded"
    assert seasonal.payload["events"][0]["role"] == "anterieur"
    assert seasonal.end == capture_on
    assert seasonal.end != date(2025, 3, 8)


def test_an_unscoped_exclusion_blocks_the_cause_and_keeps_the_gap(settings):
    def prepare(context):
        _replace_measures(context["reporting"])
        _historical_signal(
            context["establishment"],
            title="Saison sans sujet",
            summary="SAISON-SANS-SUJET",
            created_at=_at(date(2025, 3, 6)),
            business_unit=context["room"].affected_business_unit,
        )

    world = _world(settings, "exclusion-sans-sujet", before_capture=prepare)
    historical = Signal.objects.get(structured_summary="SAISON-SANS-SUJET")
    historical.structured_summary = "APRES-SANS-SUJET"
    historical.save(update_fields=["structured_summary", "updated_at"])
    opening = _open("seasonal_window")
    opening["subject_key"] = ""

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            return {**_gap(), "deepening": opening}
        if step == "lecture:2":
            reporting_id = payload["reporting"]["source_id"]
            return _gap(cause="established", evidence=(reporting_id,))
        return _gap()

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider)
    stored = BrainSearchRun.objects.get(
        dossier__analysis=world["analysis"],
        code="lecture:2",
    ).criteria["output"]

    assert [call["step"] for call in provider.calls] == ["lecture:1", "lecture:2", "correction:1"]
    assert "reporting_not_cause" in provider.calls[-1]["payload"]["correction"]["errors"]
    assert stored["subjects"][0]["cause"] == "unknown"
    assert outcome.qualification == "partial"
    assert outcome.investigation_succeeded is True
    assert any(row["code"] == "modified_after_capture" for row in outcome.limits)


def test_an_unscoped_exclusion_still_qualifies_an_independent_gap(settings):
    def prepare(context):
        _replace_measures(context["reporting"])
        _historical_signal(
            context["establishment"],
            title="Saison calcul",
            summary="SAISON-CALCUL",
            created_at=_at(date(2025, 3, 6)),
            business_unit=context["room"].affected_business_unit,
        )

    world = _world(settings, "exclusion-calcul", before_capture=prepare)
    historical = Signal.objects.get(structured_summary="SAISON-CALCUL")
    historical.structured_summary = "APRES-CALCUL"
    historical.save(update_fields=["structured_summary", "updated_at"])
    opening = _open("seasonal_window")
    opening["subject_key"] = ""

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            return {**_gap(), "deepening": opening}
        return _gap()

    outcome = _run(world["analysis"], ScriptedProvider(handle))

    assert any(row["code"] == "modified_after_capture" for row in outcome.limits)
    assert outcome.qualification == "partial"
    assert outcome.investigation_succeeded is True


def test_an_accepted_correction_without_its_lecture_row_resumes(settings):
    world = _world(settings, "reprise-correction")
    dossier = BrainDossier.objects.get(analysis=world["analysis"])
    record = {
        "input_hash": "stored",
        "input_tokens": 10,
        "payload": {},
        "output": _reading(),
        "examined_ids": [],
        "full_text_ids": [],
        "withheld_ids": [],
        "discovered_not_examined": [],
        "representative_ids": [],
    }
    BrainSearchRun.objects.create(
        dossier=dossier,
        code="correction:1",
        criteria={
            "accepted": True,
            "reading_index": 1,
            "reading": record,
            "errors": ["response_invalid"],
            "input_tokens": 10,
        },
        examined_count=1,
        retained_count=0,
    )
    provider = ScriptedProvider(lambda step, payload, analysis_id: _reading())
    outcome = _run(world["analysis"], provider)

    assert provider.calls == []
    assert outcome.semantic_readings == 1
    assert outcome.corrections == 1
    assert outcome.qualification == "factual_reading"
    assert outcome.treatment == "completed"


def test_a_rejected_correction_without_a_stop_does_not_consume_the_budget(settings):
    world = _world(settings, "correction-orpheline")
    dossier = BrainDossier.objects.get(analysis=world["analysis"])
    BrainSearchRun.objects.create(
        dossier=dossier,
        code="correction:1",
        criteria={"accepted": False, "errors": ["response_invalid"], "input_tokens": 10},
        examined_count=1,
        retained_count=0,
    )

    def handle(step, payload, analysis_id):
        if step == "lecture:1":
            return {"schema_version": "nope"}
        return _reading()

    provider = ScriptedProvider(handle)
    outcome = _run(world["analysis"], provider)

    assert [call["step"] for call in provider.calls] == ["lecture:1", "correction:1"]
    assert outcome.treatment == "completed"
    assert outcome.corrections == 1
