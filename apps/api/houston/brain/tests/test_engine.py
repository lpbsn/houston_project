"""Scripted provider tests for the autonomous engine.

The provider chooses searches. The backend only seals copies, pages them,
and checks the structure of the restitution.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta
from django.db import connection
from django.db.models import Case, DateTimeField, Value, When
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from houston.action_plans.models import ActionPlan, ActionPlanExecution
from houston.brain.admission import admit_brain_work
from houston.brain.capture import capture_investigation_dossier
from houston.brain.engine import (
    MAX_DISTINCT_COPIES,
    EngineToolCall,
    EngineTurn,
    _message_tokens,
    mechanisms_within_budget,
    metier_prompt,
    run_engine,
)
from houston.brain.errors import BrainWorkError
from houston.brain.models import (
    BrainAnalysis,
    BrainDossierItem,
    BrainExtraction,
    BrainKnowledgeVersion,
    BrainMechanismCandidate,
    BrainObjectiveEvaluation,
    BrainReporting,
    BrainSuggestion,
)
from houston.brain.objectives import record_objective_revision
from houston.brain.records import EXTRACTOR_ID, EXTRACTOR_VERSION
from houston.brain.runtime import _complete, claim_analysis
from houston.establishments.models import EstablishmentActivityDescription, EstablishmentMembership
from houston.observations.models import Observation
from houston.signals.models import Signal, SignalSourceObservation
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_activity_subject, create_business_unit

pytestmark = pytest.mark.django_db(transaction=True)

PARIS = ZoneInfo("Europe/Paris")
PROMPT_SOURCE = (
    Path(__file__).resolve().parents[5]
    / "docs"
    / "cadrage"
    / "SPORE_Brain_Prompt_Metier_v7_1_REVISE.md"
)


class ScriptedProvider:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def complete(self, *, analysis_id, messages, tools, timeout_seconds):
        self.calls.append(
            {
                "analysis_id": analysis_id,
                "messages": messages,
                "tools": tools,
                "timeout": timeout_seconds,
            }
        )
        return self.handler(messages, tools)


def test_packaged_prompt_is_the_validated_text():
    assert metier_prompt() == PROMPT_SOURCE.read_text(encoding="utf-8")
    assert metier_prompt().startswith("# SPORE Brain — Prompt métier v7")


def test_mechanism_budget_keeps_a_fitting_prefix_and_counts_the_rest():
    short = {"identifier": "a", "formulation": "court"}
    huge = {"identifier": "z", "formulation": "x" * 20_000}

    def render(selected):
        return [
            {
                "role": "user",
                "content": {
                    "mechanisms": selected,
                    "mechanisms_omitted": 2 - len(selected),
                },
            }
        ]

    ceiling = _message_tokens(render([short]), [], "fake", "fake")
    kept, omitted = mechanisms_within_budget(
        [short, huge],
        render=render,
        ceiling=ceiling,
        provider="fake",
        model="fake",
        tools=[],
    )
    assert [item["identifier"] for item in kept] == ["a"]
    assert omitted == 1


def test_search_reaches_another_pole_and_ignores_a_later_live_edit():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    kitchen = create_business_unit(
        establishment=establishment, key="cuisine_engine", label="Cuisine"
    )
    bar = create_business_unit(establishment=establishment, key="bar_engine", label="Bar")
    _signal(
        establishment,
        title="Fuite cuisine",
        summary="Fuite sous l'évier.",
        created_at=_at(period_start),
        business_unit=kitchen,
    )
    bar_signal = _signal(
        establishment,
        title="Verre cassé",
        summary="Verre au bar.",
        created_at=_at(period_start + timedelta(days=1)),
        business_unit=bar,
    )
    analysis = _analysis(owner, reporting)

    def handler(messages, tools):
        del tools
        if len(provider.calls) == 1:
            return _search(period_start, period_end, pole="Bar")
        rows = messages[-1]["content"]["rows"]
        assert [row["title"] for row in rows] == ["Verre cassé"]
        assert rows[0]["structured_summary"] == "Verre au bar."
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)
    Signal.objects.filter(pk=bar_signal.id).update(title="TITRE-VIVANT")
    again = ScriptedProvider(
        lambda messages, tools: (_ for _ in ()).throw(AssertionError("replay"))
    )
    result = run_engine(analysis.id, again)
    assert again.calls == []
    assert result["qualification"] == "not_publishable"
    assert provider.calls[0]["messages"][0]["content"] == metier_prompt()
    assert provider.calls[0]["timeout"] == 90


def test_next_page_uses_the_cursor_and_reports_the_full_match_count():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    unit = create_business_unit(establishment=establishment, key="salle_engine", label="Salle")
    for index in range(11):
        _signal(
            establishment,
            title=f"Signal {index:02d}",
            summary="Résumé structuré.",
            created_at=_at(period_start) + timedelta(hours=index),
            business_unit=unit,
        )
    analysis = _analysis(owner, reporting)

    def handler(messages, tools):
        del tools
        turn = len(provider.calls)
        if turn == 1:
            return _search(period_start, period_end)
        page = messages[-1]["content"]
        if turn == 2:
            assert page["match_count"] == 11
            assert page["returned_count"] == 10
            assert page["next_cursor"] == "10"
            return _search(period_start, period_end, cursor=page["next_cursor"])
        assert page["match_count"] == 11
        assert page["returned_count"] == 1
        assert page["rows"][0]["title"] == "Signal 10"
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)


def test_historical_window_is_distinct_from_the_reporting_period():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    unit = create_business_unit(establishment=establishment, key="hist_engine", label="Hall")
    old_start = period_start - relativedelta(years=1)
    _signal(
        establishment,
        title="Incident ancien",
        summary=f"Survenu le {old_start.isoformat()} dans le hall.",
        created_at=_at(old_start),
        business_unit=unit,
    )
    _signal(
        establishment,
        title="Incident courant",
        summary="Survenu pendant le reporting.",
        created_at=_at(period_start),
        business_unit=unit,
    )
    analysis = _analysis(owner, reporting)
    old_end = old_start + relativedelta(months=1)

    def handler(messages, tools):
        del tools
        turn = len(provider.calls)
        if turn == 1:
            return _search(old_start, old_end, basis="occurrence")
        if turn == 2:
            titles = [row["title"] for row in messages[-1]["content"]["rows"]]
            assert titles == ["Incident ancien"]
            return _search(period_start, period_end, basis="declaration")
        titles = [row["title"] for row in messages[-1]["content"]["rows"]]
        assert titles == ["Incident courant"]
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)


def test_incomplete_capture_is_unavailable_not_an_empty_business_result():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    unit = create_business_unit(establishment=establishment, key="cap_engine", label="Cave")
    _signal(
        establishment,
        title="Premier",
        summary="Un.",
        created_at=_at(period_start),
        business_unit=unit,
    )
    _signal(
        establishment,
        title="Second",
        summary="Deux.",
        created_at=_at(period_start + timedelta(days=1)),
        business_unit=unit,
    )
    analysis = _analysis(owner, reporting)
    _set_ceiling(analysis, 1)

    def handler(messages, tools):
        del tools
        if len(provider.calls) == 1:
            return _search(period_start, period_end)
        page = messages[-1]["content"]
        assert page["availability"] == "available"
        assert page["match_count"] == 1
        assert [row["title"] for row in page["rows"]] == ["Second"]
        assert page["capture_omitted"] == 1
        assert page["empty_means"] is None
        assert "absence" in page["note"]
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)


def test_observation_text_is_absent_and_status_without_journal_is_unavailable():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    unit = create_business_unit(establishment=establishment, key="obs_engine", label="Etage")
    signal = _signal(
        establishment,
        title="Ampoule grillée",
        summary="Couloir du premier.",
        created_at=_at(period_start),
        business_unit=unit,
        status=Signal.Status.RESOLVED,
    )
    observation = Observation.objects.create(
        establishment=establishment,
        submitted_by_membership=owner,
        raw_text="OBSERVATION-BRUTE-INTERDITE",
        client_submission_id=uuid.uuid4(),
        submitted_at=timezone.now(),
    )
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    analysis = _analysis(owner, reporting)

    def handler(messages, tools):
        del tools
        if len(provider.calls) == 1:
            return _search(period_start, period_end)
        row = messages[-1]["content"]["rows"][0]
        assert row["status_at_window"] == {
            "availability": "unavailable",
            "reason": "history_unreliable",
        }
        assert "resolved" not in json.dumps(row)
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)
    blob = json.dumps(
        [item.payload for item in BrainDossierItem.objects.filter(dossier__analysis=analysis)],
        ensure_ascii=False,
        default=str,
    )
    assert "OBSERVATION-BRUTE-INTERDITE" not in blob
    assert "OBSERVATION-BRUTE-INTERDITE" not in json.dumps(provider.calls, default=str)


def test_prior_reporting_and_memory_are_marked_and_searchable():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(
        period_start,
        period_end,
        measures=[_measure("Chiffre d'affaires", "100", "2025-03-01", "2025-04-01")],
    )
    prior_start = period_start - relativedelta(years=1)
    prior_end = period_end - relativedelta(years=1)
    prior = _store_reporting(
        establishment,
        owner.user,
        prior_start,
        prior_end,
        measures=[
            _measure("Chiffre d'affaires", "80", prior_start.isoformat(), prior_end.isoformat())
        ],
    )
    BrainAnalysis.objects.create(
        establishment=establishment,
        reporting=prior,
        author=owner.user,
        idempotency_key="memoire-anterieure",
        status=BrainAnalysis.Status.COMPLETED,
        published_at=timezone.now() - timedelta(days=2),
        configuration={"ceilings": {}},
        result={"summary": "MEMOIRE-DECISION-UNIQUE"},
    )
    analysis = _analysis(owner, reporting)

    def handler(messages, tools):
        del tools
        turn = len(provider.calls)
        if turn == 1:
            return EngineTurn(
                tool_calls=(
                    EngineToolCall(
                        "search_reportings",
                        {
                            "window_start": prior_start.isoformat(),
                            "window_end": prior_end.isoformat(),
                        },
                    ),
                )
            )
        if turn == 2:
            row = messages[-1]["content"]["rows"][0]
            assert row["source_kind"] == "document"
            assert row["label"] == "Chiffre d'affaires"
            assert row["value"] == "80"
            return EngineTurn(tool_calls=(EngineToolCall("search_memory", {}),))
        row = messages[-1]["content"]["rows"][0]
        assert row["source_kind"] == "decision_memory"
        assert row["result"]["summary"] == "MEMOIRE-DECISION-UNIQUE"
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)


def test_active_mechanisms_are_sealed_into_the_context():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    EstablishmentActivityDescription.objects.create(
        establishment=establishment,
        description="Hôtel de centre-ville.",
    )
    BrainKnowledgeVersion.objects.create(
        identifier="alpha",
        global_formulation="FORMULATION-ALPHA",
        conditions="Quand le taux baisse.",
        approved_at=timezone.now() - timedelta(days=1),
        activated_at=timezone.now() - timedelta(days=1),
        is_active=True,
    )
    BrainKnowledgeVersion.objects.create(
        identifier="beta",
        global_formulation="FORMULATION-BETA",
        conditions="Quand le panier change.",
        approved_at=timezone.now() - timedelta(days=1),
        activated_at=timezone.now() - timedelta(days=1),
        is_active=True,
    )
    analysis = _analysis(owner, reporting)

    def handler(messages, tools):
        del tools
        context = messages[2]["content"]
        assert {item["formulation"] for item in context["mechanisms"]} == {
            "FORMULATION-ALPHA",
            "FORMULATION-BETA",
        }
        assert context["mechanisms_omitted"] == 0
        assert context["activity_description"]["text"] == "Hôtel de centre-ville."
        if len(provider.calls) == 1:
            BrainKnowledgeVersion.objects.filter(identifier="alpha").update(is_active=False)
            return EngineTurn(restitution={"subjects": [], "anchors": []})
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)
    # One restitution finishes the run. Rebuild from the sealed dossier still has both.
    stored = json.dumps(provider.calls[0]["messages"][2]["content"], ensure_ascii=False)
    assert "FORMULATION-ALPHA" in stored
    assert "FORMULATION-BETA" in stored


def test_resume_rebuilds_the_dialogue_from_the_sealed_copy():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    unit = create_business_unit(establishment=establishment, key="reprise_engine", label="Spa")
    signal = _signal(
        establishment,
        title="TITRE-SCELLE",
        summary="Résumé scellé.",
        created_at=_at(period_start),
        business_unit=unit,
    )
    analysis = _analysis(owner, reporting)

    def first(messages, tools):
        del messages, tools
        if len(first_provider.calls) == 1:
            return _search(period_start, period_end)
        raise BrainWorkError(code="provider_unavailable", message="Coupure après la recherche.")

    first_provider = ScriptedProvider(first)
    with pytest.raises(BrainWorkError):
        run_engine(analysis.id, first_provider)
    Signal.objects.filter(pk=signal.id).update(
        title="TITRE-VIVANT",
        structured_summary="résumé vivant",
    )
    analysis.refresh_from_db()
    assert len(analysis.trace) == 1
    assert analysis.trace[0]["tool"] == "search_signals"
    assert analysis.result is None

    def second(messages, tools):
        del tools
        blob = json.dumps(messages, ensure_ascii=False)
        assert "TITRE-SCELLE" in blob
        assert "TITRE-VIVANT" not in blob
        assert messages[0]["content"] == metier_prompt()
        assert messages[1]["role"] == "format"
        assert messages[3]["role"] == "assistant"
        assert messages[4]["role"] == "tool"
        return EngineTurn(restitution={})

    second_provider = ScriptedProvider(second)
    run_engine(analysis.id, second_provider)
    assert len(second_provider.calls) == 1


def test_omitted_anchor_blocks_complete_and_a_bad_figure_drops_only_itself():
    period_start, period_end = _period()
    measures = [
        _measure("Chiffre d'affaires", "100", "2025-03-01", "2025-04-01"),
        _measure("Couverture froid", "4", "2025-03-01", "2025-04-01"),
    ]
    establishment, owner, reporting = _reporting_bundle(
        period_start,
        period_end,
        measures=measures,
        qualitative=[{"kind": "paragraph", "text": "Travaux en salle."}],
    )
    unit = create_business_unit(
        establishment=establishment, key="preuve_engine", label="Restaurant"
    )
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=unit,
        label="Service",
    )
    _signal(
        establishment,
        title="Service ralenti",
        summary="File en salle.",
        created_at=_at(period_start),
        business_unit=unit,
        activity=subject,
    )
    _signal(
        establishment,
        title="Livraison tardive",
        summary="Le fournisseur est arrivé après le service.",
        created_at=_at(period_start + timedelta(days=2)),
        business_unit=unit,
        activity=subject,
    )
    analysis = _analysis(owner, reporting)
    state = {}

    def handler(messages, tools):
        del tools
        if len(provider.calls) == 1:
            return _search(period_start, period_end)
        rows = {row["title"]: row["item_id"] for row in messages[-1]["content"]["rows"]}
        anchors = messages[2]["content"]["reporting"]
        state["rows"] = rows
        state["anchors"] = anchors
        cited = next(
            anchor["anchor_id"]
            for anchor in anchors
            if anchor["label"] == "Chiffre d'affaires"
        )
        return EngineTurn(
            restitution={
                "subjects": [
                    _subject(
                        "voisin",
                        evidence=[rows["Livraison tardive"]],
                        figures=[{"source": "measure", "item_id": cited}],
                    ),
                    _subject(
                        "chiffre-hors-reference",
                        evidence=[rows["Service ralenti"]],
                        figures=[{"source": "measure", "item_id": "pas-une-copie"}],
                    ),
                ],
                "anchors": [
                    {
                        "anchor_id": anchor["anchor_id"],
                        "disposition": "attached",
                        "subject_key": "voisin",
                    }
                    for anchor in anchors
                    if anchor["kind"] != "qualitative"
                ],
            }
        )

    provider = ScriptedProvider(handler)
    result = run_engine(analysis.id, provider)
    by_key = {subject["key"]: subject for subject in result["subjects"]}
    assert set(by_key) == {"voisin", "chiffre-hors-reference"}
    assert by_key["chiffre-hors-reference"]["figures"] == []
    assert by_key["voisin"]["figures"][0]["value"] == "100"
    assert result["qualification"] == "partial"
    assert any(
        isinstance(limit, dict) and limit.get("code") == "anchor_undisposed"
        for limit in result["limits"]
    )
    assert "Travaux en salle." not in json.dumps(result["limits"], ensure_ascii=False)


def test_compare_or_signal_without_a_contribution_mark_is_not_publishable():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(
        period_start,
        period_end,
        measures=[
            _measure("Chiffre d'affaires salle", "80", "2024-01-01", "2024-02-01", scope="Salle"),
            _measure("Chiffre d'affaires salle", "100", "2025-01-01", "2025-02-01", scope="Salle"),
        ],
    )
    unit = create_business_unit(establishment=establishment, key="marque_engine", label="Salle")
    _signal(
        establishment,
        title="Promotion midi",
        summary="Beaucoup de formules.",
        created_at=_at(period_start),
        business_unit=unit,
    )
    analysis = _analysis(owner, reporting)

    def handler(messages, tools):
        del tools
        turn = len(provider.calls)
        anchors = messages[2]["content"]["reporting"]
        if turn == 1:
            return EngineTurn(
                tool_calls=(
                    EngineToolCall(
                        "compare",
                        {
                            "left_item_id": anchors[0]["item_id"],
                            "right_item_id": anchors[1]["item_id"],
                            "kind": "temporal",
                        },
                    ),
                )
            )
        if turn == 2:
            assert messages[-1]["content"]["compare"]["accepted"] is True
            return _search(period_start, period_end)
        signal_id = messages[-1]["content"]["rows"][0]["item_id"]
        return EngineTurn(
            restitution={
                "subjects": [
                    _subject("signal-sans-marque", evidence=[signal_id], contribution=False),
                    _subject(
                        "reporting-seul",
                        evidence=[anchor["anchor_id"] for anchor in anchors],
                        contribution=True,
                    ),
                ],
                "anchors": [
                    {
                        "anchor_id": anchor["anchor_id"],
                        "disposition": "not_significant",
                    }
                    for anchor in anchors
                ],
            }
        )

    provider = ScriptedProvider(handler)
    result = run_engine(analysis.id, provider)
    assert result["qualification"] == "not_publishable"
    assert all(subject["contribution"] is False for subject in result["subjects"])


def test_accepted_compare_keeps_a_neighbor_and_writes_drafts_from_sealed_measures():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(
        period_start,
        period_end,
        measures=[
            _measure("Chiffre d'affaires salle", "80", "2024-01-01", "2024-02-01", scope="Salle"),
            _measure("Chiffre d'affaires salle", "100", "2025-01-01", "2025-02-01", scope="Salle"),
            _measure(
                "Couverture froid",
                "12",
                period_start.isoformat(),
                period_end.isoformat(),
                unit="EUR",
            ),
        ],
    )
    record_objective_revision(
        establishment=establishment,
        indicator="Couverture froid",
        unit="EUR",
        target="10",
        success_condition="gte",
        decision="accepted",
    )
    plan = ActionPlan.objects.create(
        establishment=establishment,
        created_by=owner,
        pilot_business_unit=create_business_unit(
            establishment=establishment, key="draft_engine", label="Maintenance"
        ),
        title="Plan déjà ouvert",
        description="Contrôle des chambres froides.",
        is_reusable=False,
    )
    ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=establishment,
        created_by=owner,
        title="Contrôle mensuel",
        description="Relever les températures.",
        pilot_business_unit=plan.pilot_business_unit,
        requires_validation=False,
        last_activity_at=_at(period_start),
        use_shared_chronology=True,
        start_at=_at(period_start),
        end_at=_at(period_start + timedelta(days=1)),
    )
    analysis = _analysis(owner, reporting)
    state = {}

    def handler(messages, tools):
        del tools
        anchors = messages[2]["content"]["reporting"]
        revenue = [anchor for anchor in anchors if anchor["label"] == "Chiffre d'affaires salle"]
        if len(provider.calls) == 1:
            return EngineTurn(
                tool_calls=(
                    EngineToolCall(
                        "compare",
                        {
                            "left_item_id": revenue[0]["item_id"],
                            "right_item_id": revenue[1]["item_id"],
                            "kind": "temporal",
                        },
                    ),
                )
            )
        compare = messages[-1]["content"]["compare"]
        assert compare["accepted"] is True
        assert compare["difference"] in {"20", "-20"}
        state["difference"] = compare["difference"]
        return EngineTurn(
            restitution={
                "subjects": [
                    _subject(
                        "evolution",
                        evidence=[anchor["anchor_id"] for anchor in revenue],
                        compare_ids=[compare["compare_id"]],
                        figures=[
                            {"source": "compare", "compare_id": compare["compare_id"]},
                            {"source": "measure", "item_id": "figure-inconnue"},
                        ],
                    )
                ],
                "anchors": [
                    {
                        "anchor_id": anchor["anchor_id"],
                        "disposition": "attached",
                        "subject_key": "evolution",
                    }
                    for anchor in anchors
                ],
                "proposals": {
                    "suggestions": [
                        {
                            "key": "froid",
                            "title": "Relever les températures",
                            "description": "Chaque matin.",
                        }
                    ],
                    "objectives": [
                        {"key": "suivi", "indicator": "Couverture froid", "target": "14"}
                    ],
                    "mechanisms": [
                        {
                            "key": "substitution",
                            "formulation": "Une promotion peut remplacer une vente plus rentable.",
                            "conditions": "Quand le mix change.",
                            "limits": "Pas une preuve locale.",
                            "uncertainty": "À vérifier.",
                        }
                    ],
                },
            }
        )

    provider = ScriptedProvider(handler)
    token = analysis.attempt_token
    assert claim_analysis(analysis.id, token)
    result = run_engine(analysis.id, provider)
    assert _complete(analysis.id, token, result)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert result["qualification"] == "complete"
    subject = result["subjects"][0]
    assert subject["contribution"] is True
    assert subject["figures"][0]["difference"] == state["difference"]
    assert all(figure.get("item_id") != "figure-inconnue" for figure in subject["figures"])
    assert BrainSuggestion.objects.filter(analysis=analysis, stable_key="froid").exists()
    evaluation = BrainObjectiveEvaluation.objects.get(analysis=analysis)
    assert evaluation.outcome == BrainObjectiveEvaluation.Outcome.REACHED
    assert evaluation.measure["value"] == "12"
    candidate = BrainMechanismCandidate.objects.get(analysis=analysis, stable_key="substitution")
    assert candidate.status == BrainMechanismCandidate.Status.CANDIDATE
    assert result["proposals"]["objectives"][0]["target"] == "14"


def test_a_compare_of_other_measures_does_not_support_the_finding():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(
        period_start,
        period_end,
        measures=[
            _measure("Chiffre d'affaires salle", "80", "2024-01-01", "2024-02-01", scope="Salle"),
            _measure("Chiffre d'affaires salle", "100", "2025-01-01", "2025-02-01", scope="Salle"),
            _measure("Couvert", "10", "2024-01-01", "2024-02-01", scope="Salle"),
            _measure("Couvert", "12", "2025-01-01", "2025-02-01", scope="Salle"),
        ],
    )
    analysis = _analysis(owner, reporting)
    state = {}

    def handler(messages, tools):
        del tools
        anchors = messages[2]["content"]["reporting"]
        revenue = [anchor for anchor in anchors if anchor["label"] == "Chiffre d'affaires salle"]
        covers = [anchor for anchor in anchors if anchor["label"] == "Couvert"]
        if len(provider.calls) == 1:
            return EngineTurn(
                tool_calls=(
                    EngineToolCall(
                        "compare",
                        {
                            "left_item_id": revenue[0]["item_id"],
                            "right_item_id": revenue[1]["item_id"],
                            "kind": "temporal",
                        },
                    ),
                    EngineToolCall(
                        "compare",
                        {
                            "left_item_id": covers[0]["item_id"],
                            "right_item_id": covers[1]["item_id"],
                            "kind": "temporal",
                        },
                    ),
                )
            )
        compares = [
            message["content"]["compare"]
            for message in messages
            if message.get("role") == "tool"
            and isinstance(message.get("content"), dict)
            and message["content"].get("compare")
        ]
        revenue_compare = next(
            compare
            for compare in compares
            if {compare["left_item_id"], compare["right_item_id"]}
            == {revenue[0]["item_id"], revenue[1]["item_id"]}
        )
        state["revenue_compare_id"] = revenue_compare["compare_id"]
        return EngineTurn(
            restitution={
                "subjects": [
                    _subject(
                        "couvert",
                        evidence=[anchor["anchor_id"] for anchor in covers],
                        compare_ids=[revenue_compare["compare_id"]],
                        figures=[
                            {"source": "compare", "compare_id": revenue_compare["compare_id"]}
                        ],
                    )
                ],
                "anchors": [
                    {
                        "anchor_id": anchor["anchor_id"],
                        "disposition": "not_significant",
                    }
                    for anchor in anchors
                ],
            }
        )

    provider = ScriptedProvider(handler)
    result = run_engine(analysis.id, provider)
    subject = result["subjects"][0]
    assert subject["contribution"] is False
    assert subject["figures"][0]["compare_id"] == state["revenue_compare_id"]
    assert result["qualification"] == "not_publishable"


def test_search_actions_filters_and_returns_sealed_evidence():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    kitchen = create_business_unit(
        establishment=establishment, key="cuisine_actions", label="Cuisine"
    )
    bar = create_business_unit(establishment=establishment, key="bar_actions", label="Bar")
    service = create_activity_subject(
        establishment=establishment, business_unit=kitchen, label="Service"
    )
    plonge = create_activity_subject(
        establishment=establishment, business_unit=kitchen, label="Plonge"
    )
    cold = _plan(
        establishment,
        owner,
        kitchen,
        title="Contrôle froid",
        description="Relever les températures du matin.",
        created_at=_at(period_start),
        activity=service,
    )
    probe = _execution(
        cold,
        owner,
        title="Relève du matin",
        description="Sonder les bacs.",
        created_at=_at(period_start - relativedelta(years=1)),
        start_at=_at(period_start + timedelta(days=1)),
        end_at=_at(period_start + timedelta(days=1, hours=1)),
        activity=service,
    )
    _plan(
        establishment,
        owner,
        kitchen,
        title="Fond de plonge",
        description="Vider les bacs.",
        created_at=_at(period_start + timedelta(days=2)),
        activity=plonge,
    )
    _plan(
        establishment,
        owner,
        bar,
        title="Verre du bar",
        description="Remplacer le verre.",
        created_at=_at(period_start),
    )
    _plan(
        establishment,
        owner,
        kitchen,
        title="Ancien contrôle",
        description="Campagne de l'an dernier.",
        created_at=_at(period_start - relativedelta(years=1)),
        activity=service,
    )
    analysis = _analysis(owner, reporting)

    def handler(messages, tools):
        del tools
        turn = len(provider.calls)
        if turn == 1:
            return _action_search(period_start, period_end, pole="Cuisine", activity="Service")
        page = messages[-1]["content"]
        if turn == 2:
            assert page["availability"] == "available"
            assert page["match_count"] == 2
            by_title = {row["title"]: row for row in page["rows"]}
            assert set(by_title) == {"Contrôle froid", "Relève du matin"}
            plan_row = by_title["Contrôle froid"]
            execution_row = by_title["Relève du matin"]
            assert plan_row["description"] == "Relever les températures du matin."
            assert plan_row["pilot_business_unit"]["name"] == "Cuisine"
            assert plan_row["activity_subject"]["label"] == "Service"
            assert plan_row["links_complete"] is True
            assert str(probe.id) in plan_row["execution_ids"]
            assert execution_row["source_kind"] == "execution"
            assert execution_row["description"] == "Sonder les bacs."
            assert execution_row["action_plan_id"] == str(cold.id)
            assert execution_row["start_at"] is not None
            return _action_search(
                period_start,
                period_end,
                pole="Cuisine",
                activity="Service",
                text="températures",
            )
        if turn == 3:
            assert [row["title"] for row in page["rows"]] == ["Contrôle froid"]
            return _action_search(
                period_start,
                period_end,
                kind="execution",
                pole="Cuisine",
                activity="Service",
            )
        assert [row["title"] for row in page["rows"]] == ["Relève du matin"]
        assert page["rows"][0]["source_kind"] == "execution"
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)


def test_action_window_follows_establishment_time_and_an_open_interval():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    kitchen = create_business_unit(
        establishment=establishment, key="cuisine_fenetre", label="Cuisine"
    )
    paris = ZoneInfo("Europe/Paris")
    night = datetime(2026, 1, 15, 0, 30, tzinfo=paris)
    night_plan = _plan(
        establishment,
        owner,
        kitchen,
        title="Plan de nuit",
        description="Hors fenêtre.",
        created_at=night - timedelta(days=3),
    )
    _execution(
        night_plan,
        owner,
        title="Service après minuit",
        description="Fermeture après minuit.",
        created_at=night,
        start_at=night,
        end_at=night + timedelta(hours=1),
    )
    opened = _at(period_start - timedelta(days=20))
    closed = _at(period_end + timedelta(days=5))
    span_plan = _plan(
        establishment,
        owner,
        kitchen,
        title="Plan long",
        description="Ouvert avant la période.",
        created_at=opened,
    )
    _execution(
        span_plan,
        owner,
        title="Exécution couvrante",
        description="Commence avant et finit après.",
        created_at=opened,
        start_at=opened,
        end_at=closed,
    )
    analysis = _analysis(owner, reporting)
    night_start = night.date()
    previous_day = night_start - timedelta(days=1)

    def handler(messages, tools):
        del tools
        turn = len(provider.calls)
        if turn == 1:
            return _action_search(night_start, night_start + timedelta(days=1), kind="execution")
        page = messages[-1]["content"]
        if turn == 2:
            assert [row["title"] for row in page["rows"]] == ["Service après minuit"]
            return _action_search(previous_day, night_start, kind="execution")
        if turn == 3:
            assert page["rows"] == []
            assert page["match_count"] == 0
            return _action_search(period_start, period_end, kind="execution")
        assert [row["title"] for row in page["rows"]] == ["Exécution couvrante"]
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)


def test_search_objectives_keeps_accepted_revisions_and_measure_references():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(
        period_start,
        period_end,
        measures=[
            _measure(
                "Couverture froid",
                "12",
                period_start.isoformat(),
                period_end.isoformat(),
                unit="EUR",
            )
        ],
    )
    record_objective_revision(
        establishment=establishment,
        indicator="Couverture froid",
        unit="EUR",
        target="10",
        success_condition="gte",
        decision="accepted",
        measurement_period_start=period_start,
        measurement_period_end=period_end,
    )
    superseded = record_objective_revision(
        establishment=establishment,
        indicator="Ancien nom",
        unit="EUR",
        target="1",
        success_condition="gte",
        decision="accepted",
        measurement_period_start=period_start,
        measurement_period_end=period_end,
    )
    record_objective_revision(
        establishment=establishment,
        objective=superseded.objective,
        indicator="Nom courant",
        unit="EUR",
        target="2",
        success_condition="gte",
        decision="modified",
        measurement_period_start=period_start,
        measurement_period_end=period_end,
    )
    record_objective_revision(
        establishment=establishment,
        indicator="Occupation",
        unit="EUR",
        target="80",
        success_condition="gte",
        decision="accepted",
        measurement_period_start=period_start - relativedelta(years=1),
        measurement_period_end=period_end - relativedelta(years=1),
    )
    record_objective_revision(
        establishment=establishment,
        indicator="Hygiène",
        success_condition="qualitative",
        decision="accepted",
    )
    record_objective_revision(
        establishment=establishment,
        indicator="Publicité",
        unit="EUR",
        target="1",
        success_condition="gte",
        decision="refused",
        measurement_period_start=period_start,
        measurement_period_end=period_end,
    )
    withdrawn = record_objective_revision(
        establishment=establishment,
        indicator="Menu retiré",
        unit="EUR",
        target="5",
        success_condition="gte",
        decision="accepted",
        measurement_period_start=period_start,
        measurement_period_end=period_end,
    )
    record_objective_revision(
        establishment=establishment,
        objective=withdrawn.objective,
        indicator="Menu retiré",
        unit="EUR",
        target="5",
        success_condition="gte",
        decision="refused",
        measurement_period_start=period_start,
        measurement_period_end=period_end,
    )
    record_objective_revision(
        establishment=establishment,
        indicator="Brouillon",
        unit="EUR",
        target="1",
        success_condition="gte",
        decision="recorded",
        measurement_period_start=period_start,
        measurement_period_end=period_end,
    )
    analysis = _analysis(owner, reporting)

    def handler(messages, tools):
        del tools
        if len(provider.calls) == 1:
            return _objective_search(period_start, period_end)
        page = messages[-1]["content"]
        rows = {row["indicator"]: row for row in page["rows"]}
        assert set(rows) == {"Couverture froid", "Nom courant"}
        assert page["omitted_without_measurement_period"] == 1
        assert rows["Couverture froid"]["decision"] == "accepted"
        assert rows["Nom courant"]["decision"] == "modified"
        reading = rows["Couverture froid"]["numeric_result"]
        assert reading["outcome"] == BrainObjectiveEvaluation.Outcome.REACHED
        assert reading["measure"]["value"] == "12"
        measure = BrainDossierItem.objects.get(
            dossier__analysis=analysis,
            category="document",
            role="mesure",
            payload__label="Couverture froid",
        )
        assert reading["measure"]["item_id"] == str(measure.id)
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)


def test_activity_filter_combines_with_pole_and_period():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    kitchen = create_business_unit(
        establishment=establishment, key="cuisine_filtre", label="Cuisine"
    )
    bar = create_business_unit(establishment=establishment, key="bar_filtre", label="Bar")
    service = create_activity_subject(
        establishment=establishment, business_unit=kitchen, label="Service"
    )
    plonge = create_activity_subject(
        establishment=establishment, business_unit=kitchen, label="Plonge"
    )
    _signal(
        establishment,
        title="Service cuisine",
        summary="Retard en salle.",
        created_at=_at(period_start),
        business_unit=kitchen,
        activity=service,
    )
    _signal(
        establishment,
        title="Plonge cuisine",
        summary="Bac bouché.",
        created_at=_at(period_start + timedelta(days=1)),
        business_unit=kitchen,
        activity=plonge,
    )
    _signal(
        establishment,
        title="Service bar",
        summary="Verre cassé.",
        created_at=_at(period_start),
        business_unit=bar,
        activity=service,
    )
    _signal(
        establishment,
        title="Service ancien",
        summary="L'an dernier.",
        created_at=_at(period_start - relativedelta(years=1)),
        business_unit=kitchen,
        activity=service,
    )
    analysis = _analysis(owner, reporting)

    def handler(messages, tools):
        del tools
        if len(provider.calls) == 1:
            return _search(
                period_start,
                period_end,
                pole="Cuisine",
                activity="Service",
            )
        assert [row["title"] for row in messages[-1]["content"]["rows"]] == ["Service cuisine"]
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)


def test_copy_budget_counts_distinct_sources_and_stops_explicitly():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    unit = create_business_unit(establishment=establishment, key="copies_engine", label="Hall")
    total = MAX_DISTINCT_COPIES + 5
    for index in range(total):
        _signal(
            establishment,
            title=f"Copie {index:02d}",
            summary="Source distincte.",
            created_at=_at(period_start) + timedelta(minutes=index),
            business_unit=unit,
        )
    analysis = _analysis(owner, reporting)
    seen = []

    def handler(messages, tools):
        del tools
        if len(provider.calls) == 1:
            return _search(period_start, period_end)
        page = messages[-1]["content"]
        if page.get("truncation") == "copy_budget":
            assert page["match_count"] == total
            assert page["returned_count"] == 0
            assert page["next_cursor"] == str(MAX_DISTINCT_COPIES)
            assert "tronquée" in page["note"]
            assert len(seen) == MAX_DISTINCT_COPIES
            return _search(period_start, period_end, cursor="0")
        if seen and page["rows"] and page["rows"][0]["title"] == "Copie 00":
            assert [row["item_id"] for row in page["rows"]] == seen[:10]
            assert page["truncation"] == ""
            return EngineTurn(restitution={})
        seen.extend(row["item_id"] for row in page["rows"])
        assert page["match_count"] == total
        assert page["returned_count"] == 10
        return _search(period_start, period_end, cursor=page["next_cursor"])

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)
    assert len(provider.calls) <= 8
    assert len(set(seen)) == MAX_DISTINCT_COPIES


def test_busy_history_capture_stays_complete_and_bounded():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    kitchen = create_business_unit(
        establishment=establishment, key="cuisine_volume", label="Cuisine"
    )
    service = create_activity_subject(
        establishment=establishment, business_unit=kitchen, label="Service"
    )
    old_day = period_start - relativedelta(years=1)
    _bulk_signals(
        establishment,
        kitchen,
        [
            (
                f"Historique {index:03d}",
                "Antérieur à la période.",
                _at(old_day) + timedelta(hours=index),
            )
            for index in range(240)
        ],
        activity=service,
    )
    _signal(
        establishment,
        title="Service du mois",
        summary="Retard du service courant.",
        created_at=_at(period_start),
        business_unit=kitchen,
        activity=service,
    )
    for index in range(8):
        plan = _plan(
            establishment,
            owner,
            kitchen,
            title=f"Plan {index:02d}",
            description="Contrôle périodique.",
            created_at=_at(period_start) + timedelta(minutes=index),
            activity=service,
        )
        _execution(
            plan,
            owner,
            title=f"Exécution {index:02d}",
            description="Fait pendant la période.",
            created_at=_at(period_start) + timedelta(minutes=index),
            start_at=_at(period_start) + timedelta(minutes=index),
            end_at=_at(period_start) + timedelta(minutes=index, hours=1),
            activity=service,
        )
    analysis = _analysis(owner, reporting)
    started = time.monotonic()
    with CaptureQueriesContext(connection) as captured:
        capture_investigation_dossier(analysis.id)
    elapsed = time.monotonic() - started
    coverage = BrainDossierItem.objects.get(dossier__analysis=analysis, category="coverage")
    assert coverage.payload["families"]["signal"]["complete"] is True
    assert coverage.payload["families"]["signal"]["captured"] == 241
    assert coverage.payload["families"]["plan"]["complete"] is True
    assert coverage.payload["families"]["execution"]["complete"] is True
    assert len(captured) < coverage.payload["families"]["signal"]["captured"]
    assert elapsed < 15

    def handler(messages, tools):
        del tools
        if len(provider.calls) == 1:
            return _search(period_start, period_end, pole="Cuisine", activity="Service")
        page = messages[-1]["content"]
        assert page["availability"] == "available"
        assert page["match_count"] == 1
        assert page["rows"][0]["title"] == "Service du mois"
        return _action_search(period_start, period_end, pole="Cuisine", activity="Service")

    provider = ScriptedProvider(handler)

    def finish(messages, tools):
        if len(provider.calls) < 3:
            return handler(messages, tools)
        page = messages[-1]["content"]
        assert page["match_count"] == 16
        assert page["availability"] == "available"
        return EngineTurn(restitution={})

    provider.handler = finish
    run_engine(analysis.id, provider)


def test_history_beyond_the_ceiling_still_serves_the_current_period():
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    kitchen = create_business_unit(
        establishment=establishment, key="cuisine_plafond", label="Cuisine"
    )
    service = create_activity_subject(
        establishment=establishment, business_unit=kitchen, label="Service"
    )
    old_day = period_start - relativedelta(years=1)
    _bulk_signals(
        establishment,
        kitchen,
        [
            (f"Ancien {index:02d}", "Hors période.", _at(old_day) + timedelta(hours=index))
            for index in range(30)
        ]
        + [
            (
                f"Récent {index:02d}",
                "Dans la période.",
                _at(period_start) + timedelta(hours=index),
            )
            for index in range(6)
        ],
        activity=service,
    )
    analysis = _analysis(owner, reporting)
    _set_ceiling(analysis, 10)

    def handler(messages, tools):
        del tools
        turn = len(provider.calls)
        if turn == 1:
            return _search(period_start, period_end, pole="Cuisine", activity="Service")
        page = messages[-1]["content"]
        if turn == 2:
            assert page["availability"] == "available"
            assert [row["title"] for row in page["rows"]] == [
                f"Récent {index:02d}" for index in range(6)
            ]
            assert page["match_count"] == 6
            assert page["capture_omitted"] == 26
            return _search(
                old_day,
                old_day + timedelta(days=40),
                pole="Cuisine",
                activity="Service",
            )
        assert page["availability"] == "available"
        assert page["match_count"] == 4
        assert page["capture_omitted"] == 26
        assert page["empty_means"] is None
        assert "absence" in page["note"]
        assert all(row["title"].startswith("Ancien") for row in page["rows"])
        assert "Ancien 00" not in {row["title"] for row in page["rows"]}
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_engine(analysis.id, provider)


def _search(start, end, *, pole="", activity="", basis="declaration", cursor=None):
    arguments = {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "temporal_basis": basis,
    }
    if pole:
        arguments["pole"] = pole
    if activity:
        arguments["activity"] = activity
    if cursor:
        arguments["cursor"] = cursor
    return EngineTurn(tool_calls=(EngineToolCall("search_signals", arguments),))


def _action_search(start, end, *, kind="all", pole="", activity="", text="", cursor=None):
    arguments = {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "kind": kind,
    }
    if pole:
        arguments["pole"] = pole
    if activity:
        arguments["activity"] = activity
    if text:
        arguments["text"] = text
    if cursor:
        arguments["cursor"] = cursor
    return EngineTurn(tool_calls=(EngineToolCall("search_actions", arguments),))


def _objective_search(start, end, *, text=""):
    arguments = {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
    }
    if text:
        arguments["text"] = text
    return EngineTurn(tool_calls=(EngineToolCall("search_objectives", arguments),))


def _plan(establishment, owner, unit, *, title, description, created_at, activity=None):
    plan = ActionPlan.objects.create(
        establishment=establishment,
        created_by=owner,
        pilot_business_unit=unit,
        activity_subject=activity,
        title=title,
        description=description,
        is_reusable=False,
    )
    ActionPlan.objects.filter(pk=plan.pk).update(created_at=created_at)
    plan.refresh_from_db()
    return plan


def _execution(
    plan,
    owner,
    *,
    title,
    description,
    created_at,
    start_at,
    end_at,
    activity=None,
):
    execution = ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=plan.establishment,
        created_by=owner,
        title=title,
        description=description,
        pilot_business_unit=plan.pilot_business_unit,
        activity_subject=activity,
        requires_validation=False,
        last_activity_at=created_at,
        use_shared_chronology=True,
        start_at=start_at,
        end_at=end_at,
    )
    ActionPlanExecution.objects.filter(pk=execution.pk).update(
        created_at=created_at,
        last_activity_at=created_at,
    )
    execution.refresh_from_db()
    return execution


def _bulk_signals(establishment, business_unit, specs, *, activity=None):
    pending = [
        Signal(
            establishment=establishment,
            affected_business_unit=business_unit,
            activity_subject=activity,
            routing_status=Signal.RoutingStatus.RESOLVED,
            title=title,
            structured_summary=summary,
            issue_focus=f"focus-{uuid.uuid4().hex[:12]}",
            last_activity_at=created_at,
            status=Signal.Status.OPEN,
        )
        for title, summary, created_at in specs
    ]
    created = Signal.objects.bulk_create(pending, batch_size=200)
    for offset in range(0, len(created), 100):
        batch = list(zip(created[offset : offset + 100], specs[offset : offset + 100], strict=True))
        Signal.objects.filter(pk__in=[row.pk for row, _spec in batch]).update(
            created_at=Case(
                *[When(pk=row.pk, then=Value(spec[2])) for row, spec in batch],
                output_field=DateTimeField(),
            ),
            last_activity_at=Case(
                *[When(pk=row.pk, then=Value(spec[2])) for row, spec in batch],
                output_field=DateTimeField(),
            ),
        )


def _subject(key, *, evidence, contribution=True, figures=None, compare_ids=None):
    return {
        "key": key,
        "significant": True,
        "examined": True,
        "contribution": contribution,
        "epistemic_status": "constat",
        "statement": f"Constat {key}.",
        "evidence_ids": evidence,
        "compare_ids": compare_ids or [],
        "decisive_contradiction_unexamined": False,
        "figures": figures or [],
    }


def _measure(label, value, start, end, *, scope="Etablissement", unit="EUR"):
    return {
        "label": label,
        "value": value,
        "value_kind": "number",
        "unit": unit,
        "definition": label,
        "scope": scope,
        "period": f"{start} {end}",
    }


def _period():
    today = timezone.now().astimezone(PARIS).date()
    period_end = today.replace(day=1)
    period_start = period_end - relativedelta(months=1)
    return period_start, period_end


def _at(day):
    return datetime.combine(day, datetime.min.time(), tzinfo=PARIS) + timedelta(hours=12)


def _reporting_bundle(period_start, period_end, *, measures=None, qualitative=None):
    establishment = create_establishment(
        name=f"Moteur {uuid.uuid4().hex[:8]}",
        timezone="Europe/Paris",
    )
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    reporting = _store_reporting(
        establishment,
        owner.user,
        period_start,
        period_end,
        measures=measures,
        qualitative=qualitative,
    )
    return establishment, owner, reporting


def _store_reporting(
    establishment,
    author,
    period_start,
    period_end,
    *,
    measures=None,
    qualitative=None,
):
    reporting = BrainReporting.objects.create(
        establishment=establishment,
        author=author,
        original_filename="periode.csv",
        content_type="text/csv",
        source_format=BrainReporting.SourceFormat.CSV,
        content_sha256=uuid.uuid4().hex + uuid.uuid4().hex[:32],
        storage_key=f"brain/reportings/{establishment.id}/{uuid.uuid4()}/original",
        byte_size=8,
        status=BrainReporting.Status.READY,
        period_start=period_start,
        period_end=period_end,
        period_confirmed_at=timezone.now(),
    )
    BrainExtraction.objects.create(
        reporting=reporting,
        extractor_id=EXTRACTOR_ID,
        extractor_version=EXTRACTOR_VERSION,
        source_sha256=reporting.content_sha256,
        payload={"measures": measures or [], "qualitative": qualitative or []},
    )
    return reporting


def _signal(
    establishment,
    *,
    title,
    summary,
    created_at,
    business_unit,
    status=Signal.Status.OPEN,
    activity=None,
):
    signal = Signal.objects.create(
        establishment=establishment,
        affected_business_unit=business_unit,
        activity_subject=activity,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary=summary,
        issue_focus=f"focus-{uuid.uuid4().hex[:12]}",
        last_activity_at=created_at,
        status=status,
    )
    Signal.objects.filter(pk=signal.pk).update(created_at=created_at, last_activity_at=created_at)
    signal.refresh_from_db()
    return signal


def _analysis(owner, reporting):
    return admit_brain_work(
        user=owner.user,
        establishment_id=owner.establishment_id,
        reporting_id=reporting.id,
        idempotency_key=f"demande-{uuid.uuid4().hex}",
    )


def _set_ceiling(analysis, ceiling: int):
    config = dict(analysis.configuration)
    ceilings = dict(config["ceilings"])
    ceilings["max_candidates_per_category"] = ceiling
    config["ceilings"] = ceilings
    analysis.configuration = config
    analysis.save(update_fields=["configuration", "updated_at"])
