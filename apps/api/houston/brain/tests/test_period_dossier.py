"""Period dossier capture, frozen copies, and worker reload. No provider call."""

from __future__ import annotations

import inspect
import json
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from houston.action_plans.models import ActionPlan, ActionPlanExecution
from houston.analytics.models import AnalyticsHistoryCoverage
from houston.brain import runtime
from houston.brain.admission import admit_brain_work
from houston.brain.capture import capture_period_dossier
from houston.brain.dossier import (
    SEARCH_READING,
    SEARCH_UNIVERSE,
    open_indexed_copy,
    prepare_first_reading,
    reload_period_dossier,
    reload_unexamined,
)
from houston.brain.investigation import (
    QUALIFICATION_COMPLETE,
    QUALIFICATION_REFUSED,
    InvestigationFacts,
    SubjectFinding,
    investigation_engine,
    qualify,
)
from houston.brain.models import BrainDossierItem, BrainExtraction, BrainReporting, BrainSearchRun
from houston.brain.period import (
    LIMIT_PERIOD_EXCEEDS_CALL,
    PeriodSnapshotError,
    reading_allowance,
    reading_input_tokens,
    select_first_reading,
)
from houston.brain.records import EXTRACTOR_ID, EXTRACTOR_VERSION
from houston.comments.models import Comment
from houston.establishments.models import EstablishmentMembership
from houston.observations.models import Observation
from houston.signals.constants import (
    SIGNAL_LIFECYCLE_EVENT_CREATED,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
)
from houston.signals.lifecycle_events import record_signal_lifecycle_event
from houston.signals.models import Signal, SignalLifecycleEvent, SignalSourceObservation
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db(transaction=True)

PERIOD_START = date(2026, 3, 1)
PERIOD_END = date(2026, 3, 8)
SUBJECT_START = date(2026, 3, 5)
SUBJECT_END = date(2026, 3, 8)
PARIS = "Europe/Paris"
PARIS_TZ = ZoneInfo(PARIS)

FORBIDDEN = (
    "OBSERVATION-BRUTE",
    "COMMENTAIRE-BRUT",
    "DESCRIPTION-EXECUTION",
    "DESCRIPTION-PLAN",
    "JUSTIFICATION-OBJECTIF",
    "ANCIEN-DISTRACTEUR",
    "SIGNAL-N-1",
    "AUTRE-ETABLISSEMENT",
    "MODIFIE-APRES-CAPTURE",
    "SANS-DATE-TARDIVE",
    "CREE-APRES-CAPTURE",
    "OBJECTIF-HORS-SERIE",
    "PENDANT-CAPTURE",
    "APRES-REPRISE",
)


def _at(day: date, hour: int = 12):
    return datetime(day.year, day.month, day.day, hour, tzinfo=PARIS_TZ)


def _signal(
    establishment,
    *,
    title,
    summary,
    created_at,
    business_unit=None,
    status=Signal.Status.OPEN,
    resolved_at=None,
):
    signal = Signal.objects.create(
        establishment=establishment,
        affected_business_unit=business_unit,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary=summary,
        issue_focus=f"focus-{uuid.uuid4().hex[:12]}",
        location_text="Salle 12",
        last_activity_at=created_at,
        status=status,
        resolved_at=resolved_at,
    )
    Signal.objects.filter(pk=signal.pk).update(
        created_at=created_at,
        updated_at=created_at,
        last_activity_at=created_at,
    )
    signal.refresh_from_db()
    return signal


def _world(settings):
    settings.HOUSTON_BRAIN_CAPTURE_TIMEOUT_SECONDS = 30
    establishment = create_establishment(name="Periode Paris", timezone=PARIS)
    other = create_establishment(name="Autre site", timezone=PARIS)
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    restaurant = create_business_unit(
        establishment=establishment,
        key="restauration_periode",
        label="Restauration",
    )
    housing = create_business_unit(
        establishment=establishment,
        key="hebergement_periode",
        label="Hebergement",
    )
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
                    "raw_text": "OBSERVATION-BRUTE",
                }
            ],
            "qualitative": [{"kind": "paragraph", "text": "Baisse de frequentation en salle."}],
        },
    )
    s01 = _signal(
        establishment,
        title="Service salle",
        summary="PREUVE-SALLE",
        created_at=_at(SUBJECT_START),
        business_unit=restaurant,
        status=Signal.Status.RESOLVED,
        resolved_at=timezone.now() + timedelta(days=2),
    )
    record_signal_lifecycle_event(
        signal=s01,
        event_type=SIGNAL_LIFECYCLE_EVENT_CREATED,
        occurred_at=_at(SUBJECT_START),
        metadata_safe={"to_status": Signal.Status.OPEN},
    )
    record_signal_lifecycle_event(
        signal=s01,
        event_type=SIGNAL_LIFECYCLE_EVENT_RESOLVED,
        occurred_at=timezone.now() + timedelta(days=2),
        metadata_safe={"to_status": Signal.Status.RESOLVED},
    )
    s02 = _signal(
        establishment,
        title="Clients heberges",
        summary="PISTE-HEBERGEMENT",
        created_at=_at(SUBJECT_START),
        business_unit=housing,
        status=Signal.Status.RESOLVED,
        resolved_at=_at(date(2026, 3, 7)),
    )
    long_restaurant = _signal(
        establishment,
        title="Longue salle",
        summary="LONG-RESTAURATION",
        created_at=_at(PERIOD_START),
        business_unit=restaurant,
        status=Signal.Status.RESOLVED,
        resolved_at=_at(date(2026, 3, 7)),
    )
    long_housing = _signal(
        establishment,
        title="Long hebergement",
        summary="LONG-HEBERGEMENT",
        created_at=_at(PERIOD_START),
        business_unit=housing,
        status=Signal.Status.RESOLVED,
        resolved_at=_at(date(2026, 3, 7)),
    )
    short_restaurant = _signal(
        establishment,
        title="Incident court",
        summary="REMPLISSAGE-SALLE",
        created_at=_at(SUBJECT_START),
        business_unit=restaurant,
        status=Signal.Status.RESOLVED,
        resolved_at=_at(SUBJECT_START, hour=18),
    )
    modified = _signal(
        establishment,
        title="Deja modifie",
        summary="MODIFIE-APRES-CAPTURE",
        created_at=_at(SUBJECT_START),
        business_unit=restaurant,
    )
    Signal.objects.filter(pk=modified.pk).update(updated_at=timezone.now() + timedelta(days=2))
    late = _signal(
        establishment,
        title="Declaration tardive",
        summary="Vu le 2026-03-04 au matin.",
        created_at=_at(date(2026, 3, 10)),
        business_unit=restaurant,
    )
    _signal(
        establishment,
        title="Sans date",
        summary="SANS-DATE-TARDIVE",
        created_at=_at(date(2026, 3, 11)),
    )
    ancient = _signal(
        establishment,
        title="Ancien",
        summary="ANCIEN-DISTRACTEUR",
        created_at=_at(date(2024, 1, 2)),
        status=Signal.Status.RESOLVED,
        resolved_at=_at(date(2024, 1, 4)),
    )
    _signal(
        establishment,
        title="Annee precedente",
        summary="SIGNAL-N-1",
        created_at=_at(date(2025, 3, 3)),
        status=Signal.Status.RESOLVED,
        resolved_at=_at(date(2025, 3, 6)),
    )
    future = _signal(
        establishment,
        title="Pas encore la",
        summary="CREE-APRES-CAPTURE",
        created_at=_at(SUBJECT_START),
        business_unit=restaurant,
    )
    Signal.objects.filter(pk=future.pk).update(
        created_at=timezone.now() + timedelta(days=2),
        updated_at=timezone.now(),
    )
    _signal(
        other,
        title="Hors etablissement",
        summary="AUTRE-ETABLISSEMENT",
        created_at=_at(SUBJECT_START),
    )
    observation = Observation.objects.create(
        establishment=establishment,
        submitted_by_membership=owner,
        raw_text="OBSERVATION-BRUTE au 04/03/2026",
        client_submission_id=uuid.uuid4(),
        submitted_at=timezone.now(),
    )
    SignalSourceObservation.objects.create(
        signal=s01,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    Comment.objects.create(
        establishment=establishment,
        signal=s01,
        author_membership=owner,
        body="COMMENTAIRE-BRUT sur la salle",
    )
    plan = ActionPlan.objects.create(
        establishment=establishment,
        created_by=owner,
        pilot_business_unit=restaurant,
        title="PLAN-LIE",
        description="DESCRIPTION-PLAN",
        is_reusable=False,
    )
    ActionPlanExecution.objects.create(
        action_plan=plan,
        establishment=establishment,
        created_by=owner,
        source_signal=s01,
        title="EXECUTION-LIEE",
        description="DESCRIPTION-EXECUTION",
        pilot_business_unit=restaurant,
        affected_business_unit=restaurant,
        requires_validation=False,
        use_shared_chronology=True,
        last_activity_at=_at(SUBJECT_START),
        occurrence_date=SUBJECT_START,
    )
    from houston.brain.objectives import record_objective_revision

    record_objective_revision(
        establishment=establishment,
        indicator="frequentation",
        unit="couverts",
        scope="Restauration",
        target="stable",
        measurement_period_start=PERIOD_START,
        measurement_period_end=PERIOD_END,
        justification="JUSTIFICATION-OBJECTIF",
    )
    record_objective_revision(
        establishment=establishment,
        indicator="spa",
        target="OBJECTIF-HORS-SERIE",
        measurement_period_start=PERIOD_START,
        measurement_period_end=PERIOD_END,
    )
    AnalyticsHistoryCoverage.objects.update_or_create(
        singleton_key=AnalyticsHistoryCoverage.SINGLETON_KEY,
        defaults={"reliable_from": _at(date(2020, 1, 1))},
    )
    analysis = admit_brain_work(
        user=owner.user,
        establishment_id=establishment.id,
        reporting_id=reporting.id,
        idempotency_key="periode-v3",
    )
    return {
        "analysis": analysis,
        "s01": s01,
        "s02": s02,
        "long_restaurant": long_restaurant,
        "long_housing": long_housing,
        "short_restaurant": short_restaurant,
        "modified": modified,
        "late": late,
        "ancient": ancient,
    }


def _blob(analysis) -> str:
    parts = [
        json.dumps(item.payload, ensure_ascii=False, default=str)
        for item in BrainDossierItem.objects.filter(dossier__analysis=analysis)
    ]
    parts.extend(
        json.dumps(run.criteria, ensure_ascii=False, default=str)
        for run in BrainSearchRun.objects.filter(dossier__analysis=analysis)
    )
    return "\n".join(parts)


def _copy(snapshot, source_id: str):
    return next(item for item in snapshot.copies if item.source_id == source_id)


def test_period_capture_persists_immutable_copies_and_a_worker_reloads_them(settings):
    world = _world(settings)
    analysis = world["analysis"]
    s01 = world["s01"]

    def rewrite_during_capture():
        Signal.objects.filter(pk=s01.pk).update(
            title="PENDANT-CAPTURE",
            structured_summary="PENDANT-CAPTURE",
        )

    with CaptureQueriesContext(connection) as capture_queries:
        dossier = capture_period_dossier(analysis.id, _before_close=rewrite_during_capture)
    capture_sql = "\n".join(query["sql"] for query in capture_queries.captured_queries)
    stored = _blob(analysis)
    s01.refresh_from_db()
    index_row = BrainDossierItem.objects.get(
        dossier=dossier,
        category="period_index",
        stable_key=f"index:{s01.id}",
    )
    universe = BrainSearchRun.objects.get(dossier=dossier, code=SEARCH_UNIVERSE)
    codes = {row["source_id"]: row["code"] for row in universe.criteria["exclusions"]}

    assert investigation_engine(analysis.configuration) is False
    assert "capture_period_dossier" not in inspect.getsource(runtime)
    assert dossier.closed_at is not None
    assert Observation._meta.db_table not in capture_sql
    assert SignalSourceObservation._meta.db_table not in capture_sql
    assert Comment._meta.db_table not in capture_sql
    for marker in FORBIDDEN:
        assert marker not in stored
    assert "PREUVE-SALLE" in stored
    assert "PISTE-HEBERGEMENT" in stored
    assert "raw_text" not in stored
    assert "issue_focus" not in stored
    assert s01.issue_focus not in stored
    assert s01.status == Signal.Status.RESOLVED
    assert s01.structured_summary == "PENDANT-CAPTURE"
    assert "structured_summary" not in index_row.payload
    assert "PREUVE-SALLE" not in json.dumps(index_row.payload)
    assert codes[str(world["modified"].id)] == "modified_after_capture"
    assert "MODIFIE-APRES-CAPTURE" not in json.dumps(universe.criteria)

    Signal.objects.filter(pk=s01.pk).update(
        title="APRES-REPRISE",
        structured_summary="APRES-REPRISE",
    )
    with CaptureQueriesContext(connection) as reload_queries:
        snapshot = reload_period_dossier(analysis.id)
        opened = open_indexed_copy(snapshot, str(s01.id))
    reload_sql = "\n".join(query["sql"] for query in reload_queries.captured_queries)
    kept = _copy(snapshot, str(s01.id))
    late = _copy(snapshot, str(world["late"].id))
    live_tables = (
        Signal._meta.db_table,
        SignalLifecycleEvent._meta.db_table,
        SignalSourceObservation._meta.db_table,
        Observation._meta.db_table,
        Comment._meta.db_table,
        ActionPlan._meta.db_table,
        ActionPlanExecution._meta.db_table,
    )

    assert kept.payload["structured_summary"] == "PREUVE-SALLE"
    assert kept.payload["title"] == "Service salle"
    assert kept.start == SUBJECT_START
    assert kept.end == PERIOD_END
    assert kept.payload["status_at_period_end"]["value"] == "open"
    assert all(
        datetime.fromisoformat(event["occurred_at"]) <= dossier.capture_started_at
        for event in kept.payload["events"]
    )
    assert late.role == "declaration_tardive"
    assert _copy(snapshot, str(world["long_restaurant"].id)).start == PERIOD_START
    assert (kept.end - kept.start).days < (
        _copy(snapshot, str(world["long_restaurant"].id)).end
        - _copy(snapshot, str(world["long_restaurant"].id)).start
    ).days
    assert opened.payload["structured_summary"] == "PREUVE-SALLE"
    assert "APRES-REPRISE" not in json.dumps(kept.payload)
    for table in live_tables:
        assert table not in reload_sql
    with pytest.raises(PeriodSnapshotError) as missing:
        open_indexed_copy(snapshot, str(world["ancient"].id))
    assert missing.value.code == "outside_index"

    representatives = (str(s01.id), str(world["s02"].id))
    instructions = "Lis le reporting puis un signal de chaque pole."
    schema = {"type": "object", "properties": {"constats": {"type": "array"}}}
    opened = select_first_reading(
        snapshot,
        subject_pole="Restauration",
        subject_start=SUBJECT_START,
        subject_end=SUBJECT_END,
        input_token_budget=10**9,
    )
    payload_cost = reading_input_tokens(snapshot, opened.representative_ids)
    reserved = reading_allowance(
        instructions=instructions,
        schema=schema,
        per_call_input_tokens=payload_cost + 10**6,
    )
    reading = prepare_first_reading(
        analysis.id,
        subject_pole="Restauration",
        subject_start=SUBJECT_START,
        subject_end=SUBJECT_END,
        instructions=instructions,
        schema=schema,
        per_call_input_tokens=payload_cost + reserved.overhead_tokens,
    )
    refused = select_first_reading(
        snapshot,
        subject_pole="Restauration",
        subject_start=SUBJECT_START,
        subject_end=SUBJECT_END,
        allowance=reading_allowance(
            instructions=instructions,
            schema=schema,
            per_call_input_tokens=payload_cost + reserved.overhead_tokens - 1,
        ),
    )
    with CaptureQueriesContext(connection) as discovery_queries:
        discovered_rows = reload_unexamined(analysis.id)
        reloaded = reload_period_dossier(analysis.id)
        filler = open_indexed_copy(reloaded, str(world["long_restaurant"].id))
    discovery_sql = "\n".join(query["sql"] for query in discovery_queries.captured_queries)
    discovered_ids = [row["source_id"] for row in discovered_rows]
    note = json.dumps(discovered_rows, ensure_ascii=False)
    blocked = qualify(
        InvestigationFacts(
            subjects=(
                SubjectFinding(
                    key="frequentation",
                    examined=True,
                    affirmative=True,
                    verified_analytical=True,
                    cause_established=True,
                ),
            ),
            competing_period_lead_excluded=refused.competing_period_lead_excluded,
        )
    )

    assert opened.representative_ids == representatives
    assert reading.launched is True
    assert reading.examined_ids == representatives
    assert reading.input_tokens == payload_cost + reserved.overhead_tokens
    assert reserved.overhead_tokens > reserved.framing_tokens
    assert discovered_ids[0] == str(world["long_restaurant"].id)
    assert discovered_ids.index(str(world["long_restaurant"].id)) < discovered_ids.index(
        str(world["long_housing"].id)
    )
    assert str(world["s02"].id) not in discovered_ids
    assert "PISTE-HEBERGEMENT" in json.dumps(reading.payload)
    assert "LONG-RESTAURATION" not in json.dumps(reading.payload)
    assert "LONG-RESTAURATION" not in note
    assert "structured_summary" not in note
    assert filler.payload["structured_summary"] == "LONG-RESTAURATION"
    assert refused.launched is False
    assert refused.limit == LIMIT_PERIOD_EXCEEDS_CALL
    assert refused.payload is None
    assert any(
        item.source_id == str(world["s02"].id) and item.pole == "Hebergement"
        for item in refused.discovered_not_examined
    )
    assert blocked.qualification == QUALIFICATION_REFUSED
    assert blocked.qualification != QUALIFICATION_COMPLETE
    assert BrainSearchRun.objects.filter(dossier=dossier, code=SEARCH_READING).count() == 1
    for table in live_tables:
        assert table not in discovery_sql
