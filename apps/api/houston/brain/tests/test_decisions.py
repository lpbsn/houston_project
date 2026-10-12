"""Suggestions, KPI evaluations, and platform Knowledge. Follow-ups stay out of this."""

from __future__ import annotations

import json
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from django.db import connection, connections
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from houston.action_plans.models import ActionPlan, ActionPlanExecution
from houston.action_plans.services import create_action_plan_with_execution
from houston.brain.admission import admit_brain_work
from houston.brain.capture import capture_dossier
from houston.brain.contract import assess, minimal_analysis
from houston.brain.errors import BrainAccessDenied, BrainWorkError
from houston.brain.knowledge import (
    activate_knowledge_version,
    decide_mechanism,
    revise_global_representation,
)
from houston.brain.models import (
    BrainDossier,
    BrainDossierItem,
    BrainKnowledgeVersion,
    BrainMechanismCandidate,
    BrainObjective,
    BrainObjectiveEvaluation,
    BrainSlot,
    BrainSuggestion,
)
from houston.brain.objectives import decide_objective, record_objective_revision
from houston.brain.runtime import _complete, claim_analysis, run_brain_analysis
from houston.brain.selectors import platform_knowledge_versions, platform_mechanism
from houston.brain.suggestions import convert_suggestion, revise_suggestion
from houston.brain.tests.test_admission import _admit, _reporting
from houston.establishments.models import EstablishmentMembership
from houston.platform.models import PlatformOperatorAccess
from houston.testing.factories import create_establishment, create_membership, create_user
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db(transaction=True)

EXCERPT = "La salle du restaurant a servi quarante couverts le mardi soir."
PRIVATE = "PREUVE-PRIVEE-CLIENT-NE-DOIT-PAS-SORTIR"
CLEAN = "Un effectif trop juste en salle peut dégrader le service du soir."


def _owner(establishment, role=EstablishmentMembership.Role.OWNER):
    return create_membership(establishment=establishment, role=role)


def _running(owner, reporting, key):
    analysis = _admit(owner.user, owner.establishment, reporting, key=key)
    assert claim_analysis(analysis.id, analysis.attempt_token) is True
    analysis.refresh_from_db()
    return analysis


def _proposal(unit, assignee):
    return {
        "suggestions": [
            {
                "key": "froid",
                "title": "Reprendre le contrôle du froid",
                "description": "Vérifier le groupe.",
                "pilot_business_unit_id": str(unit.id),
                "tasks": [
                    {
                        "task": "Contrôler le groupe froid",
                        "business_unit_id": str(unit.id),
                        "position": 1,
                    }
                ],
                "assignees": [
                    {
                        "membership_id": str(assignee.id),
                        "business_unit_id": str(unit.id),
                    }
                ],
            }
        ],
        "mechanisms": [],
    }


def _finish(analysis, proposals=None):
    result = {
        "schema_version": "brain_analysis_v1",
        "proposals": proposals or {"suggestions": [], "mechanisms": []},
    }
    assert _complete(analysis.id, analysis.attempt_token, result=result) is True
    analysis.refresh_from_db()
    assert analysis.status == analysis.Status.COMPLETED
    return result


def _pole(establishment):
    unit = create_business_unit(establishment=establishment, key="restaurant", label="Salle")
    staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(membership=staff, business_unit=unit)
    return unit, staff


def test_a_proposal_cannot_invent_a_kpi_target():
    payload = minimal_analysis(["s0000"])
    payload["proposals"] = {"suggestions": [], "mechanisms": [], "objectives": [{"target": "12"}]}
    assert assess(payload, pieces=["s0000"], items=[]).ok is False


def test_cancel_and_a_stale_token_publish_no_decision_object():
    establishment = create_establishment(name="Brain décisions", timezone="Europe/Paris")
    owner = _owner(establishment)
    payload = {"proposals": _proposal(*_pole(establishment))}
    canceled = _running(owner, _reporting(establishment, owner.user), "annulation")
    canceled.cancel_requested_at = timezone.now()
    canceled.save(update_fields=["cancel_requested_at", "updated_at"])
    assert _complete(canceled.id, canceled.attempt_token, result=payload) is False
    canceled.refresh_from_db()
    assert canceled.status == canceled.Status.CANCELED
    assert canceled.result is None

    other = create_establishment(name="Brain jeton", timezone="Europe/Paris")
    other_owner = _owner(other)
    stale = _running(other_owner, _reporting(other, other_owner.user), "jeton")
    old = stale.attempt_token
    stale.attempt_token = uuid.uuid4()
    stale.save(update_fields=["attempt_token", "updated_at"])
    assert _complete(stale.id, old, result=payload) is False
    assert BrainSuggestion.objects.count() == 0
    assert BrainObjectiveEvaluation.objects.count() == 0
    assert BrainMechanismCandidate.objects.count() == 0


def test_completion_publishes_the_result_and_the_draft_together():
    establishment = create_establishment(name="Brain publication", timezone="Europe/Paris")
    owner = _owner(establishment)
    unit, staff = _pole(establishment)
    analysis = _running(owner, _reporting(establishment, owner.user), "publication")
    before_plans = ActionPlan.objects.count()
    _finish(analysis, _proposal(unit, staff))
    assert analysis.result["schema_version"] == "brain_analysis_v1"
    assert BrainSuggestion.objects.filter(analysis=analysis, status="draft").count() == 1
    assert ActionPlan.objects.count() == before_plans


def test_concurrent_conversion_revision_conflict_revoked_rights_and_deleted_plan():
    establishment = create_establishment(name="Brain suggestions", timezone="Europe/Paris")
    owner = _owner(establishment)
    outsider = _owner(
        create_establishment(name="Autre établissement"),
        EstablishmentMembership.Role.DIRECTOR,
    )
    unit, staff = _pole(establishment)
    reporting = _reporting(establishment, owner.user)
    analysis = admit_brain_work(
        user=owner.user,
        establishment_id=establishment.id,
        reporting_id=reporting.id,
        idempotency_key="suggestion",
    )
    capture_dossier(analysis.id)
    assert claim_analysis(analysis.id, analysis.attempt_token) is True
    analysis.refresh_from_db()
    stored = _finish(analysis, _proposal(unit, staff))
    suggestion = BrainSuggestion.objects.get(analysis=analysis)
    first = suggestion.current_revision
    existing, _execution = create_action_plan_with_execution(
        establishment_id=establishment.id,
        created_by=owner,
        pilot_business_unit_id=unit.id,
        title="Plan déjà ouvert",
        tasks=[
            {
                "task": "Surveiller le froid",
                "business_unit_id": unit.id,
                "position": 1,
            }
        ],
        assignees=[
            {"membership_id": staff.id, "business_unit_id": unit.id},
        ],
        use_shared_chronology=False,
    )

    def _convert(_):
        try:
            return convert_suggestion(
                user=owner.user,
                suggestion_id=suggestion.id,
                expected_revision_id=first.id,
            )
        except Exception as exc:
            return exc
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(_convert, (1, 2)))
    assert not any(isinstance(result, Exception) for result in results)
    assert sorted(result.created for result in results) == [False, True]
    plan_id = results[0].action_plan_id
    assert len({result.action_plan_id for result in results}) == 1
    assert plan_id != existing.id
    noticed = [plan for result in results for plan in result.related_plan_ids]
    assert existing.id in noticed
    existing.refresh_from_db()
    assert existing.title == "Plan déjà ouvert"
    analysis.refresh_from_db()
    assert analysis.result == stored
    assert ActionPlan.objects.filter(establishment=establishment).count() == 2

    with pytest.raises(BrainWorkError) as conflict:
        revise_suggestion(
            user=owner.user,
            suggestion_id=suggestion.id,
            expected_revision_id=first.id,
            title="Conflit",
            pilot_business_unit_id=unit.id,
            assignees=[{"membership_id": str(staff.id), "business_unit_id": str(unit.id)}],
        )
    assert conflict.value.code == "suggestion_already_converted"
    suggestion.refresh_from_db()
    assert suggestion.current_revision_id == first.id
    assert suggestion.action_plan_id == plan_id

    execution = ActionPlanExecution.objects.get(action_plan_id=plan_id)
    execution.action_plan = None
    execution.save(update_fields=["action_plan", "updated_at"])
    ActionPlan.objects.filter(pk=plan_id).delete()
    again = convert_suggestion(
        user=owner.user,
        suggestion_id=suggestion.id,
        expected_revision_id=first.id,
    )
    assert again.created is False
    assert again.action_plan_id == plan_id
    assert not ActionPlan.objects.filter(pk=plan_id).exists()

    bare = _running(owner, _reporting(establishment, owner.user), "sans-assigne")
    _finish(
        bare,
        {
            "suggestions": [
                {
                    "key": "sans-responsable",
                    "title": "À désigner",
                    "pilot_business_unit_id": str(unit.id),
                    "tasks": [
                        {
                            "task": "Désigner quelqu'un",
                            "business_unit_id": str(unit.id),
                            "position": 1,
                        }
                    ],
                    "assignees": [],
                }
            ],
            "mechanisms": [],
        },
    )
    undesignated = BrainSuggestion.objects.get(stable_key="sans-responsable")
    with pytest.raises(BrainWorkError) as missing:
        convert_suggestion(
            user=owner.user,
            suggestion_id=undesignated.id,
            expected_revision_id=undesignated.current_revision_id,
        )
    assert missing.value.code == "assignee_required"
    owner.status = EstablishmentMembership.Status.DEACTIVATED
    owner.save(update_fields=["status", "updated_at"])
    with pytest.raises(BrainAccessDenied):
        convert_suggestion(
            user=owner.user,
            suggestion_id=undesignated.id,
            expected_revision_id=undesignated.current_revision_id,
        )
    with pytest.raises(BrainAccessDenied):
        convert_suggestion(
            user=outsider.user,
            suggestion_id=undesignated.id,
            expected_revision_id=undesignated.current_revision_id,
        )
    assert undesignated.action_plan_id is None


def test_two_directors_cannot_overwrite_a_newer_suggestion_revision():
    establishment = create_establishment(name="Brain révision", timezone="Europe/Paris")
    owner = _owner(establishment)
    director = _owner(establishment, EstablishmentMembership.Role.DIRECTOR)
    unit, staff = _pole(establishment)
    analysis = _running(owner, _reporting(establishment, owner.user), "revision")
    _finish(analysis, _proposal(unit, staff))
    suggestion = BrainSuggestion.objects.get(analysis=analysis)
    current = suggestion.current_revision
    revise_suggestion(
        user=director.user,
        suggestion_id=suggestion.id,
        expected_revision_id=current.id,
        title="Décision du directeur",
        pilot_business_unit_id=unit.id,
        assignees=[{"membership_id": str(staff.id), "business_unit_id": str(unit.id)}],
        tasks=[
            {
                "task": "Contrôler le groupe froid",
                "business_unit_id": str(unit.id),
                "position": 1,
            }
        ],
    )
    with pytest.raises(BrainWorkError) as conflict:
        revise_suggestion(
            user=owner.user,
            suggestion_id=suggestion.id,
            expected_revision_id=current.id,
            title="Ancienne décision",
            pilot_business_unit_id=unit.id,
            assignees=[{"membership_id": str(staff.id), "business_unit_id": str(unit.id)}],
        )
    assert conflict.value.code == "suggestion_revision_conflict"
    suggestion.refresh_from_db()
    assert suggestion.current_revision.title == "Décision du directeur"
    assert suggestion.current_revision_id != current.id


def test_plan_completion_and_objective_decisions_stay_independent():
    establishment = create_establishment(name="Brain indépendance", timezone="Europe/Paris")
    owner = _owner(establishment)
    unit, staff = _pole(establishment)
    revision = record_objective_revision(
        establishment=establishment,
        indicator="Couverture froid",
        unit="signal",
        target="0",
        method="comptage",
        due_on=date(2026, 3, 15),
    )
    reporting = _reporting(establishment, owner.user)
    analysis = admit_brain_work(
        user=owner.user,
        establishment_id=establishment.id,
        reporting_id=reporting.id,
        idempotency_key="independant",
    )
    capture_dossier(analysis.id)
    assert claim_analysis(analysis.id, analysis.attempt_token) is True
    analysis.refresh_from_db()
    _finish(analysis, _proposal(unit, staff))
    evaluation = BrainObjectiveEvaluation.objects.get(analysis=analysis)
    assert evaluation.revision_id == revision.id
    assert evaluation.outcome == "non_evaluable"
    snapshot = (evaluation.outcome, evaluation.reason, evaluation.revision_id)
    suggestion = BrainSuggestion.objects.get(analysis=analysis)
    converted = convert_suggestion(
        user=owner.user,
        suggestion_id=suggestion.id,
        expected_revision_id=suggestion.current_revision_id,
    )
    ActionPlanExecution.objects.filter(action_plan_id=converted.action_plan_id).update(
        status=ActionPlanExecution.Status.DONE
    )
    evaluation.refresh_from_db()
    revision.refresh_from_db()
    assert (evaluation.outcome, evaluation.reason, evaluation.revision_id) == snapshot
    assert revision.indicator == "Couverture froid"
    assert revision.target == "0"
    plans = ActionPlan.objects.filter(establishment=establishment).count()
    refused = decide_objective(
        user=owner.user,
        objective_id=revision.objective_id,
        expected_revision_id=revision.id,
        decision="refused",
    )
    assert refused.decision == "refused"
    assert refused.id != revision.id
    assert ActionPlan.objects.filter(establishment=establishment).count() == plans
    evaluation.refresh_from_db()
    assert evaluation.revision_id == revision.id
    assert evaluation.outcome == "non_evaluable"
    with pytest.raises(BrainWorkError) as unjustified:
        decide_objective(
            user=owner.user,
            objective_id=revision.objective_id,
            expected_revision_id=refused.id,
            decision="modified",
            target="4",
        )
    assert unjustified.value.code == "objective_target_unjustified"
    objective = BrainObjective.objects.get(pk=revision.objective_id)
    assert objective.current_revision_id == refused.id
    assert objective.current_revision.target == "0"


def test_a_revision_changed_during_analysis_keeps_its_own_bilan():
    establishment = create_establishment(name="Brain révision vivante", timezone="Europe/Paris")
    owner = _owner(establishment)
    captured = record_objective_revision(
        establishment=establishment,
        indicator="Couverture froid",
        unit="signal",
        target="0",
        method="comptage",
        due_on=date(2026, 3, 15),
    )
    reporting = _reporting(establishment, owner.user)
    analysis = admit_brain_work(
        user=owner.user,
        establishment_id=establishment.id,
        reporting_id=reporting.id,
        idempotency_key="pendant",
    )
    capture_dossier(analysis.id)
    replacement = record_objective_revision(
        establishment=establishment,
        objective=captured.objective,
        indicator="Révision pendant l'analyse",
        unit="signal",
        target="1",
        method="comptage",
        due_on=date(2026, 3, 20),
    )
    assert claim_analysis(analysis.id, analysis.attempt_token) is True
    analysis.refresh_from_db()
    _finish(analysis)
    evaluation = BrainObjectiveEvaluation.objects.get(analysis=analysis)
    assert evaluation.revision_id == captured.id
    replacement.refresh_from_db()
    assert replacement.indicator == "Révision pendant l'analyse"
    assert replacement.target == "1"
    captured.objective.refresh_from_db()
    assert captured.objective.current_revision_id == replacement.id
    assert captured.objective.current_bilan_id is None


def test_an_older_period_finished_later_does_not_replace_the_current_bilan():
    establishment = create_establishment(name="Brain bilans", timezone="Europe/Paris")
    owner = _owner(establishment)
    revision = record_objective_revision(
        establishment=establishment,
        indicator="Fréquentation",
        unit="couvert",
        target="40",
        method="comptage",
        measurement_period_start=date(2026, 1, 1),
        measurement_period_end=date(2026, 4, 1),
    )
    march = _reporting(establishment, owner.user)
    january = _reporting(establishment, owner.user)
    january.storage_key = f"{january.storage_key}-janvier"
    january.period_start = date(2026, 1, 1)
    january.period_end = date(2026, 2, 1)
    january.save(update_fields=["storage_key", "period_start", "period_end", "updated_at"])
    march_analysis = _admit(owner.user, establishment, march, key="mars")
    capture_dossier(march_analysis.id)
    assert claim_analysis(march_analysis.id, march_analysis.attempt_token) is True
    march_analysis.refresh_from_db()
    _finish(march_analysis)
    revision.objective.refresh_from_db()
    march_bilan = revision.objective.current_bilan
    assert march_bilan.analysis_id == march_analysis.id
    assert march_bilan.measured_period_end == date(2026, 4, 1)
    assert march_bilan.revision_id == revision.id
    january_analysis = _admit(owner.user, establishment, january, key="janvier")
    capture_dossier(january_analysis.id)
    assert claim_analysis(january_analysis.id, january_analysis.attempt_token) is True
    january_analysis.refresh_from_db()
    _finish(january_analysis)
    january_evaluation = BrainObjectiveEvaluation.objects.get(analysis=january_analysis)
    assert january_evaluation.revision_id == revision.id
    assert january_evaluation.measured_period_end == date(2026, 2, 1)
    revision.objective.refresh_from_db()
    revision.refresh_from_db()
    assert revision.objective.current_bilan_id == march_bilan.id
    assert revision.indicator == "Fréquentation"
    assert revision.target == "40"


def test_objective_revision_conflict_keeps_the_newer_decision():
    establishment = create_establishment(name="Brain objectif conflit", timezone="Europe/Paris")
    owner = _owner(establishment)
    director = _owner(establishment, EstablishmentMembership.Role.DIRECTOR)
    current = record_objective_revision(
        establishment=establishment,
        indicator="Couverture froid",
        target="0",
        method="comptage",
    )
    newer = decide_objective(
        user=director.user,
        objective_id=current.objective_id,
        expected_revision_id=current.id,
        decision="modified",
        indicator="Couverture révisée",
        justification="Le directeur a changé l'indicateur.",
    )
    with pytest.raises(BrainWorkError) as conflict:
        decide_objective(
            user=owner.user,
            objective_id=current.objective_id,
            expected_revision_id=current.id,
            decision="modified",
            indicator="Ancien indicateur",
            justification="Trop tard.",
        )
    assert conflict.value.code == "objective_revision_conflict"
    newer.refresh_from_db()
    assert newer.indicator == "Couverture révisée"
    current.objective.refresh_from_db()
    assert current.objective.current_revision_id == newer.id


def test_approval_does_not_activate_and_platform_output_has_no_client_data():
    assert BrainKnowledgeVersion.objects.filter(is_active=True).count() == 0
    establishment = create_establishment(name="Hôtel des Glycines", timezone="Europe/Paris")
    owner = _owner(establishment)
    operator = create_user(username=f"operator_{uuid.uuid4().hex[:8]}")
    PlatformOperatorAccess.objects.create(
        user=operator,
        is_active=True,
        granted_at=timezone.now(),
    )
    reporting = _reporting(establishment, owner.user)
    analysis = admit_brain_work(
        user=owner.user,
        establishment_id=establishment.id,
        reporting_id=reporting.id,
        idempotency_key="mecanisme",
    )
    dossier = BrainDossier.objects.create(
        analysis=analysis,
        establishment=establishment,
        timezone="Europe/Paris",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 4, 1),
        capture_started_at=timezone.now(),
        closed_at=timezone.now(),
    )
    item = BrainDossierItem.objects.create(
        dossier=dossier,
        category="document",
        stable_key="document:qualitative:0000",
        role="qualitatif",
        payload={"text": EXCERPT},
        reason="reporting_courant",
    )
    assert claim_analysis(analysis.id, analysis.attempt_token) is True
    analysis.refresh_from_db()
    _finish(
        analysis,
        {
            "suggestions": [],
            "mechanisms": [
                {
                    "key": "service",
                    "formulation": PRIVATE,
                    "global_formulation": "",
                    "conditions": EXCERPT,
                    "limits": "Ne prouve pas la cause.",
                    "uncertainty": "Hypothèse.",
                    "evidence_item_ids": [str(item.id)],
                }
            ],
        },
    )
    candidate = BrainMechanismCandidate.objects.get(analysis=analysis)
    assert candidate.status == "candidate"
    assert candidate.private_evidence == [str(item.id)]
    assert candidate.knowledge_version_id is None
    assert candidate.conditions == EXCERPT
    assert candidate.global_representation["conditions"] == ""
    assert candidate.global_representation["withheld"]["conditions"] == "dossier_excerpt"
    assert candidate.global_representation["limits"] == "Ne prouve pas la cause."
    with pytest.raises(BrainAccessDenied):
        decide_mechanism(user=owner.user, candidate_id=candidate.id, decision="approve")
    with pytest.raises(BrainAccessDenied):
        revise_global_representation(
            user=operator,
            candidate_id=candidate.id,
            formulation=CLEAN,
        )
    refused = (
        f"Mécanisme {uuid.uuid4()} à revoir.",
        "Hôtel des Glycines devrait revoir son service.",
        f"{EXCERPT} Cela reste une hypothèse.",
    )
    for text in refused:
        with pytest.raises(BrainWorkError):
            revise_global_representation(
                user=owner.user,
                candidate_id=candidate.id,
                formulation=text,
                conditions="Effectif observé sur plusieurs services.",
                limits="Ne prouve pas la cause.",
                uncertainty="Hypothèse.",
            )
    candidate.refresh_from_db()
    assert candidate.status == "candidate"
    assert candidate.global_formulation == ""
    assert EXCERPT not in json.dumps(candidate.global_representation, ensure_ascii=False)
    assert BrainKnowledgeVersion.objects.count() == 0
    revise_global_representation(
        user=owner.user,
        candidate_id=candidate.id,
        formulation=CLEAN,
        conditions="Effectif observé sur plusieurs services.",
        limits="Ne prouve pas la cause.",
        uncertainty="Hypothèse.",
    )
    with CaptureQueriesContext(connection) as approval_queries:
        decide_mechanism(user=operator, candidate_id=candidate.id, decision="approve")
    approval_sql = "\n".join(query["sql"] for query in approval_queries.captured_queries).lower()
    assert "dossieritem" not in approval_sql
    candidate.refresh_from_db()
    version = candidate.knowledge_version
    assert version is not None
    assert version.is_active is False
    assert version.activated_at is None
    assert version.global_formulation == CLEAN
    assert version.conditions == "Effectif observé sur plusieurs services."
    assert version.limits == "Ne prouve pas la cause."
    assert version.uncertainty == "Hypothèse."
    analysis.refresh_from_db()
    assert analysis.configuration["knowledge"]["selection"] == "none"
    with CaptureQueriesContext(connection) as platform_queries:
        viewed = {
            "versions": platform_knowledge_versions(user=operator),
            "mechanism": platform_mechanism(user=operator, candidate_id=candidate.id),
        }
    platform_sql = "\n".join(query["sql"] for query in platform_queries.captured_queries).lower()
    assert "dossieritem" not in platform_sql
    assert "private_evidence" not in platform_sql
    blob = json.dumps(viewed, ensure_ascii=False)
    assert PRIVATE not in blob
    assert "Hôtel des Glycines" not in blob
    assert "quarante couverts" not in blob
    assert str(item.id) not in blob
    assert str(establishment.id) not in blob
    assert viewed["mechanism"]["representation"] == {
        "formulation": CLEAN,
        "conditions": "Effectif observé sur plusieurs services.",
        "limits": "Ne prouve pas la cause.",
        "uncertainty": "Hypothèse.",
        "withheld": {},
    }
    assert viewed["mechanism"]["is_active"] is False
    assert viewed["versions"][0]["formulation"] == CLEAN
    assert viewed["versions"][0]["conditions"] == "Effectif observé sur plusieurs services."
    assert viewed["versions"][0]["is_active"] is False
    activate_knowledge_version(user=operator, version_id=version.id)
    version.refresh_from_db()
    analysis.refresh_from_db()
    assert version.is_active is True
    assert analysis.configuration["knowledge"]["selection"] == "none"
    later = _admit(owner.user, establishment, reporting, key="apres-activation")
    assert later.configuration["knowledge"]["version_id"] == str(version.id)
    assert later.configuration["knowledge"]["formulation"] == CLEAN
    assert later.configuration["knowledge"]["conditions"] == version.conditions
    version.global_formulation = "REMPLACE-APRES-ADMISSION"
    version.save(update_fields=["global_formulation", "updated_at"])
    later.refresh_from_db()
    assert later.configuration["knowledge"]["formulation"] == CLEAN


def test_numeric_bounds_qualitative_and_incomparable_measures():
    establishment = create_establishment(name="Brain mesures", timezone="Europe/Paris")
    owner = _owner(establishment)
    due = date(2026, 3, 15)
    specs = [
        ("Fréquentation gte", "gte", "40", "accepted", "reached", "numeric_comparison"),
        ("Fréquentation gt", "gt", "40", "accepted", "not_reached", "numeric_comparison"),
        ("Fréquentation gt plus", "gt", "40", "accepted", "reached", "numeric_comparison"),
        ("Fréquentation lt", "lt", "10", "accepted", "not_reached", "numeric_comparison"),
        ("Fréquentation lte", "lte", "10", "accepted", "reached", "numeric_comparison"),
        ("Fréquentation eq", "eq", "10", "accepted", "reached", "numeric_comparison"),
        ("Fréquentation eq moins", "eq", "10", "accepted", "not_reached", "numeric_comparison"),
        ("Fréquentation unité", "gte", "40", "accepted", "non_evaluable", "unit_mismatch"),
        ("Fréquentation ambiguë", "gte", "40", "accepted", "non_evaluable", "ambiguous_measure"),
        ("Fréquentation absente", "gte", "40", "accepted", "non_evaluable", "measure_missing"),
        (
            "Fréquentation texte",
            "gte",
            "au moins 40",
            "accepted",
            "non_evaluable",
            "target_not_numeric",
        ),
        (
            "Fréquentation sans opérateur",
            "",
            "au moins 40",
            "accepted",
            "non_evaluable",
            "condition_missing",
        ),
        (
            "Service attentif",
            "qualitative",
            "Tenir un service attentif",
            "accepted",
            "qualitative",
            "qualitative_appreciation",
        ),
        ("Fréquentation en attente", "gte", "40", "recorded", "non_evaluable", "decision_pending"),
        ("Fréquentation refusée", "gte", "40", "refused", "non_evaluable", "decision_refused"),
        ("Fréquentation double", "gte", "40", "accepted", "non_evaluable", "ambiguous_measure"),
    ]
    measures = {
        "Fréquentation gte": [("40", "couvert", [])],
        "Fréquentation gt": [("40", "couvert", [])],
        "Fréquentation gt plus": [("41", "couvert", [])],
        "Fréquentation lt": [("10", "couvert", [])],
        "Fréquentation lte": [("10", "couvert", [])],
        "Fréquentation eq": [("10", "couvert", [])],
        "Fréquentation eq moins": [("9", "couvert", [])],
        "Fréquentation unité": [("40", "kg", [])],
        "Fréquentation ambiguë": [("40", "couvert", ["deux lectures"])],
        "Fréquentation texte": [("40", "couvert", [])],
        "Fréquentation sans opérateur": [("40", "couvert", [])],
        "Service attentif": [("40", "couvert", [])],
        "Fréquentation en attente": [("40", "couvert", [])],
        "Fréquentation refusée": [("40", "couvert", [])],
        "Fréquentation double": [("40", "couvert", []), ("41", "couvert", [])],
    }
    for indicator, condition, target, decision, _outcome, _reason in specs:
        revision = record_objective_revision(
            establishment=establishment,
            indicator=indicator,
            unit="couvert",
            target=target,
            success_condition=condition,
            method="comptage",
            due_on=due,
        )
        if decision == "accepted":
            decide_objective(
                user=owner.user,
                objective_id=revision.objective_id,
                expected_revision_id=revision.id,
                decision="accepted",
            )
        elif decision == "refused":
            decide_objective(
                user=owner.user,
                objective_id=revision.objective_id,
                expected_revision_id=revision.id,
                decision="refused",
            )
    reporting = _reporting(establishment, owner.user)
    extraction = reporting.extractions.get()
    extraction.payload = {
        "measures": [
            {
                "label": label,
                "value": value,
                "unit": unit,
                "ambiguities": ambiguities,
            }
            for label, rows in measures.items()
            for value, unit, ambiguities in rows
        ],
        "qualitative": [{"text": "Service du mois.", "locator": {"block": 0}}],
    }
    extraction.save(update_fields=["payload", "updated_at"])
    analysis = _admit(owner.user, establishment, reporting, key="mesures")
    capture_dossier(analysis.id)
    copied = BrainDossierItem.objects.get(
        dossier__analysis=analysis,
        category="objective",
        payload__indicator="Fréquentation gte",
    )
    assert copied.payload["decision"] == "accepted"
    assert copied.payload["success_condition"] == "gte"
    assert claim_analysis(analysis.id, analysis.attempt_token) is True
    analysis.refresh_from_db()
    _finish(analysis)
    by_indicator = {
        evaluation.revision.indicator: evaluation
        for evaluation in BrainObjectiveEvaluation.objects.filter(analysis=analysis).select_related(
            "revision"
        )
    }
    assert len(by_indicator) == len(specs)
    for indicator, _condition, _target, _decision, outcome, reason in specs:
        evaluation = by_indicator[indicator]
        assert evaluation.outcome == outcome
        assert evaluation.reason == reason
        if outcome == "qualitative":
            assert evaluation.measure is None
        if outcome in {"reached", "not_reached"}:
            assert evaluation.reason == "numeric_comparison"
            assert evaluation.measure["value"]
            assert len(evaluation.source_item_ids) == 2
    reached = by_indicator["Fréquentation gte"]
    objective = reached.objective
    objective.refresh_from_db()
    assert objective.current_bilan_id == reached.id
    assert objective.current_revision_id == reached.revision_id


def test_a_publication_error_rolls_back_and_is_not_retried(monkeypatch):
    monkeypatch.setattr("houston.brain.runtime.publish_brain_analysis", lambda *_a, **_k: True)

    def _refuse_retry(*_args, **_kwargs):
        raise AssertionError("retry")

    monkeypatch.setattr("houston.brain.runtime._handoff_transient", _refuse_retry)
    establishment = create_establishment(name="Brain rollback", timezone="Europe/Paris")
    owner = _owner(establishment)
    revision = record_objective_revision(
        establishment=establishment,
        indicator="Couverture froid",
        unit="signal",
        target="0",
        method="comptage",
        due_on=date(2026, 3, 15),
    )
    reporting = _reporting(establishment, owner.user)
    analysis = _running(owner, reporting, "rollback")
    dossier = BrainDossier.objects.create(
        analysis=analysis,
        establishment=establishment,
        timezone="Europe/Paris",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 4, 1),
        capture_started_at=timezone.now(),
        closed_at=timezone.now(),
    )
    BrainDossierItem.objects.create(
        dossier=dossier,
        category="objective",
        stable_key=f"objective-revision:{revision.id}",
        role="chevauchement",
        payload={
            "source_id": str(revision.objective_id),
            "revision_id": str(revision.id),
            "decision": revision.decision,
            "success_condition": revision.success_condition,
        },
        reason="objectif_pertinent",
    )
    BrainDossierItem.objects.create(
        dossier=dossier,
        category="objective",
        stable_key="objective-revision:absent",
        role="chevauchement",
        payload={
            "source_id": str(revision.objective_id),
            "revision_id": str(uuid.uuid4()),
            "decision": "recorded",
            "success_condition": "",
        },
        reason="objectif_pertinent",
    )
    assert analysis.transient_retries_used == 0
    inserted = []
    original = BrainObjectiveEvaluation.objects.get_or_create

    def _counting(*args, **kwargs):
        row, created = original(*args, **kwargs)
        inserted.append(row.pk)
        return row, created

    monkeypatch.setattr(BrainObjectiveEvaluation.objects, "get_or_create", _counting)
    finished = _complete(
        analysis.id,
        analysis.attempt_token,
        result=minimal_analysis(["s0000"]),
    )
    assert finished is False
    assert len(inserted) == 1
    analysis.refresh_from_db()
    revision.objective.refresh_from_db()
    assert analysis.status == analysis.Status.FAILED
    assert analysis.failure_code == "evaluation_revision_missing"
    assert analysis.result is None
    assert analysis.transient_retries_used == 0
    assert revision.objective.current_bilan_id is None
    assert not BrainSlot.objects.filter(analysis=analysis).exists()
    assert BrainObjectiveEvaluation.objects.filter(analysis=analysis).count() == 0
    assert BrainSuggestion.objects.filter(analysis=analysis).count() == 0
    assert BrainMechanismCandidate.objects.filter(analysis=analysis).count() == 0
    assert (
        _complete(
            analysis.id,
            analysis.attempt_token,
            result=minimal_analysis(["s0000"]),
        )
        is False
    )
    run_brain_analysis(analysis.id, analysis.attempt_token)
    analysis.refresh_from_db()
    assert analysis.status == analysis.Status.FAILED
    assert analysis.failure_code == "evaluation_revision_missing"
    assert analysis.transient_retries_used == 0
    assert analysis.result is None
    assert BrainObjectiveEvaluation.objects.filter(analysis=analysis).count() == 0
