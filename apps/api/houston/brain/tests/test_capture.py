from __future__ import annotations

import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from dateutil.relativedelta import relativedelta
from django.db import connection, connections
from django.utils import timezone

from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionReview,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
)
from houston.analytics.models import (
    AnalyticsHistoryCoverage,
    OperationalPattern,
    SignalPatternAssignment,
)
from houston.brain.admission import admit_brain_work
from houston.brain.capture import capture_dossier
from houston.brain.collection import (
    REQUIRED_SEARCHES,
    ROLE_INTENTION,
    ROLE_LATE,
    ROLE_N1,
    ROLE_OVERLAP,
)
from houston.brain.errors import BrainWorkError, CaptureTimeout, CaptureVolumeExceeded
from houston.brain.models import (
    BrainDossier,
    BrainDossierItem,
    BrainExtraction,
    BrainReporting,
    BrainSearchRun,
)
from houston.brain.objectives import record_objective_revision
from houston.brain.records import EXTRACTOR_ID, EXTRACTOR_VERSION
from houston.comments.models import Comment
from houston.establishments.models import EstablishmentMembership
from houston.observations.models import Observation
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_CREATED,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
)
from houston.signals.lifecycle_events import record_signal_lifecycle_event
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.selectors import signal_feed_queryset
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db(transaction=True)

PARIS = ZoneInfo("Europe/Paris")
FORBIDDEN = (
    "FORBIDDEN_RAW",
    "FORBIDDEN_COMMENT",
    "FORBIDDEN_RETAINED_COMMENT",
    "FORBIDDEN_REVIEW",
    "FORBIDDEN_EXEC_DESCRIPTION",
    "FORBIDDEN_TASK_DESCRIPTION",
    "FORBIDDEN_OTHER_ESTABLISHMENT",
    "FORBIDDEN_OTHER_EXECUTION",
    "FORBIDDEN_OTHER_REPORTING",
    "FORBIDDEN_OTHER_OBJECTIVE",
    "FORBIDDEN_FAR_MEASURE",
    "FORBIDDEN_OLD_QUALITATIVE",
    "FORBIDDEN_OTHER_ORG_PATTERN",
)


def _period():
    today = timezone.now().astimezone(PARIS).date()
    period_end = today.replace(day=1) - relativedelta(months=1)
    period_start = period_end - relativedelta(months=1)
    return period_start, period_end


def _at(day):
    return datetime.combine(day, datetime.min.time(), tzinfo=PARIS) + timedelta(hours=12)


def _reporting(establishment, author, period_start, period_end, *, measures=None, qualitative=None):
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
        payload={
            "measures": measures or [],
            "qualitative": qualitative or [],
        },
    )
    return reporting


def _signal(
    establishment,
    *,
    title,
    summary,
    created_at,
    status=Signal.Status.OPEN,
    resolved_at=None,
    business_unit=None,
    focus=None,
):
    signal = Signal.objects.create(
        establishment=establishment,
        affected_business_unit=business_unit,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary=summary,
        issue_focus=focus or f"focus-{uuid.uuid4().hex[:12]}",
        location_text="Chambre 12",
        last_activity_at=created_at,
        status=status,
        resolved_at=resolved_at,
    )
    Signal.objects.filter(pk=signal.pk).update(created_at=created_at, last_activity_at=created_at)
    signal.refresh_from_db()
    return signal


def _owner(establishment):
    return create_membership(establishment=establishment, role=EstablishmentMembership.Role.OWNER)


def _analysis(owner, reporting, key="demande"):
    return admit_brain_work(
        user=owner.user,
        establishment_id=owner.establishment_id,
        reporting_id=reporting.id,
        idempotency_key=key,
    )


def _blob(dossier) -> str:
    parts = [
        json.dumps(item.payload, ensure_ascii=False, default=str) for item in dossier.items.all()
    ]
    parts.extend(
        json.dumps(run.criteria, ensure_ascii=False, default=str)
        for run in dossier.search_runs.all()
    )
    return "\n".join(parts)


def test_capture_keeps_feed_excluded_signals_late_declarations_and_a_stable_copy(settings):
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 20
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier Paris", timezone="Europe/Paris")
    other = create_establishment(name="Autre etablissement", timezone="Europe/Paris")
    other_owner = _owner(other)
    other_unit = create_business_unit(
        establishment=other, key="autre_brain", label="Autre pole"
    )
    owner = _owner(establishment)
    kitchen = create_business_unit(
        establishment=establishment, key="cuisine_brain", label="Cuisine"
    )
    bar = create_business_unit(establishment=establishment, key="bar_brain", label="Bar")
    reporting = _reporting(
        establishment,
        owner.user,
        period_start,
        period_end,
        measures=[
            {"label": "Taux d'occupation", "value": "80", "value_kind": "number", "unit": "%"}
        ],
    )
    resolved = _signal(
        establishment,
        title="Panne hors feed",
        summary="Le groupe froid s'est arrêté.",
        created_at=_at(period_start + timedelta(days=2)),
        status=Signal.Status.RESOLVED,
        resolved_at=_at(period_start + timedelta(days=8)),
        business_unit=kitchen,
    )
    overlap = _signal(
        establishment,
        title="Signal encore ouvert",
        summary=f"Mention interne le {(period_start + timedelta(days=4)).strftime('%d/%m/%Y')}.",
        created_at=_at(period_start + timedelta(days=3)),
        business_unit=bar,
    )
    late = _signal(
        establishment,
        title="Déclaré après la période",
        summary=f"La panne date du {(period_start + timedelta(days=4)).strftime('%d/%m/%Y')}.",
        created_at=_at(period_end + timedelta(days=5)),
    )
    hidden = _signal(
        establishment,
        title="Date seulement dans le brut",
        summary="Aucun jour explicite ici.",
        created_at=_at(period_end + timedelta(days=6)),
    )
    too_late = _signal(
        establishment,
        title="Créé après la capture",
        summary=f"Le {(period_start + timedelta(days=4)).strftime('%d/%m/%Y')}.",
        created_at=timezone.now() + timedelta(days=2),
    )
    old = _signal(
        establishment,
        title="Historique hors fenêtres",
        summary="Ancien et déjà clos.",
        created_at=_at(period_start - relativedelta(years=3)),
        status=Signal.Status.RESOLVED,
        resolved_at=_at(period_start - relativedelta(years=3) + timedelta(days=2)),
    )
    n1_start = period_start - relativedelta(years=1)
    n1 = _signal(
        establishment,
        title="Signal N-1",
        summary="Même mois l'an dernier.",
        created_at=_at(n1_start + timedelta(days=3)),
        status=Signal.Status.RESOLVED,
        resolved_at=_at(n1_start + timedelta(days=6)),
    )
    event_only = _signal(
        establishment,
        title="Événement de période",
        summary="Clos bien avant, journal pendant la période.",
        created_at=_at(period_start - relativedelta(years=2)),
        status=Signal.Status.RESOLVED,
        resolved_at=_at(period_start - relativedelta(years=2) + timedelta(days=1)),
    )
    foreign = _signal(
        other,
        title="FORBIDDEN_OTHER_ESTABLISHMENT",
        summary=f"Le {(period_start + timedelta(days=4)).strftime('%d/%m/%Y')}.",
        created_at=_at(period_start + timedelta(days=2)),
    )
    observation = Observation.objects.create(
        establishment=establishment,
        submitted_by_membership=owner,
        raw_text=f"FORBIDDEN_RAW {(period_start + timedelta(days=4)).strftime('%d/%m/%Y')}",
        client_submission_id=uuid.uuid4(),
        submitted_at=timezone.now(),
    )
    SignalSourceObservation.objects.create(
        signal=resolved,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    Comment.objects.create(
        establishment=establishment,
        signal=hidden,
        author_membership=owner,
        body=f"FORBIDDEN_COMMENT {(period_start + timedelta(days=4)).strftime('%d/%m/%Y')}",
    )
    Comment.objects.create(
        establishment=establishment,
        signal=resolved,
        author_membership=owner,
        body="FORBIDDEN_RETAINED_COMMENT sur le signal retenu",
    )
    record_signal_lifecycle_event(
        signal=resolved,
        event_type=SIGNAL_LIFECYCLE_EVENT_CREATED,
        occurred_at=_at(period_start - timedelta(days=1)),
        metadata_safe={"to_status": Signal.Status.OPEN},
    )
    record_signal_lifecycle_event(
        signal=resolved,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=_at(period_start + timedelta(days=8)),
        metadata_safe={"to_status": Signal.Status.RESOLVED},
    )
    record_signal_lifecycle_event(
        signal=resolved,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=_at(period_end + timedelta(days=2)),
        metadata_safe={"to_status": Signal.Status.RESOLVED},
    )
    record_signal_lifecycle_event(
        signal=resolved,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=timezone.now() + timedelta(days=3),
        metadata_safe={"to_status": Signal.Status.RESOLVED},
    )
    record_signal_lifecycle_event(
        signal=event_only,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=_at(period_start + timedelta(days=4)),
        metadata_safe={"to_status": Signal.Status.RESOLVED},
    )
    AnalyticsHistoryCoverage.objects.create(
        singleton_key=AnalyticsHistoryCoverage.SINGLETON_KEY,
        reliable_from=_at(period_start - relativedelta(years=5)),
    )
    pattern = OperationalPattern(
        organization=establishment.organization,
        label="Fuite chronique",
        semantic_label="Fuite chronique",
    )
    pattern.save()
    other_pattern = OperationalPattern(
        organization=other.organization,
        label="FORBIDDEN_OTHER_ORG_PATTERN",
        semantic_label="FORBIDDEN_OTHER_ORG_PATTERN",
    )
    other_pattern.save()
    SignalPatternAssignment.objects.create(
        signal=resolved,
        pattern=pattern,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature="signature-fuite",
        assigned_classifier_version="v1",
        assigned_at=timezone.now(),
    )
    SignalPatternAssignment.objects.create(
        signal=overlap,
        pattern=other_pattern,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature="signature-etrangere",
        assigned_classifier_version="v1",
        assigned_at=timezone.now(),
    )
    plan = ActionPlan.objects.create(
        establishment=establishment,
        created_by=owner,
        pilot_business_unit=kitchen,
        title="Reprendre le froid",
        description="FORBIDDEN_EXEC_DESCRIPTION",
        is_reusable=False,
    )
    execution = ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=establishment,
        created_by=owner,
        source_signal=resolved,
        title="Reprendre le froid",
        description="FORBIDDEN_EXEC_DESCRIPTION",
        pilot_business_unit=kitchen,
        requires_validation=False,
        last_activity_at=_at(period_start + timedelta(days=5)),
        use_shared_chronology=True,
        start_at=_at(period_start + timedelta(days=5)),
        end_at=_at(period_start + timedelta(days=6)),
        started_at=_at(period_start + timedelta(days=5)),
    )
    team = ActionPlanExecutionTeam.objects.create(
        action_plan_execution=execution,
        business_unit=kitchen,
        is_pilot=True,
    )
    ActionPlanExecutionTask.objects.create(
        action_plan_execution=execution,
        execution_team=team,
        task="Contrôler le groupe froid",
        description="FORBIDDEN_TASK_DESCRIPTION",
        position=1,
    )
    ActionPlanExecutionReview.objects.create(
        action_plan_execution=execution,
        reviewer_membership=owner,
        stars=4,
        comment="FORBIDDEN_REVIEW",
        reviewed_at=timezone.now(),
    )
    foreign_plan = ActionPlan.objects.create(
        establishment=other,
        created_by=other_owner,
        pilot_business_unit=other_unit,
        title="FORBIDDEN_OTHER_EXECUTION",
        is_reusable=False,
    )
    ActionPlanExecution.objects.create(
        action_plan=foreign_plan,
        establishment=other,
        created_by=other_owner,
        title="FORBIDDEN_OTHER_EXECUTION",
        pilot_business_unit=other_unit,
        requires_validation=False,
        last_activity_at=_at(period_start + timedelta(days=5)),
        use_shared_chronology=True,
        start_at=_at(period_start + timedelta(days=5)),
        end_at=_at(period_start + timedelta(days=6)),
        started_at=_at(period_start + timedelta(days=5)),
    )
    previous_start = period_start - (period_end - period_start)
    prior = _reporting(
        establishment,
        owner.user,
        previous_start,
        period_start,
        measures=[{"label": "CA salle", "value": "10", "value_kind": "number", "unit": "EUR"}],
        qualitative=[{"kind": "paragraph", "text": "FORBIDDEN_OLD_QUALITATIVE"}],
    )
    _reporting(
        other,
        other_owner.user,
        previous_start,
        period_start,
        measures=[
            {
                "label": "FORBIDDEN_OTHER_REPORTING",
                "value": "9",
                "value_kind": "number",
                "unit": "EUR",
            }
        ],
    )
    far_start = period_start - relativedelta(years=4)
    _reporting(
        establishment,
        owner.user,
        far_start,
        far_start + relativedelta(months=1),
        measures=[{"label": "FORBIDDEN_FAR_MEASURE", "value": "1", "value_kind": "number"}],
    )
    copied = record_objective_revision(
        establishment=establishment,
        indicator="Couverture froid",
        due_on=period_start + timedelta(days=10),
        unit="signal",
        target="0",
        method="comptage",
    )
    record_objective_revision(
        establishment=establishment,
        indicator="Marge hors période",
        due_on=period_end + timedelta(days=40),
    )
    matched = record_objective_revision(
        establishment=establishment,
        indicator="Taux d'occupation",
        due_on=period_end + timedelta(days=80),
        unit="%",
    )
    record_objective_revision(
        establishment=other,
        indicator="FORBIDDEN_OTHER_OBJECTIVE",
        due_on=period_start + timedelta(days=10),
    )
    analysis = _analysis(owner, reporting)
    dossier = capture_dossier(analysis.id)

    feed_ids = set(
        signal_feed_queryset(membership=owner, view_mode="general").values_list("id", flat=True)
    )
    assert resolved.id not in feed_ids
    assert old.id not in feed_ids
    signal_items = {
        item.payload["source_id"]: item for item in dossier.items.filter(category="signal")
    }
    assert str(resolved.id) in signal_items
    assert signal_items[str(resolved.id)].role == ROLE_OVERLAP
    assert signal_items[str(resolved.id)].payload["business_units"]["affected"]["name"] == "Cuisine"
    assert signal_items[str(overlap.id)].payload["business_units"]["affected"]["name"] == "Bar"
    assert "phenomenon_mentioned_at" not in signal_items[str(overlap.id)].payload
    assert signal_items[str(overlap.id)].payload["pattern_assignment"] is None
    assert signal_items[str(overlap.id)].payload["recorded_at"] == overlap.created_at.isoformat()
    late_item = signal_items[str(late.id)]
    assert late_item.role == ROLE_LATE
    assert late_item.payload["recorded_at"] == late.created_at.isoformat()
    assert (
        late_item.payload["phenomenon_mentioned_at"]
        == (period_start + timedelta(days=4)).isoformat()
    )
    assert late_item.payload["recorded_at"] != late_item.payload["phenomenon_mentioned_at"]
    assert late_item.payload["mention"]["uncertainty"] == "text_mention"
    assert late_item.payload["mention"]["field"] == "structured_summary"
    assert str(hidden.id) not in signal_items
    assert str(too_late.id) not in signal_items
    assert str(old.id) not in signal_items
    assert str(foreign.id) not in signal_items
    assert str(event_only.id) in signal_items
    assert signal_items[str(n1.id)].role == ROLE_N1
    resolved_payload = signal_items[str(resolved.id)].payload
    assert resolved_payload["status_at_capture"] == {
        "value": Signal.Status.RESOLVED,
        "as_of": "capture",
    }
    assert resolved_payload["status_at_period_start"]["value"] == Signal.Status.OPEN
    assert resolved_payload["status_at_period_end"]["value"] == Signal.Status.RESOLVED
    assert len(resolved_payload["events"]) == 3
    assert {event["role"] for event in resolved_payload["events"]} == {
        "periode",
        "suivi",
        "anterieur",
    }
    assert resolved_payload["source_observation_link_counts"]["created_from"] == 1
    assert resolved_payload["pattern_assignment"]["label"] == "Fuite chronique"
    assert resolved_payload["pattern_assignment"]["pattern_id"] == str(pattern.id)
    execution_item = dossier.items.get(category="execution", role=ROLE_OVERLAP)
    assert execution_item.payload["source_signal_id"] == str(resolved.id)
    assert execution_item.payload["started_at"]
    task_item = dossier.items.get(category="execution_task")
    assert task_item.payload["task"] == "Contrôler le groupe froid"
    assert dossier.items.filter(category="plan", payload__title="Reprendre le froid").exists()
    prior_item = dossier.items.get(category="reporting")
    assert prior_item.payload["source_id"] == str(prior.id)
    assert prior_item.payload["measures"][0]["label"] == "CA salle"
    objective_ids = {
        item.payload["revision_id"] for item in dossier.items.filter(category="objective")
    }
    assert str(copied.id) in objective_ids
    assert str(matched.id) in objective_ids
    objective_search = dossier.search_runs.get(code="objectifs_pertinents")
    assert objective_search.examined_count == 3
    assert objective_search.retained_count == 2
    assert any(
        row["reason"] == "periode_non_comparable" for row in objective_search.criteria["exclusions"]
    )
    assert set(dossier.search_runs.values_list("code", flat=True)) == set(REQUIRED_SEARCHES)
    text = _blob(dossier)
    for marker in FORBIDDEN:
        assert marker not in text
    assert "raw_text" not in text
    resolved.title = "Titre modifié après fermeture"
    resolved.save(update_fields=["title", "updated_at"])
    record_objective_revision(
        establishment=establishment,
        objective=copied.objective,
        indicator="Révision postérieure",
        due_on=period_start + timedelta(days=10),
    )
    late_item.refresh_from_db()
    resolved_item = dossier.items.get(stable_key=f"signal:{resolved.id}")
    assert resolved_item.payload["title"] == "Panne hors feed"
    copied_item = dossier.items.get(stable_key=f"objective-revision:{copied.id}")
    assert copied_item.payload["revision_id"] == str(copied.id)
    assert copied_item.payload["indicator"] == "Couverture froid"
    with pytest.raises(BrainWorkError) as refused:
        capture_dossier(analysis.id)
    assert refused.value.code == "dossier_already_closed"
    assert (
        dossier.items.get(stable_key=f"signal:{resolved.id}").payload["title"] == "Panne hors feed"
    )


def test_empty_establishment_still_records_every_minimal_search():
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier vide", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    dossier = capture_dossier(_analysis(owner, reporting).id)
    runs = {run.code: run for run in dossier.search_runs.all()}
    assert set(runs) == set(REQUIRED_SEARCHES)
    assert runs["objectifs_pertinents"].examined_count == 0
    assert runs["objectifs_pertinents"].retained_count == 0
    assert runs["declarations_tardives"].examined_count == 0
    assert dossier.items.count() == 0
    assert dossier.closed_at is not None


def test_civil_period_uses_the_establishment_timezone():
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier fuseau", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    end_instant = datetime.combine(period_end, datetime.min.time(), tzinfo=PARIS)
    inside = _signal(
        establishment,
        title="Dedans",
        summary="Avant la fin civile.",
        created_at=end_instant - timedelta(minutes=30),
    )
    outside = _signal(
        establishment,
        title="Dehors",
        summary="Après la fin civile.",
        created_at=end_instant + timedelta(minutes=30),
    )
    dossier = capture_dossier(_analysis(owner, reporting).id)
    roles = {
        item.payload["source_id"]: item.role for item in dossier.items.filter(category="signal")
    }
    assert roles[str(inside.id)] == ROLE_OVERLAP
    assert str(outside.id) not in roles
    late_search = dossier.search_runs.get(code="declarations_tardives")
    assert late_search.examined_count == 1
    assert late_search.retained_count == 0


def test_a_planned_execution_after_capture_is_an_intention():
    today = timezone.now().astimezone(PARIS).date()
    period_start = today
    period_end = today + timedelta(days=40)
    establishment = create_establishment(name="Dossier intention", timezone="Europe/Paris")
    owner = _owner(establishment)
    business_unit = create_business_unit(
        establishment=establishment, key="intent_brain", label="Hall"
    )
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    plan = ActionPlan.objects.create(
        establishment=establishment,
        created_by=owner,
        pilot_business_unit=business_unit,
        title="Intervention à venir",
        is_reusable=False,
    )
    ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=establishment,
        created_by=owner,
        title="Intervention à venir",
        pilot_business_unit=business_unit,
        requires_validation=False,
        last_activity_at=timezone.now(),
        use_shared_chronology=True,
        start_at=timezone.now() + timedelta(days=5),
        end_at=timezone.now() + timedelta(days=6),
    )
    dossier = capture_dossier(_analysis(owner, reporting).id)
    item = dossier.items.get(category="execution")
    assert item.role == ROLE_INTENTION
    assert item.payload["planned_after_capture"] is True


def test_volume_ceiling_rolls_the_capture_back(settings):
    settings.HOUSTON_BRAIN_MAX_CANDIDATES_PER_CATEGORY = 1
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier volume", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    for index in (1, 2):
        _signal(
            establishment,
            title=f"Signal {index}",
            summary="Ouvert pendant la période.",
            created_at=_at(period_start + timedelta(days=index)),
        )
    analysis = _analysis(owner, reporting)
    with pytest.raises(CaptureVolumeExceeded) as refused:
        capture_dossier(analysis.id)
    assert refused.value.category == "chevauchement_signals"
    assert BrainDossier.objects.filter(analysis=analysis).count() == 0
    assert BrainDossierItem.objects.count() == 0


def test_n1_signals_and_executions_share_one_category_ceiling(settings):
    settings.HOUSTON_BRAIN_MAX_CANDIDATES_PER_CATEGORY = 1
    period_start, period_end = _period()
    n1_start = period_start - relativedelta(years=1)
    establishment = create_establishment(name="Dossier plafond n1", timezone="Europe/Paris")
    owner = _owner(establishment)
    business_unit = create_business_unit(
        establishment=establishment, key="n1_ceiling_brain", label="Hall"
    )
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    _signal(
        establishment,
        title="Signal N-1",
        summary="Clos l'an dernier.",
        created_at=_at(n1_start + timedelta(days=2)),
        status=Signal.Status.RESOLVED,
        resolved_at=_at(n1_start + timedelta(days=4)),
    )
    plan = ActionPlan.objects.create(
        establishment=establishment,
        created_by=owner,
        pilot_business_unit=business_unit,
        title="Exécution N-1",
        is_reusable=False,
    )
    ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=establishment,
        created_by=owner,
        title="Exécution N-1",
        pilot_business_unit=business_unit,
        requires_validation=False,
        last_activity_at=_at(n1_start + timedelta(days=3)),
        use_shared_chronology=True,
        start_at=_at(n1_start + timedelta(days=3)),
        end_at=_at(n1_start + timedelta(days=4)),
    )
    analysis = _analysis(owner, reporting)
    with pytest.raises(CaptureVolumeExceeded) as refused:
        capture_dossier(analysis.id)
    assert refused.value.category == "fenetre_n_1"
    assert not BrainDossier.objects.filter(analysis=analysis).exists()


def test_incomplete_capture_rolls_back():
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier incomplet", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    analysis = _analysis(owner, reporting)
    with pytest.raises(BrainWorkError) as refused:
        capture_dossier(analysis.id, _fail_before_close=True)
    assert refused.value.code == "capture_incomplete"
    assert not BrainDossier.objects.filter(analysis=analysis).exists()
    assert BrainSearchRun.objects.count() == 0


def test_repeatable_read_keeps_the_snapshot_when_a_source_changes():
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier rr", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    signal = _signal(
        establishment,
        title="Titre au début",
        summary="Ouvert.",
        created_at=_at(period_start + timedelta(days=2)),
    )
    seen = {}

    def before_close():
        def update():
            try:
                Signal.objects.filter(pk=signal.id).update(title="Titre concurrent")
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(update).result()
        with connection.cursor() as cursor:
            cursor.execute("SHOW transaction_isolation")
            seen["isolation"] = cursor.fetchone()[0]
        seen["title"] = Signal.objects.get(pk=signal.id).title

    dossier = capture_dossier(_analysis(owner, reporting).id, _before_close=before_close)
    assert seen["isolation"] == "repeatable read"
    assert seen["title"] == "Titre au début"
    assert dossier.items.get(category="signal").payload["title"] == "Titre au début"
    signal.refresh_from_db()
    assert signal.title == "Titre concurrent"


def test_historical_status_is_not_reconstructable_without_coverage():
    period_start, period_end = _period()
    establishment = create_establishment(
        name="Dossier sans journal fiable", timezone="Europe/Paris"
    )
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    signal = _signal(
        establishment,
        title="Ouvert",
        summary="Sans couverture.",
        created_at=_at(period_start + timedelta(days=2)),
    )
    record_signal_lifecycle_event(
        signal=signal,
        event_type=SIGNAL_LIFECYCLE_EVENT_CREATED,
        occurred_at=_at(period_start - timedelta(days=1)),
        metadata_safe={"to_status": Signal.Status.OPEN},
    )
    dossier = capture_dossier(_analysis(owner, reporting).id)
    payload = dossier.items.get(category="signal").payload
    assert payload["status_at_capture"]["value"] == Signal.Status.OPEN
    assert payload["status_at_period_start"] == {"value": "not_reconstructable"}
    assert payload["status_at_period_end"] == {"value": "not_reconstructable"}


@pytest.mark.slow
def test_capture_uses_the_admitted_budget_when_the_setting_changes(settings):
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 20
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier budget", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    analysis = _analysis(owner, reporting)
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 1
    dossier = capture_dossier(analysis.id, _pauses=(2,))
    assert dossier.closed_at is not None


@pytest.mark.slow
def test_two_injected_waits_fail_the_capture_and_leave_it_unclosed(settings):
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 20
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier delai", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    analysis = _analysis(owner, reporting)
    started = time.monotonic()
    with pytest.raises(CaptureTimeout):
        capture_dossier(analysis.id, _pauses=(12, 12))
    elapsed = time.monotonic() - started
    assert 12 < elapsed < 23
    assert not BrainDossier.objects.filter(analysis=analysis).exists()


@pytest.mark.slow
def test_a_statement_longer_than_the_remaining_budget_is_canceled(settings):
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 2
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier statement", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    analysis = _analysis(owner, reporting)
    started = time.monotonic()
    with pytest.raises(CaptureTimeout):
        capture_dossier(analysis.id, _pauses=(8,))
    assert time.monotonic() - started < 5
    assert not BrainDossier.objects.filter(analysis=analysis).exists()


def test_python_past_the_deadline_fails_at_the_next_check_and_leaves_the_dossier_unclosed(
    settings,
):
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 2
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier python", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    analysis = _analysis(owner, reporting)
    started = time.monotonic()

    def before_close():
        time.sleep(3)

    with pytest.raises(CaptureTimeout):
        capture_dossier(analysis.id, _before_close=before_close)
    elapsed = time.monotonic() - started
    assert elapsed >= 3
    assert elapsed < 8
    assert not BrainDossier.objects.filter(analysis=analysis).exists()


def test_a_closing_statement_longer_than_the_remaining_budget_is_canceled(settings):
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 2
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier ecriture", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    analysis = _analysis(owner, reporting)
    started = time.monotonic()
    with pytest.raises(CaptureTimeout):
        capture_dossier(analysis.id, _pauses_before_close=(8,))
    assert time.monotonic() - started < 5
    assert not BrainDossier.objects.filter(analysis=analysis).exists()


def test_commit_is_refused_when_python_exhausts_the_budget_after_the_closing_write(settings):
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 2
    period_start, period_end = _period()
    establishment = create_establishment(name="Dossier commit", timezone="Europe/Paris")
    owner = _owner(establishment)
    reporting = _reporting(establishment, owner.user, period_start, period_end)
    analysis = _analysis(owner, reporting)
    seen = {}

    def before_commit(budget):
        seen["remaining"] = budget.remaining()
        time.sleep(3)

    started = time.monotonic()
    with pytest.raises(CaptureTimeout):
        capture_dossier(analysis.id, _before_commit=before_commit)
    assert seen["remaining"] > 0
    assert time.monotonic() - started >= 3
    assert not BrainDossier.objects.filter(analysis=analysis).exists()
