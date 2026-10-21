"""One running analysis per establishment, resumed from the sealed trace."""

from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from houston.brain import runtime as brain_runtime
from houston.brain.admission import admit_brain_work
from houston.brain.engine import EngineTurn
from houston.brain.models import (
    BrainAnalysis,
    BrainDossier,
    BrainDossierItem,
    BrainKnowledgeVersion,
    BrainMechanismCandidate,
    BrainObjectiveEvaluation,
    BrainSuggestion,
)
from houston.brain.objectives import record_objective_revision
from houston.brain.provider import BrainProviderUnavailable
from houston.brain.runtime import claim_analysis, request_analysis_cancel, run_brain_analysis
from houston.brain.selectors import active_brain_work, analysis_detail, analysis_page
from houston.brain.tests.test_admission import _admit, _reporting
from houston.brain.tests.test_engine import (
    _analysis,
    _at,
    _measure,
    _period,
    _reporting_bundle,
    _search,
    _set_ceiling,
    _signal,
    _subject,
)
from houston.brain.tests.test_support import allow_publish
from houston.establishments.models import EstablishmentMembership
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db(transaction=True)


class ScriptedProvider:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def complete(self, *, analysis_id, messages, tools, timeout_seconds):
        self.calls.append({"messages": messages, "tools": tools})
        outcome = self.handler(analysis_id, messages, tools)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_same_reporting_returns_the_open_analysis_and_a_failed_one_does_not(monkeypatch):
    allow_publish(monkeypatch)
    establishment = create_establishment(name="Brain empreinte")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    reporting = _reporting(establishment, owner.user)
    first = _admit(owner.user, establishment, reporting, key="une")
    second = _admit(owner.user, establishment, reporting, key="deux")
    assert second.id == first.id
    assert first.context_fingerprint
    assert not first.configuration.get("contributions")
    first.status = BrainAnalysis.Status.FAILED
    first.failure_code = "response_invalid"
    first.save(update_fields=["status", "failure_code", "updated_at"])
    relaunch = _admit(owner.user, establishment, reporting, key="trois")
    assert relaunch.id != first.id
    replay = _admit(owner.user, establishment, reporting, key="une")
    assert replay.id == first.id


def test_a_contribution_or_a_new_mechanism_is_another_analysis(monkeypatch):
    allow_publish(monkeypatch)
    establishment = create_establishment(name="Brain apport")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    reporting = _reporting(establishment, owner.user)
    first = _admit(owner.user, establishment, reporting, key="sans-apport")
    with_note = admit_brain_work(
        user=owner.user,
        establishment_id=establishment.id,
        reporting_id=reporting.id,
        idempotency_key="avec-apport",
        contributions=[{"kind": "apport", "text": "Le chef confirme la rupture."}],
    )
    assert with_note.id != first.id
    assert with_note.configuration["contributions"] == [
        {"kind": "apport", "text": "Le chef confirme la rupture."}
    ]
    BrainKnowledgeVersion.objects.create(
        identifier="rupture-froid",
        global_formulation="Une rupture de froid dégrade le service.",
        conditions="Quand la chaîne est interrompue.",
        limits="Pas une cause locale à elle seule.",
        uncertainty="À vérifier sur place.",
        approved_at=timezone.now(),
        is_active=True,
    )
    activated = _admit(owner.user, establishment, reporting, key="mecanisme")
    assert activated.id != first.id
    assert "rupture-froid" in {
        item["identifier"] for item in activated.configuration["mechanisms"]
    }
    assert "rupture-froid" not in {
        item["identifier"] for item in first.configuration["mechanisms"]
    }


def test_one_running_analysis_leaves_the_next_visible(monkeypatch):
    allow_publish(monkeypatch)
    establishment = create_establishment(name="Brain file")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    first_reporting = _reporting(establishment, owner.user)
    second_reporting = _reporting(establishment, owner.user)
    second_reporting.storage_key = f"{second_reporting.storage_key}-2"
    second_reporting.content_sha256 = "b" * 64
    second_reporting.save(update_fields=["storage_key", "content_sha256", "updated_at"])
    second_reporting.extractions.update(source_sha256="b" * 64)
    current = _admit(owner.user, establishment, first_reporting, key="courante")
    waiting = _admit(owner.user, establishment, second_reporting, key="suivante")
    assert waiting.id != current.id
    page = analysis_page(
        user=owner.user,
        establishment_id=establishment.id,
        limit=10,
        cursor=None,
    )
    assert {row["id"] for row in page["results"]} == {str(current.id), str(waiting.id)}
    assert claim_analysis(current.id, current.attempt_token) is True
    assert claim_analysis(waiting.id, waiting.attempt_token) is False
    waiting.refresh_from_db()
    assert waiting.status == BrainAnalysis.Status.QUEUED
    assert waiting.attempt_count == 0
    shown = active_brain_work(user=owner.user, establishment_id=establishment.id)
    assert shown["id"] == str(current.id)
    assert shown["status"] == BrainAnalysis.Status.RUNNING
    request_analysis_cancel(current.id)
    waiting.refresh_from_db()
    assert claim_analysis(waiting.id, waiting.attempt_token) is True


def test_a_time_handoff_keeps_the_sealed_dossier_and_the_committed_tool(monkeypatch):
    allow_publish(monkeypatch)
    clock = {"now": 0.0}
    monkeypatch.setattr("houston.brain.runtime.time.monotonic", lambda: clock["now"])
    analysis = _prepare_quiet(monkeypatch)
    period_start, period_end = analysis.reporting.period_start, analysis.reporting.period_end
    dossiers = {"closed": None}

    def handler(_analysis_id, messages, _tools):
        if len(provider.calls) == 1:
            clock["now"] = 500.0
            return _search(period_start, period_end)
        assert any(message.get("role") == "tool" for message in messages)
        return EngineTurn(restitution={})

    provider = ScriptedProvider(handler)
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    dossier = BrainDossier.objects.get(analysis=analysis)
    assert analysis.status == BrainAnalysis.Status.QUEUED
    assert analysis.transient_retries_used == 0
    assert analysis.attempt_token
    assert dossier.closed_at is not None
    dossiers["closed"] = dossier.closed_at
    tool_entries = [entry for entry in analysis.trace if entry.get("kind") == "tool"]
    assert len(tool_entries) == 1
    assert tool_entries[0]["envelope"] is not None
    first_token = analysis.attempt_token
    clock["now"] = 0.0
    run_brain_analysis(analysis.id, first_token, provider=provider)
    analysis.refresh_from_db()
    dossier.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert analysis.failure_code == ""
    assert analysis.result["qualification"] == "not_publishable"
    assert analysis.transient_retries_used == 0
    assert dossier.closed_at == dossiers["closed"]
    assert BrainDossier.objects.filter(analysis=analysis).count() == 1
    assert len([entry for entry in analysis.trace if entry.get("kind") == "tool"]) == 1
    assert len(provider.calls) == 2


def test_truncated_capture_cannot_be_qualified_complete(monkeypatch):
    allow_publish(monkeypatch)
    period_start, period_end = _period()
    establishment, owner, reporting = _reporting_bundle(period_start, period_end)
    unit = create_business_unit(establishment=establishment, key="cap_life", label="Cave")
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

    def handler(_analysis_id, messages, _tools):
        if len(provider.calls) == 1:
            return _search(period_start, period_end)
        page = messages[-1]["content"]
        assert page["empty_means"] is None
        assert page["capture_omitted"] == 1
        evidence = [row["item_id"] for row in page["rows"]]
        documents = BrainDossierItem.objects.filter(
            dossier__analysis_id=analysis.id,
            category="document",
        )
        return EngineTurn(
            restitution={
                "subjects": [_subject("vu", evidence=evidence)],
                "anchors": [
                    {
                        "anchor_id": str(item.id),
                        "disposition": "not_significant",
                        "subject_key": "",
                    }
                    for item in documents
                ],
            }
        )

    provider = ScriptedProvider(handler)
    run_brain_analysis(analysis.id, analysis.attempt_token, provider=provider)
    analysis.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.COMPLETED
    assert analysis.failure_code == ""
    assert analysis.result["qualification"] != "complete"
    assert {"code": "capture_incomplete"} in analysis.result["limits"]
    tool = next(entry for entry in analysis.trace if entry.get("kind") == "tool")
    assert tool["envelope"]["empty_means"] is None
    assert tool["envelope"]["capture_omitted"] == 1


def test_cancel_and_provider_failure_publish_no_qualification(monkeypatch):
    allow_publish(monkeypatch)
    canceled = _prepare_quiet(monkeypatch)

    def cancel_during(_analysis_id, _messages, _tools):
        request_analysis_cancel(_analysis_id)
        return EngineTurn(restitution={"subjects": [_subject("trop-tard", evidence=["x"])]})

    run_brain_analysis(
        canceled.id,
        canceled.attempt_token,
        provider=ScriptedProvider(cancel_during),
    )
    canceled.refresh_from_db()
    assert canceled.status == BrainAnalysis.Status.CANCELED
    assert canceled.result is None

    failed = _prepare_quiet(monkeypatch)

    def unavailable(_analysis_id, _messages, _tools):
        raise BrainProviderUnavailable()

    run_brain_analysis(failed.id, failed.attempt_token, provider=ScriptedProvider(unavailable))
    failed.refresh_from_db()
    assert failed.status == BrainAnalysis.Status.QUEUED
    assert failed.transient_retries_used == 1
    run_brain_analysis(failed.id, failed.attempt_token, provider=ScriptedProvider(unavailable))
    failed.refresh_from_db()
    assert failed.status == BrainAnalysis.Status.FAILED
    assert failed.failure_code == "transient_exhausted"
    assert failed.result is None


def test_cancel_after_restitution_leaves_no_derived_object(monkeypatch):
    allow_publish(monkeypatch)
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
    revision = record_objective_revision(
        establishment=establishment,
        indicator="Couverture froid",
        unit="EUR",
        target="10",
        success_condition="gte",
        decision="accepted",
    )
    analysis = _analysis(owner, reporting)
    original_complete = brain_runtime._complete

    def cancel_before_commit(analysis_id, token, result=None):
        request_analysis_cancel(analysis_id)
        return original_complete(analysis_id, token, result)

    monkeypatch.setattr(brain_runtime, "_complete", cancel_before_commit)

    def handler(_analysis_id, _messages, _tools):
        return EngineTurn(
            restitution={
                "proposals": {
                    "suggestions": [{"key": "froid", "title": "Relever les températures"}],
                    "mechanisms": [
                        {
                            "key": "substitution",
                            "formulation": "Une promotion peut remplacer une vente plus rentable.",
                        }
                    ],
                }
            }
        )

    run_brain_analysis(
        analysis.id,
        analysis.attempt_token,
        provider=ScriptedProvider(handler),
    )
    analysis.refresh_from_db()
    revision.objective.refresh_from_db()
    assert analysis.status == BrainAnalysis.Status.CANCELED
    assert BrainSuggestion.objects.filter(analysis=analysis).count() == 0
    assert BrainObjectiveEvaluation.objects.filter(analysis=analysis).count() == 0
    assert BrainMechanismCandidate.objects.filter(analysis=analysis).count() == 0
    assert revision.objective.current_bilan_id is None
    detail = analysis_detail(
        user=owner.user,
        establishment_id=establishment.id,
        analysis_id=analysis.id,
    )
    assert detail["result"] is None
    assert detail["qualification"] is None
    assert detail["suggestions"] == []
    assert detail["evaluations"] == []
    assert detail["mechanisms"] == []


def test_selectors_distinguish_the_three_terminal_readings(monkeypatch):
    allow_publish(monkeypatch)
    establishment = create_establishment(name="Brain lecture")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    readings = {}
    for key, qualification in (
        ("complete", "complete"),
        ("partial", "partial"),
        ("muted", "not_publishable"),
    ):
        reporting = _reporting(establishment, owner.user)
        reporting.storage_key = f"{reporting.storage_key}-{key}"
        reporting.content_sha256 = uuid.uuid4().hex + uuid.uuid4().hex[:32]
        reporting.save(update_fields=["storage_key", "content_sha256", "updated_at"])
        reporting.extractions.update(source_sha256=reporting.content_sha256)
        analysis = _admit(owner.user, establishment, reporting, key=key)
        analysis.status = BrainAnalysis.Status.COMPLETED
        analysis.result = {
            "schema_version": "brain_engine_v1",
            "qualification": qualification,
            "subjects": [],
        }
        analysis.save(update_fields=["status", "result", "updated_at"])
        readings[qualification] = str(analysis.id)
    failed = _admit(
        owner.user,
        establishment,
        _reporting(establishment, owner.user),
        key="echec",
    )
    failed.status = BrainAnalysis.Status.FAILED
    failed.failure_code = "response_invalid"
    failed.save(update_fields=["status", "failure_code", "updated_at"])
    page = analysis_page(
        user=owner.user,
        establishment_id=establishment.id,
        limit=10,
        cursor=None,
    )
    by_id = {row["id"]: row for row in page["results"]}
    assert by_id[readings["complete"]]["investigation_succeeded"] is True
    assert by_id[readings["partial"]]["investigation_succeeded"] is True
    assert by_id[readings["not_publishable"]]["qualification"] == "not_publishable"
    assert by_id[readings["not_publishable"]]["investigation_succeeded"] is False
    assert by_id[str(failed.id)]["qualification"] is None
    assert by_id[str(failed.id)]["investigation_succeeded"] is None


def _prepare_quiet(monkeypatch):
    allow_publish(monkeypatch)
    establishment = create_establishment(name=f"Brain cycle {uuid.uuid4().hex[:8]}")
    owner = create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)
    reporting = _reporting(establishment, owner.user)
    return _admit(owner.user, establishment, reporting, key=uuid.uuid4().hex)
