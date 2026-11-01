"""Business regressions: aggregation detail, operational reality, isolation and snapshots."""

from __future__ import annotations

import json
import uuid
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from houston.action_plans.models import (
    ActionPlanExecutionReview,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
)
from houston.brain.capture import capture_investigation_dossier
from houston.brain.engine import EngineToolCall, EngineTurn, run_engine
from houston.brain.engine_tools import SealedView, execute_tool, render_tool_result
from houston.brain.terrain_evidence import collect_terrain_evidence
from houston.brain.tests.test_engine import (
    ScriptedProvider,
    _analysis,
    _at,
    _execution,
    _period,
    _plan,
    _reporting_bundle,
    _set_ceiling,
    _signal,
)
from houston.comments.models import Comment
from houston.observations.models import Observation
from houston.signals.models import CandidateSignal, SignalSourceObservation
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def terrain():
    start, end = _period()
    site, owner, reporting = _reporting_bundle(start, end)
    unit = create_business_unit(establishment=site, key="terrain", label="Restaurant")
    signal = _signal(
        site,
        title="Service lent",
        summary="Attente au déjeuner.",
        created_at=_at(start),
        business_unit=unit,
    )
    plan = _plan(
        site,
        owner,
        unit,
        title="Réorganiser le déjeuner",
        description="Renforcer la prise de commande.",
        created_at=_at(start),
    )
    execution = _execution(
        plan,
        owner,
        title=plan.title,
        description=plan.description,
        created_at=_at(start),
        start_at=_at(start),
        end_at=_at(end),
    )
    team = ActionPlanExecutionTeam.objects.create(
        action_plan_execution=execution, business_unit=unit, is_pilot=True
    )
    return site, owner, reporting, signal, execution, team


def candidate(terrain, summary, observation=None):
    site, owner, _, signal, _, _ = terrain
    observation = observation or Observation.objects.create(
        establishment=site,
        submitted_by_membership=owner,
        raw_text="RAW_NOT_FOR_BRAIN",
        submitted_at=timezone.now(),
        client_submission_id=uuid.uuid4(),
    )
    SignalSourceObservation.objects.get_or_create(
        signal=signal,
        observation=observation,
        link_type="aggregated_from",
    )
    return CandidateSignal.objects.create(
        establishment=site,
        observation=observation,
        result_signal=signal,
        title="Renoncement aux desserts",
        structured_summary=summary,
        outcome=CandidateSignal.Outcome.AGGREGATED_SIGNAL,
        schema_version="test",
    )


def view_for(terrain, *, ceiling=None):
    _, owner, reporting, *_ = terrain
    analysis = _analysis(owner, reporting)
    if ceiling is not None:
        _set_ceiling(analysis, ceiling)
    dossier = capture_investigation_dossier(analysis.id)
    return SealedView(dossier, list(dossier.items.all()))


def search(view, **arguments):
    entry = execute_tool(
        view,
        "search_evidence",
        arguments,
        examined=set(),
        remaining_copies=40,
        consultations_remaining=10,
    )
    return render_tool_result(view, entry)


def test_aggregated_consequence_is_searchable_without_mutating_signal_or_loading_raw(terrain):
    fact = candidate(terrain, "Trois tables ont renoncé au dessert à 14 h après l’attente.")
    view = view_for(terrain)
    result = search(view, kind="observation_fact", text="dessert")
    assert result["match_count"] == 1
    assert "Trois tables" in result["rows"][0]["text"]
    assert result["rows"][0]["signal_id"] == str(terrain[3].id)
    assert result["rows"][0]["source_id"] == str(fact.id)
    terrain[3].refresh_from_db()
    assert terrain[3].structured_summary == "Attente au déjeuner."
    assert "RAW_NOT_FOR_BRAIN" not in json.dumps([i.payload for i in view.items])


def test_multiple_candidates_do_not_invent_independent_observations(terrain):
    first = candidate(terrain, "Trois tables sont parties.")
    candidate(terrain, "La salle est froide.", observation=first.observation)
    result = search(view_for(terrain), kind="observation_fact")
    assert result["match_count"] == 2
    assert len({row["event_key"] for row in result["rows"]}) == 1
    assert result["match_count_is"] == "source_details_not_independent_observations"


def test_capture_survives_source_correction_and_deletion(terrain):
    fact = candidate(terrain, "Trois tables ont renoncé au dessert.")
    view = view_for(terrain)
    before = search(view, kind="observation_fact")["rows"][0]
    fact.structured_summary = "Correction : une table."
    fact.save()
    fact.delete()
    after = search(view, kind="observation_fact")["rows"][0]
    assert before == after
    assert after["source_version"]


def test_task_skipped_and_review_are_not_kpi_results(terrain):
    _, owner, _, _, execution, team = terrain
    task = ActionPlanExecutionTask.objects.create(
        action_plan_execution=execution,
        execution_team=team,
        task="Tester deux personnes à midi",
        description="Répartir les heures sans augmenter le total.",
        position=1,
        status="skipped",
        skipped_reason="Absence du renfort",
        skipped_at=timezone.now(),
        assigned_membership=owner,
    )
    ActionPlanExecutionReview.objects.create(
        action_plan_execution=execution,
        reviewer_membership=owner,
        stars=3,
        comment="Organisation revue, effets à mesurer.",
        reviewed_at=timezone.now(),
    )
    result = search(view_for(terrain), parent_id=str(execution.id))
    task_row = next(row for row in result["rows"] if row["kind"] == "execution_task")
    review = next(row for row in result["rows"] if row["kind"] == "execution_review")
    assert task_row["source_id"] == str(task.id)
    assert task_row["status_at_capture"] == "skipped"
    assert task_row["skipped_reason"] == "Absence du renfort"
    assert task_row["assigned_to"]["membership_id"] == str(owner.id)
    assert "not_kpi_result" in task_row["epistemic_status"]
    assert "not_measured_business_effect" in review["epistemic_status"]


def test_only_plan_discussions_are_captured_and_not_validated_as_decisions(terrain):
    site, owner, _, signal, execution, _ = terrain
    Comment.objects.create(
        establishment=site,
        action_plan_execution=execution,
        author_membership=owner,
        body="Le fournisseur reporte à mardi.",
    )
    Comment.objects.create(
        establishment=site,
        signal=signal,
        author_membership=owner,
        body="SIGNAL_COMMENT_OUT_OF_SCOPE",
    )
    result = search(view_for(terrain), kind="plan_discussion")
    assert len(result["rows"]) == 1
    assert "fournisseur" in result["rows"][0]["text"]
    assert result["rows"][0]["epistemic_status"] == "reported_discussion_not_validated_decision"


def test_other_establishment_and_rejected_candidate_are_not_exposed(terrain):
    first = candidate(terrain, "Rejected content")
    first.outcome = CandidateSignal.Outcome.REJECTED
    first.save()
    start, end = _period()
    other, _, _ = _reporting_bundle(start, end)
    invalid = candidate(terrain, "OTHER_TENANT_CONTENT")
    CandidateSignal.objects.filter(pk=invalid.pk).update(establishment=other)
    result = search(view_for(terrain), kind="observation_fact")
    assert result["rows"] == []
    assert result["availability"] == "unavailable"
    assert result["empty_means"] is None


def test_omissions_are_unavailable_not_proof_of_no_evidence(terrain):
    candidate(terrain, "Rare dessert detail")
    candidate(terrain, "Recent unrelated detail")
    view = view_for(terrain, ceiling=1)
    result = search(view, kind="observation_fact", text="Rare dessert")
    assert result["availability"] == "unavailable"
    assert result["empty_means"] is None


def test_source_edits_do_not_force_live_queries_during_search(terrain):
    candidate(terrain, "Trois desserts refusés.")
    view = view_for(terrain)
    with CaptureQueriesContext(connection) as queries:
        result = search(view, kind="observation_fact")
    assert len(queries) == 0
    assert result["returned_count"] == 1


def test_queries_do_not_grow_per_candidate_and_never_load_chat_contents(terrain):
    site = terrain[0]
    candidate(terrain, "Un fait.")

    def collect():
        return collect_terrain_evidence(
            establishment_id=site.id, capture_at=timezone.now(), ceiling=100, run=lambda fn: fn()
        )

    with CaptureQueriesContext(connection) as first:
        collect()
    for _ in range(10):
        candidate(terrain, "Autre fait.")
    with CaptureQueriesContext(connection) as second:
        collect()
    assert len(first) == len(second)
    assert not any('"chat_chatmessage"' in q["sql"] for q in second.captured_queries)
    assert not any('"raw_text"' in q["sql"] for q in second.captured_queries)


def test_existing_dossier_without_evidence_is_unavailable(terrain):
    view = view_for(terrain)
    for family in (
        "observation_fact",
        "execution_task",
        "plan_discussion",
        "execution_review",
        "assignment",
    ):
        view.coverage["families"].pop(family)
    assert search(view, kind="observation_fact")["availability"] == "unavailable"


def test_evidence_is_exposed_to_engine_and_citable(terrain):
    candidate(terrain, "Trois tables ont renoncé au dessert.")
    analysis = _analysis(terrain[1], terrain[2])

    def handle(messages, tools):
        if len(provider.calls) == 1:
            assert any(t["name"] == "search_evidence" for t in tools)
            return EngineTurn(
                tool_calls=(EngineToolCall("search_evidence", {"kind": "observation_fact"}),)
            )
        row = messages[-1]["content"]["rows"][0]
        return EngineTurn(
            restitution={
                "subjects": [
                    {
                        "key": "dessert",
                        "significant": True,
                        "examined": True,
                        "contribution": True,
                        "epistemic_status": "hypothese",
                        "statement": "Le renoncement rapporté pourrait contribuer à la baisse.",
                        "evidence_ids": [row["item_id"]],
                        "figures": [],
                    }
                ],
                "anchors": [],
                "proposals": {},
            }
        )

    provider = ScriptedProvider(handle)
    result = run_engine(analysis.id, provider)
    assert result["subjects"][0]["key"] == "dessert"
    assert result["subjects"][0]["evidence_ids"]


def test_future_declarations_are_not_captured(terrain):
    fact = candidate(terrain, "FUTURE_FACT")
    Observation.objects.filter(pk=fact.observation_id).update(
        submitted_at=timezone.now() + timedelta(days=2)
    )
    assert search(view_for(terrain), kind="observation_fact")["rows"] == []


def test_source_version_does_not_change_when_capture_time_changes(terrain):
    site, _, _, _, execution, team = terrain
    ActionPlanExecutionTask.objects.create(
        action_plan_execution=execution, execution_team=team, task="Vérifier la carte", position=1
    )
    now = timezone.now()

    def collect(at):
        rows, _ = collect_terrain_evidence(
            establishment_id=site.id, capture_at=at, ceiling=100, run=lambda fn: fn()
        )
        return next(row.payload for row in rows if row.payload["kind"] == "execution_task")

    before, after = collect(now), collect(now + timedelta(seconds=10))
    assert before["as_of"] != after["as_of"]
    assert before["source_version"] == after["source_version"]


def test_public_citation_keeps_evidence_identity_and_links_to_parent(terrain):
    from houston.brain.selectors import public_sources

    candidate(terrain, "Trois tables ont renoncé au dessert.")
    view = view_for(terrain)
    evidence = next(item for item in view.items if item.category == "terrain_evidence")
    source = public_sources([evidence])[0]
    assert source["item_id"] == str(evidence.id)
    assert source["category"] == "terrain_evidence"
    assert source["locators"][0] == {"format": "spore_signal", "source_id": str(terrain[3].id)}


def test_pr359_comment_task_provenance_when_messaging_is_installed(terrain):
    if "created_task" not in {f.name for f in Comment._meta.get_fields()}:
        pytest.skip("Integration case runs when PR #359 is installed")
    site, owner, _, _, execution, team = terrain
    task = ActionPlanExecutionTask.objects.create(
        action_plan_execution=execution,
        execution_team=team,
        task="Confirmer le renfort",
        position=1,
    )
    comment = Comment.objects.create(
        establishment=site,
        action_plan_execution=execution,
        author_membership=owner,
        body="Confirmer le renfort",
        created_task=task,
        pinned_at=timezone.now(),
    )
    rows = search(view_for(terrain), parent_id=str(execution.id))["rows"]
    task_row = next(row for row in rows if row["kind"] == "execution_task")
    discussion = next(row for row in rows if row["kind"] == "plan_discussion")
    assert task_row["source_comment_id"] == str(comment.id)
    assert discussion["created_task_id"] == str(task.id)
    assert discussion["pinned_at"]
    assert "not_validated_decision" in discussion["epistemic_status"]
