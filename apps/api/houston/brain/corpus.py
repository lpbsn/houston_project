"""Seal the copies an investigation may search. Live tables are read only here.

The dossier can hold more than the model is shown. A family that does not fit
the capture ceiling is marked incomplete. A later search must call that
incomplete family unavailable, not empty.
"""

from __future__ import annotations

from datetime import datetime

from django.db.models import Q

from houston.action_plans.constants import EXECUTION_LIFECYCLE_METADATA_SAFE_KEYS
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionLifecycleEvent,
)
from houston.brain.collection import (
    CATEGORY_CONTEXT,
    CATEGORY_DOCUMENT,
    CATEGORY_EXECUTION,
    CATEGORY_OBJECTIVE,
    CATEGORY_PLAN,
    CATEGORY_REPORTING,
    CATEGORY_SIGNAL,
    ROLE_CURRENT_MEASURE,
    ROLE_CURRENT_QUALITATIVE,
    DossierRow,
    document_stable_key,
)
from houston.brain.comparability import freeze_measure
from houston.brain.mentions import first_explicit_mention
from houston.brain.models import (
    BrainAnalysis,
    BrainExtraction,
    BrainObjectiveRevision,
    BrainReporting,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    EstablishmentActivityDescription,
)
from houston.signals.constants import SIGNAL_LIFECYCLE_METADATA_SAFE_KEYS
from houston.signals.models import Signal, SignalLifecycleEvent

CATEGORY_COVERAGE = "coverage"
CATEGORY_ORGANIZATION = "organization"
CATEGORY_KNOWLEDGE = "knowledge"
CATEGORY_MEMORY = "analysis_memory"

_ACCEPTED = ("accepted", "modified")
_FAMILIES = ("signal", "plan", "execution", "objective", "reporting", "memory")


def assemble_investigation_corpus(
    *,
    analysis: BrainAnalysis,
    extraction_payload: dict,
    capture_at: datetime,
    reliable_from: datetime | None,
    ceiling: int,
    run,
) -> list[DossierRow]:
    """Copy one establishment as of ``capture_at``. Observations are not read."""
    establishment = analysis.establishment
    reporting = analysis.reporting
    rows: list[DossierRow] = []
    coverage = {
        "reference_at": capture_at.isoformat(),
        "reliable_from": reliable_from.isoformat() if reliable_from else None,
        "families": {},
    }
    signal_rows, signal_coverage = _signals(
        run,
        establishment_id=establishment.id,
        capture_at=capture_at,
        ceiling=ceiling,
    )
    execution_rows, execution_ids, execution_coverage = _executions(
        run,
        establishment_id=establishment.id,
        capture_at=capture_at,
        ceiling=ceiling,
    )
    plan_rows, plan_coverage = _plans(
        run,
        establishment_id=establishment.id,
        capture_at=capture_at,
        ceiling=ceiling,
        execution_ids=execution_ids,
        executions_complete=execution_coverage["complete"],
    )
    objective_rows, objective_coverage = _objectives(
        run,
        establishment_id=establishment.id,
        capture_at=capture_at,
        ceiling=ceiling,
    )
    reporting_rows, reporting_coverage = _prior_reportings(
        run,
        establishment_id=establishment.id,
        current_id=reporting.id,
        capture_at=capture_at,
        period_start=reporting.period_start,
        period_end=reporting.period_end,
        ceiling=ceiling,
    )
    memory_rows, memory_coverage = _memory(
        run,
        establishment_id=establishment.id,
        analysis_id=analysis.id,
        capture_at=capture_at,
        ceiling=ceiling,
    )
    coverage["families"] = {
        "signal": signal_coverage,
        "plan": plan_coverage,
        "execution": execution_coverage,
        "objective": objective_coverage,
        "reporting": reporting_coverage,
        "memory": memory_coverage,
    }
    rows.append(
        DossierRow(CATEGORY_COVERAGE, "coverage", "couverture", coverage, "instant_reference")
    )
    rows.extend(
        _documents(
            extraction_payload,
            period_start=reporting.period_start,
            period_end=reporting.period_end,
            reporting_id=str(reporting.id),
        )
    )
    rows.append(_organization(run, establishment))
    rows.append(_activity(run, establishment))
    rows.extend(_knowledge(analysis))
    rows.extend(signal_rows)
    rows.extend(plan_rows)
    rows.extend(execution_rows)
    rows.extend(objective_rows)
    rows.extend(reporting_rows)
    rows.extend(memory_rows)
    return rows


def _signals(run, *, establishment_id, capture_at, ceiling: int):
    predicate = Q(establishment_id=establishment_id, created_at__lte=capture_at)
    total = run(lambda: Signal.objects.filter(predicate).count())
    signals = run(
        lambda: list(
            Signal.objects.filter(predicate)
            .select_related(
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
            )
            .order_by("-created_at", "-id")[:ceiling]
        )
    )
    events = _signal_events(run, establishment_id, [row.id for row in signals], capture_at)
    items = []
    for signal in signals:
        mention = first_explicit_mention(
            title=signal.title,
            structured_summary=signal.structured_summary,
        )
        items.append(
            DossierRow(
                CATEGORY_SIGNAL,
                f"signal:{signal.id}",
                "copie",
                {
                    "source_id": str(signal.id),
                    "title": signal.title,
                    "structured_summary": signal.structured_summary,
                    "created_at": signal.created_at.isoformat(),
                    "location_text": signal.location_text,
                    "issue_focus": signal.issue_focus,
                    "expected_action": signal.expected_action,
                    "affected_business_unit": _unit(signal.affected_business_unit),
                    "responsible_business_unit": _unit(signal.responsible_business_unit),
                    "activity_subject": _activity_ref(signal.activity_subject),
                    "occurrence_date": mention.civil_date.isoformat() if mention else None,
                    "occurrence_provenance": mention.provenance() if mention else None,
                    "events": events.get(signal.id, []),
                },
                "signal_structure",
            )
        )
    return items, _family(total, len(signals))


def _executions(run, *, establishment_id, capture_at, ceiling: int):
    predicate = Q(establishment_id=establishment_id, created_at__lte=capture_at)
    total = run(lambda: ActionPlanExecution.objects.filter(predicate).count())
    rows = run(
        lambda: list(
            ActionPlanExecution.objects.filter(predicate)
            .select_related(
                "pilot_business_unit",
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
            )
            .order_by("-created_at", "-id")[:ceiling]
        )
    )
    events = _execution_events(run, establishment_id, [row.id for row in rows], capture_at)
    items = []
    for execution in rows:
        items.append(
            DossierRow(
                CATEGORY_EXECUTION,
                f"execution:{execution.id}",
                "copie",
                {
                    "source_id": str(execution.id),
                    "action_plan_id": _str(execution.action_plan_id),
                    "source_signal_id": _str(execution.source_signal_id),
                    "title": execution.title,
                    "description": execution.description,
                    "created_at": execution.created_at.isoformat(),
                    "occurrence_date": _iso(execution.occurrence_date),
                    "start_at": _iso(execution.start_at),
                    "end_at": _iso(execution.end_at),
                    "pilot_business_unit": _unit(execution.pilot_business_unit),
                    "affected_business_unit": _unit(execution.affected_business_unit),
                    "responsible_business_unit": _unit(execution.responsible_business_unit),
                    "activity_subject": _activity_ref(execution.activity_subject),
                    "events": events.get(execution.id, []),
                },
                "execution",
            )
        )
    return items, [row.id for row in rows], _family(total, len(rows))


def _plans(
    run,
    *,
    establishment_id,
    capture_at,
    ceiling: int,
    execution_ids,
    executions_complete: bool,
):
    predicate = Q(establishment_id=establishment_id, created_at__lte=capture_at)
    total = run(lambda: ActionPlan.objects.filter(predicate).count())
    plans = run(
        lambda: list(
            ActionPlan.objects.filter(predicate)
            .select_related(
                "pilot_business_unit",
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
            )
            .order_by("-created_at", "-id")[:ceiling]
        )
    )
    links = _plan_links(run, establishment_id, execution_ids)
    items = []
    for plan in plans:
        linked = links.get(plan.id, {"execution_ids": [], "source_signal_ids": []})
        items.append(
            DossierRow(
                CATEGORY_PLAN,
                f"plan:{plan.id}",
                "copie",
                {
                    "source_id": str(plan.id),
                    "title": plan.title,
                    "description": plan.description,
                    "created_at": plan.created_at.isoformat(),
                    "catalog_status_at_reference": plan.catalog_status,
                    "pilot_business_unit": _unit(plan.pilot_business_unit),
                    "affected_business_unit": _unit(plan.affected_business_unit),
                    "responsible_business_unit": _unit(plan.responsible_business_unit),
                    "activity_subject": _activity_ref(plan.activity_subject),
                    "execution_ids": linked["execution_ids"],
                    "source_signal_ids": linked["source_signal_ids"],
                    "links_complete": executions_complete,
                },
                "plan",
            )
        )
    return items, _family(total, len(plans))


def _objectives(run, *, establishment_id, capture_at, ceiling: int):
    latest = (
        BrainObjectiveRevision.objects.filter(
            establishment_id=establishment_id,
            created_at__lte=capture_at,
            decision__in=_ACCEPTED,
        )
        .order_by("objective_id", "-created_at", "-id")
        .distinct("objective_id")
    )
    total = run(latest.count)
    kept = run(lambda: list(latest[:ceiling]))
    items = []
    for revision in kept:
        items.append(
            DossierRow(
                CATEGORY_OBJECTIVE,
                f"objective-revision:{revision.id}",
                "copie",
                {
                    "source_id": str(revision.objective_id),
                    "revision_id": str(revision.id),
                    "indicator": revision.indicator,
                    "unit": revision.unit,
                    "scope": revision.scope,
                    "reference": revision.reference,
                    "target": revision.target,
                    "success_condition": revision.success_condition,
                    "decision": revision.decision,
                    "due_on": _iso(revision.due_on),
                    "measurement_period_start": _iso(revision.measurement_period_start),
                    "measurement_period_end": _iso(revision.measurement_period_end),
                    "method": revision.method,
                    "content_hash": revision.content_hash,
                    "created_at": revision.created_at.isoformat(),
                },
                "objectif_accepte",
            )
        )
    return items, _family(total, len(kept))


def _prior_reportings(
    run,
    *,
    establishment_id,
    current_id,
    capture_at,
    period_start,
    period_end,
    ceiling: int,
):
    predicate = Q(
        establishment_id=establishment_id,
        status=BrainReporting.Status.READY,
        period_start__isnull=False,
        period_end__isnull=False,
        period_confirmed_at__lte=capture_at,
    )
    total = run(
        lambda: BrainReporting.objects.filter(predicate).exclude(pk=current_id).count()
    )
    reportings = run(
        lambda: list(
            BrainReporting.objects.filter(predicate)
            .exclude(pk=current_id)
            .order_by("period_start", "id")[:ceiling]
        )
    )
    extractions = run(
        lambda: list(
            BrainExtraction.objects.filter(
                reporting_id__in=[row.id for row in reportings]
            ).order_by("reporting_id", "-created_at")
        )
    )
    by_reporting = {}
    for extraction in extractions:
        by_reporting.setdefault(extraction.reporting_id, extraction)
    items = []
    for reporting in reportings:
        extraction = by_reporting.get(reporting.id)
        measures = _measure_payloads(
            extraction.payload if extraction is not None else None,
            period_start=reporting.period_start,
            period_end=reporting.period_end,
        )
        if not measures:
            items.append(
                DossierRow(
                    CATEGORY_REPORTING,
                    f"prior-reporting:{reporting.id}",
                    "indisponible",
                    {
                        "source_id": str(reporting.id),
                        "source_kind": "document",
                        "availability": "unavailable",
                        "reason": "measures_not_captured",
                        "period_start": reporting.period_start.isoformat(),
                        "period_end": reporting.period_end.isoformat(),
                    },
                    "reporting_anterieur",
                )
            )
            continue
        for index, measure in enumerate(measures):
            items.append(
                DossierRow(
                    CATEGORY_REPORTING,
                    f"prior-measure:{reporting.id}:{index:04d}",
                    "reporting_anterieur",
                    {
                        **measure,
                        "source_kind": "document",
                        "availability": "available",
                        "reporting_id": str(reporting.id),
                        "reporting_period_start": reporting.period_start.isoformat(),
                        "reporting_period_end": reporting.period_end.isoformat(),
                    },
                    "reporting_anterieur",
                )
            )
    captured = len(reportings)
    return items, _family(total, captured)


def _memory(run, *, establishment_id, analysis_id, capture_at, ceiling: int):
    predicate = Q(
        establishment_id=establishment_id,
        status=BrainAnalysis.Status.COMPLETED,
        published_at__isnull=False,
        published_at__lte=capture_at,
    )
    total = run(lambda: BrainAnalysis.objects.filter(predicate).exclude(pk=analysis_id).count())
    analyses = run(
        lambda: list(
            BrainAnalysis.objects.filter(predicate)
            .exclude(pk=analysis_id)
            .only("id", "published_at", "result")
            .order_by("published_at", "id")[:ceiling]
        )
    )
    items = []
    for prior in analyses:
        available = isinstance(prior.result, dict)
        items.append(
            DossierRow(
                CATEGORY_MEMORY,
                f"memory:{prior.id}",
                "memoire",
                {
                    "source_id": str(prior.id),
                    "source_kind": "decision_memory",
                    "published_at": prior.published_at.isoformat(),
                    "availability": "available" if available else "unavailable",
                    "reason": "" if available else "result_not_captured",
                    "result": prior.result if available else None,
                },
                "memoire_decisionnelle",
            )
        )
    return items, _family(total, len(analyses))


def _documents(payload, *, period_start, period_end, reporting_id: str) -> list[DossierRow]:
    rows = []
    if not isinstance(payload, dict):
        return rows
    for index, block in enumerate(payload.get("qualitative") or []):
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or "")
        if not text.strip():
            continue
        locator = block.get("locator") if isinstance(block.get("locator"), dict) else {}
        rows.append(
            DossierRow(
                CATEGORY_DOCUMENT,
                document_stable_key("qualitative", index),
                ROLE_CURRENT_QUALITATIVE,
                {
                    "source_kind": "reporting",
                    "reporting_id": reporting_id,
                    "kind": str(block.get("kind") or "paragraph"),
                    "text": text,
                    "locator": locator,
                },
                "reporting_courant",
            )
        )
    measures = _measure_payloads(payload, period_start=period_start, period_end=period_end)
    for index, measure in enumerate(measures):
        rows.append(
            DossierRow(
                CATEGORY_DOCUMENT,
                document_stable_key("measure", index),
                ROLE_CURRENT_MEASURE,
                {**measure, "source_kind": "reporting", "reporting_id": reporting_id},
                "reporting_courant",
            )
        )
    return rows


def _organization(run, establishment) -> DossierRow:
    units = run(
        lambda: list(
            BusinessUnit.objects.filter(establishment_id=establishment.id).order_by(
                "specific_name", "id"
            )
        )
    )
    activities = run(
        lambda: list(
            ActivitySubject.objects.filter(establishment_id=establishment.id)
            .order_by("label", "id")
        )
    )
    return DossierRow(
        CATEGORY_ORGANIZATION,
        "organization",
        "organigramme",
        {
            "establishment_id": str(establishment.id),
            "name": establishment.name,
            "timezone": establishment.timezone,
            "business_units": [
                {"id": str(unit.id), "name": unit.specific_name, "active": unit.active}
                for unit in units
            ],
            "activities": [
                {
                    "id": str(activity.id),
                    "label": activity.label,
                    "business_unit_id": str(activity.business_unit_id),
                    "active": activity.active,
                }
                for activity in activities
            ],
        },
        "organigramme",
    )


def _activity(run, establishment) -> DossierRow:
    description = run(
        lambda: EstablishmentActivityDescription.objects.filter(
            establishment_id=establishment.id
        ).first()
    )
    text = (description.description if description is not None else "").strip()
    if description is None or not text:
        return DossierRow(
            CATEGORY_CONTEXT,
            "establishment-context",
            "absent",
            {"present": False, "availability": "available"},
            "contexte_etablissement",
        )
    return DossierRow(
        CATEGORY_CONTEXT,
        "establishment-context",
        "copie",
        {
            "present": True,
            "availability": "available",
            "source_id": str(description.id),
            "text": text,
        },
        "contexte_etablissement",
    )


def _knowledge(analysis: BrainAnalysis) -> list[DossierRow]:
    """Seal the mechanisms copied at admission. A later activation is not reread."""
    config = analysis.configuration if isinstance(analysis.configuration, dict) else {}
    mechanisms = config.get("mechanisms")
    if not isinstance(mechanisms, list):
        return []
    rows = []
    for mechanism in mechanisms:
        if not isinstance(mechanism, dict):
            continue
        version_id = str(mechanism.get("version_id") or "").strip()
        if not version_id:
            continue
        rows.append(
            DossierRow(
                CATEGORY_KNOWLEDGE,
                f"knowledge:{version_id}",
                "actif",
                {
                    "source_id": version_id,
                    "identifier": mechanism.get("identifier") or "",
                    "formulation": mechanism.get("formulation") or "",
                    "conditions": mechanism.get("conditions") or "",
                    "limits": mechanism.get("limits") or "",
                    "uncertainty": mechanism.get("uncertainty") or "",
                },
                "knowledge_actif",
            )
        )
    return rows


def _measure_payloads(payload, *, period_start, period_end) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    measures = []
    for index, raw in enumerate(payload.get("measures") or []):
        if not isinstance(raw, dict):
            continue
        frozen = freeze_measure(
            raw,
            measure_id=f"measure:{index:04d}",
            period_start=period_start,
            period_end=period_end,
        )
        measures.append(frozen)
    return measures


def _signal_events(run, establishment_id, signal_ids, capture_at) -> dict:
    if not signal_ids:
        return {}
    rows = run(
        lambda: list(
            SignalLifecycleEvent.objects.filter(
                establishment_id=establishment_id,
                signal_id__in=signal_ids,
                occurred_at__lte=capture_at,
            ).order_by("occurred_at", "id")
        )
    )
    grouped: dict = {}
    for row in rows:
        metadata = row.metadata_safe if isinstance(row.metadata_safe, dict) else {}
        grouped.setdefault(row.signal_id, []).append(
            {
                "event_type": row.event_type,
                "occurred_at": row.occurred_at.isoformat(),
                "metadata": {
                    key: metadata[key]
                    for key in SIGNAL_LIFECYCLE_METADATA_SAFE_KEYS
                    if key in metadata and metadata[key] is not None
                },
            }
        )
    return grouped


def _execution_events(run, establishment_id, execution_ids, capture_at) -> dict:
    if not execution_ids:
        return {}
    rows = run(
        lambda: list(
            ActionPlanExecutionLifecycleEvent.objects.filter(
                establishment_id=establishment_id,
                action_plan_execution_id__in=execution_ids,
                occurred_at__lte=capture_at,
            ).order_by("occurred_at", "id")
        )
    )
    grouped: dict = {}
    for row in rows:
        metadata = row.metadata_safe if isinstance(row.metadata_safe, dict) else {}
        grouped.setdefault(row.action_plan_execution_id, []).append(
            {
                "event_type": row.event_type,
                "occurred_at": row.occurred_at.isoformat(),
                "metadata": {
                    key: metadata[key]
                    for key in EXECUTION_LIFECYCLE_METADATA_SAFE_KEYS
                    if key in metadata and metadata[key] is not None
                },
            }
        )
    return grouped


def _plan_links(run, establishment_id, execution_ids) -> dict:
    if not execution_ids:
        return {}
    rows = run(
        lambda: list(
            ActionPlanExecution.objects.filter(
                establishment_id=establishment_id,
                id__in=execution_ids,
                action_plan_id__isnull=False,
            ).values("id", "action_plan_id", "source_signal_id")
        )
    )
    grouped: dict = {}
    for row in rows:
        bucket = grouped.setdefault(
            row["action_plan_id"],
            {"execution_ids": [], "source_signal_ids": []},
        )
        bucket["execution_ids"].append(str(row["id"]))
        if row["source_signal_id"] is not None:
            bucket["source_signal_ids"].append(str(row["source_signal_id"]))
    return grouped


def _family(total: int, captured: int) -> dict:
    omitted = max(0, total - captured)
    return {"complete": omitted == 0, "captured": captured, "omitted": omitted}


def _unit(unit) -> dict | None:
    if unit is None:
        return None
    return {"id": str(unit.id), "name": unit.specific_name}


def _activity_ref(activity) -> dict | None:
    if activity is None:
        return None
    return {"id": str(activity.id), "label": activity.label}


def _iso(value) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _str(value) -> str | None:
    if value is None:
        return None
    return str(value)

