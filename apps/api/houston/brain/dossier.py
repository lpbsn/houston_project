"""Persist a period snapshot and reload it without the live tables.

The current executor still closes a dossier through ``capture_dossier``.
This module copies one period inside that same kind of short transaction,
then lets a worker read the copies back. It does not call a provider, open
a deepening, or publish a result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction

from houston.action_plans.constants import EXECUTION_LIFECYCLE_METADATA_SAFE_KEYS
from houston.action_plans.models import (
    ActionPlanExecution,
    ActionPlanExecutionLifecycleEvent,
)
from houston.analytics.journal import (
    JournalEvent,
    execution_status_at,
    signal_status_at,
)
from houston.brain.collection import (
    _bounded,
    _journal_events,
    _measures,
    _named,
    _public_event,
    _specific,
    _status_at,
    _window,
    _zone,
    execution_overlap_q,
    signal_overlap_q,
)
from houston.brain.comparability import freeze_measure
from houston.brain.errors import BrainWorkError
from houston.brain.investigation import PER_CALL_INPUT_TOKENS, historical_copy_decision
from houston.brain.models import (
    BrainDossier,
    BrainDossierItem,
    BrainObjective,
    BrainSearchRun,
)
from houston.brain.numbers import fold
from houston.brain.period import (
    CATEGORY_EXECUTION,
    CATEGORY_MEMORY,
    CATEGORY_OBJECTIVE,
    CATEGORY_PLAN,
    CATEGORY_SIGNAL,
    FirstReading,
    PeriodCopy,
    PeriodOmission,
    PeriodSnapshot,
    PeriodSnapshotError,
    PeriodSource,
    _clone_copy,
    _index_for,
    freeze_period_snapshot,
    reading_allowance,
    resume_period_snapshot,
    select_first_reading,
)
from houston.signals.constants import SIGNAL_LIFECYCLE_METADATA_SAFE_KEYS
from houston.signals.models import Signal, SignalLifecycleEvent

SEARCH_UNIVERSE = "univers_periode"
SEARCH_READING = "premiere_lecture"
CATEGORY_REPORTING = "reporting"
CATEGORY_SERIES = "series"
CATEGORY_INDEX = "period_index"

_COPY_CATEGORIES = frozenset(
    {CATEGORY_SIGNAL, CATEGORY_EXECUTION, CATEGORY_PLAN, CATEGORY_OBJECTIVE}
)


@dataclass(frozen=True)
class AssembledPeriod:
    snapshot: PeriodSnapshot
    examined_count: int


def assemble_period_snapshot(
    *,
    establishment,
    reporting,
    extraction_payload: dict,
    capture_at: datetime,
    reliable_from: datetime | None,
    ceiling: int,
    run,
) -> AssembledPeriod:
    """Read one establishment's period. Prior years and observations are not loaded."""
    tz = _zone(establishment.timezone)
    period = _window(reporting.period_start, reporting.period_end, tz)
    reporting_payload = _reporting_payload(reporting, extraction_payload)
    series = _series_payloads(reporting_payload["measures"])
    signals = _period_signals(
        run,
        establishment_id=establishment.id,
        period=period,
        capture_at=capture_at,
        ceiling=ceiling,
    )
    copied_signal_ids = [
        row.id for row in signals if _timestamp_allows(row.created_at, row.updated_at, capture_at)
    ]
    signal_events = _signal_events(run, establishment.id, copied_signal_ids, capture_at)
    executions = _period_executions(
        run,
        establishment_id=establishment.id,
        period=period,
        capture_at=capture_at,
        ceiling=ceiling,
    )
    copied_execution_ids = [
        row.id
        for row in executions
        if _timestamp_allows(row.created_at, row.updated_at, capture_at)
    ]
    execution_events = _execution_events(run, establishment.id, copied_execution_ids, capture_at)
    plans = _linked_plans(
        run,
        establishment_id=establishment.id,
        signal_ids=copied_signal_ids,
        ceiling=ceiling,
    )
    objectives = _objective_rows(
        run,
        establishment_id=establishment.id,
        ceiling=ceiling,
    )
    sources = (
        tuple(
            _signal_source(
                row,
                tz=tz,
                period=period,
                capture_at=capture_at,
                events=signal_events.get(row.id, []),
                reliable_from=reliable_from,
            )
            for row in signals
        )
        + tuple(
            _execution_source(
                row,
                tz=tz,
                period=period,
                capture_at=capture_at,
                events=execution_events.get(row.id, []),
                reliable_from=reliable_from,
            )
            for row in executions
        )
        + tuple(_plan_source(row, tz=tz, capture_at=capture_at) for row in plans)
        + tuple(_objective_source(row, capture_at=capture_at) for row in objectives)
    )
    snapshot = freeze_period_snapshot(
        capture_at=capture_at,
        period_start=reporting.period_start,
        period_end=reporting.period_end,
        reporting=reporting_payload,
        series=series,
        sources=sources,
    )
    return AssembledPeriod(snapshot=snapshot, examined_count=len(sources))


def persist_period_contents(dossier: BrainDossier, assembled: AssembledPeriod) -> None:
    """Write the frozen copies, the period index, and the omissions. No live row."""
    snapshot = assembled.snapshot
    items = [
        BrainDossierItem(
            dossier=dossier,
            category=CATEGORY_REPORTING,
            stable_key=f"reporting:{snapshot.reporting.get('source_id') or dossier.id}",
            role="periode",
            payload=snapshot.reporting,
            reason="reporting_courant",
        )
    ]
    for row in snapshot.series:
        key = str(row.get("series_key") or "")
        items.append(
            BrainDossierItem(
                dossier=dossier,
                category=CATEGORY_SERIES,
                stable_key=f"series:{key}",
                role="serie",
                payload=row,
                reason="serie_reporting",
            )
        )
    for row in snapshot.objectives:
        items.append(
            BrainDossierItem(
                dossier=dossier,
                category=CATEGORY_OBJECTIVE,
                stable_key=f"objective:{row.get('source_id')}",
                role="serie_correspondante",
                payload=row,
                reason="objectif_serie",
            )
        )
    indexed = {entry.source_id: entry for entry in snapshot.index}
    for copy in snapshot.copies:
        items.append(
            BrainDossierItem(
                dossier=dossier,
                category=copy.category,
                stable_key=f"{copy.category}:{copy.source_id}",
                role=copy.role,
                payload=copy.payload,
                reason="copie_periode",
            )
        )
        entry = indexed.get(copy.source_id)
        if entry is None:
            continue
        items.append(
            BrainDossierItem(
                dossier=dossier,
                category=CATEGORY_INDEX,
                stable_key=f"index:{copy.source_id}",
                role=copy.role,
                payload=entry.as_record(),
                reason="index_periode",
            )
        )
    BrainDossierItem.objects.bulk_create(items)
    BrainSearchRun.objects.create(
        dossier=dossier,
        code=SEARCH_UNIVERSE,
        criteria={
            "exclusions": [
                {"source_id": item.source_id, "code": item.code} for item in snapshot.omissions
            ]
        },
        examined_count=assembled.examined_count,
        retained_count=len(snapshot.copies),
    )


def reload_period_dossier(analysis_id) -> PeriodSnapshot:
    """Rebuild the snapshot from the closed dossier. Live sources are not queried."""
    dossier = (
        BrainDossier.objects.filter(analysis_id=analysis_id, closed_at__isnull=False)
        .only("id", "capture_started_at", "period_start", "period_end")
        .first()
    )
    if dossier is None:
        raise BrainWorkError(
            code="dossier_not_closed",
            message="Le dossier de période n'est pas fermé.",
        )
    items = list(
        BrainDossierItem.objects.filter(dossier_id=dossier.id).only("category", "role", "payload")
    )
    universe = (
        BrainSearchRun.objects.filter(dossier_id=dossier.id, code=SEARCH_UNIVERSE)
        .only("criteria")
        .first()
    )
    snapshot = _snapshot_from_items(dossier, items, universe.criteria if universe else {})
    return resume_period_snapshot(snapshot)


def prepare_first_reading(
    analysis_id,
    *,
    subject_pole: str,
    subject_start: date,
    subject_end: date,
    instructions: str = "",
    schema: object | None = None,
    per_call_input_tokens: int = PER_CALL_INPUT_TOKENS,
    provider: str = "fake",
    model: str = "fake",
) -> FirstReading:
    """Select from the frozen dossier and store the unexamined candidates.

    The note keeps identifiers and poles. It does not keep their summaries,
    and it does not open a deepening.
    """
    snapshot = reload_period_dossier(analysis_id)
    allowance = reading_allowance(
        instructions=instructions,
        schema=schema,
        per_call_input_tokens=per_call_input_tokens,
        provider=provider,
        model=model,
    )
    reading = select_first_reading(
        snapshot,
        subject_pole=subject_pole,
        subject_start=subject_start,
        subject_end=subject_end,
        allowance=allowance,
        provider=provider,
        model=model,
    )
    _store_reading(analysis_id, reading)
    return reading


def reload_unexamined(analysis_id) -> tuple[dict, ...]:
    """Candidates left unread. Summaries are not in this note."""
    run = (
        BrainSearchRun.objects.filter(
            dossier__analysis_id=analysis_id,
            dossier__closed_at__isnull=False,
            code=SEARCH_READING,
        )
        .only("criteria")
        .first()
    )
    if run is None:
        raise BrainWorkError(
            code="reading_not_prepared",
            message="La découverte de la première lecture n'est pas enregistrée.",
        )
    criteria = run.criteria if isinstance(run.criteria, dict) else {}
    rows = criteria.get("discovered_not_examined") or []
    if not isinstance(rows, list):
        raise BrainWorkError(
            code="reading_not_prepared",
            message="La découverte de la première lecture n'est pas enregistrée.",
        )
    return tuple(row for row in rows if isinstance(row, dict))


def open_indexed_copy(snapshot: PeriodSnapshot, source_id: str):
    """Frozen copy of an identifier already in the period index.

    A later deepening will use this instead of the live row. An identifier
    that was never indexed is refused.
    """
    if source_id not in {entry.source_id for entry in snapshot.index}:
        raise PeriodSnapshotError("outside_index")
    for item in snapshot.copies:
        if item.source_id == source_id:
            return _clone_copy(item)
    raise PeriodSnapshotError("outside_index")


def _store_reading(analysis_id, reading: FirstReading) -> None:
    dossier = (
        BrainDossier.objects.filter(analysis_id=analysis_id, closed_at__isnull=False)
        .only("id")
        .first()
    )
    if dossier is None:
        raise BrainWorkError(
            code="dossier_not_closed",
            message="Le dossier de période n'est pas fermé.",
        )
    record = reading.search_record()
    considered = len(reading.examined_ids) + len(reading.discovered_not_examined)
    with transaction.atomic():
        BrainSearchRun.objects.update_or_create(
            dossier_id=dossier.id,
            code=SEARCH_READING,
            defaults={
                "criteria": record,
                "examined_count": considered,
                "retained_count": len(reading.examined_ids),
            },
        )


def _snapshot_from_items(dossier, items, criteria: object) -> PeriodSnapshot:
    reporting = None
    series = []
    objectives = []
    copies_by_id = {}
    index_by_id = {}
    for item in items:
        payload = item.payload if isinstance(item.payload, dict) else {}
        if item.category == CATEGORY_REPORTING:
            reporting = payload
        elif item.category == CATEGORY_SERIES:
            series.append(payload)
        elif item.category == CATEGORY_OBJECTIVE:
            objectives.append(payload)
        elif item.category == CATEGORY_INDEX:
            source_id = str(payload.get("source_id") or "")
            if source_id:
                index_by_id[source_id] = payload
        elif item.category == CATEGORY_MEMORY or item.category in _COPY_CATEGORIES:
            source_id = str(payload.get("source_id") or "")
            if source_id:
                copies_by_id[source_id] = (item, payload)
    if not isinstance(reporting, dict):
        raise BrainWorkError(
            code="period_dossier_unreadable",
            message="La copie du reporting est absente du dossier.",
        )
    copies = []
    for source_id, (item, payload) in copies_by_id.items():
        if item.category == CATEGORY_OBJECTIVE:
            continue
        if item.category == CATEGORY_MEMORY:
            copies.append(_memory_copy(item.role, payload))
            continue
        indexed = index_by_id.get(source_id)
        if indexed is None:
            raise BrainWorkError(
                code="period_index_incomplete",
                message="L'index de période ne couvre pas une copie.",
            )
        copies.append(_stored_copy(item.category, item.role, payload, indexed))
    ordered = tuple(sorted(copies, key=lambda row: (row.category, row.pole, row.source_id)))
    exclusions = []
    raw_exclusions = criteria.get("exclusions") if isinstance(criteria, dict) else None
    if isinstance(raw_exclusions, list):
        for row in raw_exclusions:
            if isinstance(row, dict) and row.get("source_id") and row.get("code"):
                exclusions.append(_omission(str(row["source_id"]), str(row["code"])))
    return PeriodSnapshot(
        capture_at=dossier.capture_started_at,
        period_start=dossier.period_start,
        period_end=dossier.period_end,
        reporting=reporting,
        series=tuple(series),
        objectives=tuple(objectives),
        copies=ordered,
        index=_index_for(ordered),
        omissions=tuple(sorted(exclusions, key=lambda item: item.source_id)),
    )


def _memory_copy(role: str, payload: dict) -> PeriodCopy:
    return PeriodCopy(
        source_id=str(payload.get("source_id") or ""),
        category=CATEGORY_MEMORY,
        pole="",
        role=role,
        title=str(payload.get("title") or ""),
        start=None,
        end=None,
        payload=payload,
    )


def _stored_copy(category: str, role: str, payload: dict, indexed: dict) -> PeriodCopy:
    return PeriodCopy(
        source_id=str(payload.get("source_id") or indexed.get("source_id")),
        category=category,
        pole=str(indexed.get("pole") or ""),
        role=role,
        title=str(indexed.get("title") or payload.get("title") or ""),
        start=_civil(indexed.get("start")),
        end=_civil(indexed.get("end")),
        payload=payload,
    )


def _omission(source_id: str, code: str) -> PeriodOmission:
    return PeriodOmission(source_id, code)


def _period_signals(run, *, establishment_id, period, capture_at, ceiling: int):
    overlap = run(
        lambda: list(
            Signal.objects.filter(establishment_id=establishment_id)
            .filter(
                signal_overlap_q(
                    establishment_id=establishment_id,
                    period_start=period.start,
                    period_end=period.end,
                )
            )
            .filter(created_at__lte=capture_at)
            .select_related(
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
                "operational_unit",
            )
            .order_by("created_at", "id")[: ceiling + 1]
        )
    )
    overlap = _bounded(overlap, ceiling, CATEGORY_SIGNAL)
    late = run(
        lambda: list(
            Signal.objects.filter(
                establishment_id=establishment_id,
                created_at__gt=period.end,
                created_at__lte=capture_at,
            )
            .select_related(
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
                "operational_unit",
            )
            .order_by("created_at", "id")[: ceiling + 1]
        )
    )
    late = _bounded(late, ceiling, CATEGORY_SIGNAL)
    seen = {row.id for row in overlap}
    return [*overlap, *[row for row in late if row.id not in seen]]


def _period_executions(run, *, establishment_id, period, capture_at, ceiling: int):
    rows = run(
        lambda: list(
            ActionPlanExecution.objects.filter(establishment_id=establishment_id)
            .filter(execution_overlap_q(period))
            .filter(created_at__lte=capture_at)
            .defer("description")
            .select_related(
                "pilot_business_unit",
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
            )
            .order_by("created_at", "id")[: ceiling + 1]
        )
    )
    return _bounded(rows, ceiling, CATEGORY_EXECUTION)


def _linked_plans(run, *, establishment_id, signal_ids, ceiling: int) -> list[_PlanView]:
    if not signal_ids:
        return []
    rows = run(
        lambda: list(
            ActionPlanExecution.objects.filter(
                establishment_id=establishment_id,
                source_signal_id__in=signal_ids,
                action_plan_id__isnull=False,
            )
            .order_by("action_plan__created_at", "action_plan_id", "id")
            .values(
                "id",
                "source_signal_id",
                "action_plan_id",
                "action_plan__title",
                "action_plan__catalog_status",
                "action_plan__created_at",
                "action_plan__updated_at",
                "action_plan__pilot_business_unit_id",
                "action_plan__pilot_business_unit__specific_name",
            )[: ceiling + 1]
        )
    )
    rows = _bounded(rows, ceiling, CATEGORY_PLAN)
    grouped: dict = {}
    for row in rows:
        view = grouped.get(row["action_plan_id"])
        if view is None:
            view = _PlanView(
                id=row["action_plan_id"],
                title=row["action_plan__title"],
                catalog_status=row["action_plan__catalog_status"],
                created_at=row["action_plan__created_at"],
                updated_at=row["action_plan__updated_at"],
                pilot_id=row["action_plan__pilot_business_unit_id"],
                pilot_name=row["action_plan__pilot_business_unit__specific_name"],
                signal_ids=[],
                execution_ids=[],
            )
            grouped[row["action_plan_id"]] = view
        view.signal_ids.append(str(row["source_signal_id"]))
        view.execution_ids.append(str(row["id"]))
    return list(grouped.values())


def _objective_rows(run, *, establishment_id, ceiling: int):
    rows = run(
        lambda: list(
            BrainObjective.objects.filter(establishment_id=establishment_id)
            .select_related("current_revision")
            .order_by("created_at", "id")[: ceiling + 1]
        )
    )
    return _bounded(rows, ceiling, CATEGORY_OBJECTIVE)


def _signal_events(run, establishment_id, signal_ids, capture_at):
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
        grouped.setdefault(row.signal_id, []).append(row)
    return grouped


def _execution_events(run, establishment_id, execution_ids, capture_at):
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
        grouped.setdefault(row.action_plan_execution_id, []).append(row)
    return grouped


def _signal_source(
    signal,
    *,
    tz,
    period,
    capture_at,
    events,
    reliable_from,
    span_end: date | None = None,
) -> PeriodSource:
    start, end = _signal_span(signal, tz, span_end or period.end_on, capture_at)
    pole = (
        _specific(signal.affected_business_unit)
        or _specific(signal.responsible_business_unit)
        or ""
    )
    if not _timestamp_allows(signal.created_at, signal.updated_at, capture_at):
        return _bare_source(
            signal,
            category=CATEGORY_SIGNAL,
            pole=pole,
            start=start,
            end=end,
        )
    journal = _journal_events(
        events,
        period=period,
        allowed=SIGNAL_LIFECYCLE_METADATA_SAFE_KEYS,
        keep_suivi=True,
    )
    reconstructed = [
        JournalEvent(
            event_type=event["event_type"],
            occurred_at=event["occurred_at"],
            metadata_safe=event["metadata"],
        )
        for event in journal
    ]
    payload = {
        "source_id": str(signal.id),
        "recorded_at": signal.created_at.isoformat(),
        "title": signal.title,
        "structured_summary": signal.structured_summary,
        "location_text": signal.location_text,
        "business_units": {
            "affected": _named(
                signal.affected_business_unit_id,
                _specific(signal.affected_business_unit),
            ),
            "responsible": _named(
                signal.responsible_business_unit_id,
                _specific(signal.responsible_business_unit),
            ),
        },
        "activity_subject": _named(
            signal.activity_subject_id,
            getattr(signal.activity_subject, "label", None),
        ),
        "operational_unit": _named(
            signal.operational_unit_id,
            getattr(signal.operational_unit, "label", None),
        ),
        "status_at_period_start": _status_at(
            period.start,
            reliable_from,
            reconstructed,
            signal_status_at,
        ),
        "status_at_period_end": _status_at(
            period.end,
            reliable_from,
            reconstructed,
            signal_status_at,
        ),
        "events": [_public_event(event) for event in journal],
    }
    return PeriodSource(
        source_id=str(signal.id),
        category=CATEGORY_SIGNAL,
        pole=pole,
        start=start,
        end=end,
        created_at=signal.created_at,
        updated_at=signal.updated_at,
        payload=payload,
    )


def _execution_source(
    execution,
    *,
    tz: ZoneInfo,
    period,
    capture_at,
    events,
    reliable_from,
    span_end: date | None = None,
) -> PeriodSource:
    start, end = _execution_span(execution, tz, span_end or period.end_on)
    pole = (
        _specific(execution.affected_business_unit)
        or _specific(execution.pilot_business_unit)
        or ""
    )
    if not _timestamp_allows(execution.created_at, execution.updated_at, capture_at):
        return _bare_source(
            execution,
            category=CATEGORY_EXECUTION,
            pole=pole,
            start=start,
            end=end,
        )
    journal = _journal_events(
        events,
        period=period,
        allowed=EXECUTION_LIFECYCLE_METADATA_SAFE_KEYS,
        keep_suivi=True,
    )
    reconstructed = [
        JournalEvent(
            event_type=event["event_type"],
            occurred_at=event["occurred_at"],
            metadata_safe=event["metadata"],
        )
        for event in journal
    ]
    payload = {
        "source_id": str(execution.id),
        "title": execution.title,
        "structured_summary": "",
        "business_units": {
            "pilot": _named(
                execution.pilot_business_unit_id,
                _specific(execution.pilot_business_unit),
            ),
            "affected": _named(
                execution.affected_business_unit_id,
                _specific(execution.affected_business_unit),
            ),
        },
        "activity_subject": _named(
            execution.activity_subject_id,
            getattr(execution.activity_subject, "label", None),
        ),
        "occurrence_date": _iso_date(execution.occurrence_date),
        "start_at": _iso_datetime(execution.start_at),
        "end_at": _iso_datetime(execution.end_at),
        "status_at_period_start": _status_at(
            period.start,
            reliable_from,
            reconstructed,
            execution_status_at,
        ),
        "status_at_period_end": _status_at(
            period.end,
            reliable_from,
            reconstructed,
            execution_status_at,
        ),
        "events": [_public_event(event) for event in journal],
        "action_plan_id": _text_or_none(execution.action_plan_id),
        "source_signal_id": _text_or_none(execution.source_signal_id),
    }
    return PeriodSource(
        source_id=str(execution.id),
        category=CATEGORY_EXECUTION,
        pole=pole,
        start=start,
        end=end,
        created_at=execution.created_at,
        updated_at=execution.updated_at,
        payload={key: value for key, value in payload.items() if value is not None},
    )


def _plan_source(plan: _PlanView, *, tz: ZoneInfo, capture_at) -> PeriodSource:
    signal_ids = tuple(dict.fromkeys(plan.signal_ids))
    start = plan.created_at.astimezone(tz).date()
    payload = {
        "source_id": str(plan.id),
        "title": plan.title,
        "pilot_business_unit": _named(plan.pilot_id, plan.pilot_name),
        "source_signal_ids": list(signal_ids),
        "execution_ids": list(dict.fromkeys(plan.execution_ids)),
        "catalog_status": plan.catalog_status,
    }
    if not _timestamp_allows(plan.created_at, plan.updated_at, capture_at):
        payload = {"source_id": str(plan.id)}
    return PeriodSource(
        source_id=str(plan.id),
        category=CATEGORY_PLAN,
        pole=plan.pilot_name or "",
        start=start,
        end=start + timedelta(days=1),
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        payload=payload,
        linked_source_ids=signal_ids,
    )


def _objective_source(objective, *, capture_at) -> PeriodSource:
    revision = objective.current_revision
    updated_at = objective.updated_at
    created_at = objective.created_at
    if revision is not None and revision.created_at > updated_at:
        updated_at = revision.created_at
    payload: dict = {"source_id": str(objective.id)}
    series_key = ""
    start = None
    end = None
    if revision is not None and _timestamp_allows(created_at, updated_at, capture_at):
        series_key = fold(revision.indicator)
        start = revision.measurement_period_start
        end = revision.measurement_period_end
        payload = {
            "source_id": str(objective.id),
            "series_key": series_key,
            "indicator": revision.indicator,
            "unit": revision.unit,
            "scope": revision.scope,
            "target": revision.target,
            "period_start": _iso_date(revision.measurement_period_start),
            "period_end": _iso_date(revision.measurement_period_end),
        }
        payload = {key: value for key, value in payload.items() if value is not None}
    return PeriodSource(
        source_id=str(objective.id),
        category=CATEGORY_OBJECTIVE,
        pole=str(revision.scope or "") if revision is not None else "",
        start=start,
        end=end,
        created_at=created_at,
        updated_at=updated_at,
        payload=payload,
        series_key=series_key,
    )


def _bare_source(row, *, category: str, pole: str, start, end) -> PeriodSource:
    return PeriodSource(
        source_id=str(row.id),
        category=category,
        pole=pole,
        start=start,
        end=end,
        created_at=row.created_at,
        updated_at=row.updated_at,
        payload={"source_id": str(row.id)},
    )


def _signal_span(signal, tz: ZoneInfo, period_end: date, capture_at: datetime):
    start = signal.created_at.astimezone(tz).date()
    terminal = None
    for candidate in (signal.resolved_at, signal.canceled_at):
        if candidate is not None and candidate <= capture_at:
            terminal = candidate if terminal is None else min(terminal, candidate)
    if terminal is None:
        return start, period_end
    return start, terminal.astimezone(tz).date() + timedelta(days=1)


def _execution_span(execution, tz: ZoneInfo, period_end: date):
    if execution.occurrence_date is not None:
        return execution.occurrence_date, execution.occurrence_date + timedelta(days=1)
    if execution.start_at is not None:
        start = execution.start_at.astimezone(tz).date()
        if execution.end_at is not None:
            return start, execution.end_at.astimezone(tz).date() + timedelta(days=1)
        return start, period_end
    return None, None


def _reporting_payload(reporting, extraction_payload: dict) -> dict:
    payload = extraction_payload if isinstance(extraction_payload, dict) else {}
    qualitative = []
    for block in payload.get("qualitative") or []:
        if not isinstance(block, dict):
            continue
        text = str(block.get("text") or "").strip()
        if not text:
            continue
        qualitative.append({"kind": str(block.get("kind") or "paragraph"), "text": text})
    measures = [
        freeze_measure(
            raw,
            measure_id=f"measure:{index}",
            period_start=reporting.period_start,
            period_end=reporting.period_end,
        )
        for index, raw in enumerate(_measures(payload))
    ]
    return {
        "source_id": str(reporting.id),
        "period_start": reporting.period_start.isoformat(),
        "period_end": reporting.period_end.isoformat(),
        "measures": measures,
        "qualitative": qualitative,
    }


def _series_payloads(measures: list[dict]) -> tuple[dict, ...]:
    seen: set[str] = set()
    rows = []
    for measure in measures:
        label = str(measure.get("label") or "").strip()
        if not label:
            continue
        key = fold(label)
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "series_key": key,
                "label": label,
                "unit": str(measure.get("unit") or ""),
                "scope": str(measure.get("scope") or ""),
            }
        )
    return tuple(rows)


def _timestamp_allows(created_at, updated_at, capture_at) -> bool:
    return historical_copy_decision(
        created_at=created_at,
        updated_at=updated_at,
        capture_at=capture_at,
    ).copied


def _civil(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _iso_date(value):
    if value is None:
        return None
    return value.isoformat()


def _iso_datetime(value):
    if value is None:
        return None
    return value.isoformat()


def _text_or_none(value):
    if value is None:
        return None
    return str(value)


@dataclass
class _PlanView:
    id: object
    title: str
    catalog_status: str | None
    created_at: datetime
    updated_at: datetime
    pilot_id: object
    pilot_name: str | None
    signal_ids: list[str]
    execution_ids: list[str]
