"""Bounded terrain collection for one capture.

Independent of feed retention, pins, and pagination.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from django.db.models import Count, Exists, OuterRef, Q

from houston.action_plans.constants import EXECUTION_LIFECYCLE_METADATA_SAFE_KEYS
from houston.action_plans.models import (
    ActionPlanExecution,
    ActionPlanExecutionLifecycleEvent,
    ActionPlanExecutionTask,
)
from houston.analytics.journal import JournalEvent, execution_status_at, signal_status_at
from houston.analytics.models import SignalPatternAssignment
from houston.brain.errors import BrainWorkError, CaptureVolumeExceeded
from houston.brain.mentions import first_period_mention
from houston.brain.models import BrainExtraction, BrainObjective, BrainReporting
from houston.brain.objectives import revision_overlaps_period
from houston.establishments.models import EstablishmentActivityDescription
from houston.signals.constants import (
    ACTIVE_SIGNAL_STATUSES,
    SIGNAL_LIFECYCLE_METADATA_SAFE_KEYS,
)
from houston.signals.models import Signal, SignalLifecycleEvent, SignalSourceObservation

SEARCH_SIGNAL_OVERLAP = "chevauchement_signals"
SEARCH_LATE_DECLARATIONS = "declarations_tardives"
SEARCH_EXECUTION_OVERLAP = "chevauchement_executions"
SEARCH_PLAN_LINKS = "liens_plans"
SEARCH_PRIOR_REPORTING = "reporting_anterieur"
SEARCH_N1 = "fenetre_n_1"
SEARCH_OBJECTIVES = "objectifs_pertinents"

REQUIRED_SEARCHES = (
    SEARCH_SIGNAL_OVERLAP,
    SEARCH_LATE_DECLARATIONS,
    SEARCH_EXECUTION_OVERLAP,
    SEARCH_PLAN_LINKS,
    SEARCH_PRIOR_REPORTING,
    SEARCH_N1,
    SEARCH_OBJECTIVES,
)

CATEGORY_SIGNAL = "signal"
CATEGORY_EXECUTION = "execution"
CATEGORY_TASK = "execution_task"
CATEGORY_PLAN = "plan"
CATEGORY_REPORTING = "reporting"
CATEGORY_DOCUMENT = "document"
CATEGORY_OBJECTIVE = "objective"
CATEGORY_CONTEXT = "establishment_context"

ROLE_OVERLAP = "chevauchement"
ROLE_LATE = "declaration_tardive"
ROLE_INTENTION = "intention"
ROLE_N1 = "n_1"
ROLE_LINK = "lien_direct"
ROLE_PRIOR = "reporting_anterieur"
ROLE_PERIOD = "periode"
ROLE_SUIVI = "suivi"
ROLE_BEFORE = "anterieur"
ROLE_CURRENT_MEASURE = "mesure"
ROLE_CURRENT_QUALITATIVE = "qualitatif"

NOT_RECONSTRUCTABLE = "not_reconstructable"
REASON_NOT_COMPARABLE = "periode_non_comparable"
REASON_NO_PERIOD_DATE = "date_periode_absente"
REASON_ALREADY_OVERLAP = "deja_chevauchement"
REASON_NO_MEASURE = "sans_mesure"

_MEASURE_KEYS = (
    "label",
    "value",
    "value_kind",
    "unit",
    "period",
    "scope",
    "definition",
    "locator",
    "ambiguities",
)
_FORBIDDEN_KEYS = frozenset(
    {
        "raw_text",
        "body",
        "comment",
        "request_comment",
        "review_comment",
        "cancel_comment",
        "description",
        "skipped_reason",
        "instance_description",
        "transcription",
    }
)
_LINK_TYPES = ("created_from", "aggregated_from", "merged_from")


@dataclass(frozen=True)
class DossierRow:
    category: str
    stable_key: str
    role: str
    payload: dict
    reason: str


@dataclass
class SearchRecord:
    code: str
    criteria: dict
    examined_count: int = 0
    retained_count: int = 0
    exclusions: list[dict] = field(default_factory=list)

    def as_criteria(self) -> dict:
        criteria = dict(self.criteria)
        if self.exclusions:
            criteria["exclusions"] = self.exclusions
        return criteria


@dataclass(frozen=True)
class _Window:
    start_on: date
    end_on: date
    start: datetime
    end: datetime


def collect_capture(
    *,
    establishment,
    reporting: BrainReporting,
    extraction_payload: dict,
    capture_at: datetime,
    reliable_from: datetime | None,
    ceiling: int,
    run,
) -> tuple[list[DossierRow], list[SearchRecord]]:
    """Read one establishment and return dossier rows plus every minimal search."""
    tz = _zone(establishment.timezone)
    period = _window(reporting.period_start, reporting.period_end, tz)
    previous = _window(
        reporting.period_start - (reporting.period_end - reporting.period_start),
        reporting.period_start,
        tz,
    )
    year_ago = _window(
        reporting.period_start - relativedelta(years=1),
        reporting.period_end - relativedelta(years=1),
        tz,
    )
    capture_on = capture_at.astimezone(tz).date()
    base = _base_criteria(establishment, tz.key, period, capture_at)
    labels = _measure_labels(extraction_payload)

    overlap = _load_signals(
        run,
        establishment.id,
        signal_overlap_q(
            establishment_id=establishment.id,
            period_start=period.start,
            period_end=period.end,
        ),
        ceiling,
        SEARCH_SIGNAL_OVERLAP,
    )
    late = _load_signals(
        run,
        establishment.id,
        Q(created_at__gt=period.end, created_at__lte=capture_at),
        ceiling,
        SEARCH_LATE_DECLARATIONS,
    )
    n1_signals = _load_signals(
        run,
        establishment.id,
        signal_overlap_q(
            establishment_id=establishment.id,
            period_start=year_ago.start,
            period_end=year_ago.end,
        ),
        ceiling,
        SEARCH_N1,
    )
    signal_ids = [row.id for row in (*overlap, *late, *n1_signals)]
    events = _signal_events(run, establishment.id, signal_ids, capture_at)
    links = _link_counts(run, establishment.id, signal_ids)
    patterns = _patterns(run, establishment.id, establishment.organization_id, signal_ids)

    overlap_ids = {row.id for row in overlap}
    late_kept, late_excluded, late_ids = _late_items(
        late,
        overlap_ids=overlap_ids,
        period=period,
        events=events,
        links=links,
        patterns=patterns,
        reliable_from=reliable_from,
    )
    overlap_items = [
        _signal_item(
            row,
            stable_key=f"signal:{row.id}",
            role=ROLE_OVERLAP,
            reason="chevauchement_periode",
            period=period,
            events=events,
            links=links,
            patterns=patterns,
            reliable_from=reliable_from,
            mention=None,
            keep_suivi=True,
        )
        for row in overlap
    ]
    n1_signal_items = [
        _signal_item(
            row,
            stable_key=f"signal:{row.id}:n_1",
            role=ROLE_N1,
            reason="fenetre_n_1",
            period=year_ago,
            events=events,
            links=links,
            patterns=patterns,
            reliable_from=reliable_from,
            mention=None,
            keep_suivi=False,
        )
        for row in n1_signals
    ]

    executions = _load_executions(
        run,
        establishment.id,
        execution_overlap_q(period),
        ceiling,
        SEARCH_EXECUTION_OVERLAP,
    )
    n1_executions = _load_executions(
        run,
        establishment.id,
        execution_overlap_q(year_ago),
        ceiling,
        SEARCH_N1,
    )
    if len(n1_signals) + len(n1_executions) > ceiling:
        raise CaptureVolumeExceeded(SEARCH_N1)
    execution_ids = [row.id for row in (*executions, *n1_executions)]
    tasks = _tasks(run, execution_ids, ceiling)
    execution_events = _execution_events(run, establishment.id, execution_ids, capture_at)

    execution_items, task_items = _execution_items(
        executions,
        tasks=tasks,
        events=execution_events,
        period=period,
        capture_at=capture_at,
        capture_on=capture_on,
        reliable_from=reliable_from,
        role_for_period=True,
    )
    n1_execution_items, n1_task_items = _execution_items(
        n1_executions,
        tasks=tasks,
        events=execution_events,
        period=year_ago,
        capture_at=capture_at,
        capture_on=capture_on,
        reliable_from=reliable_from,
        role_for_period=False,
    )

    retained_signal_ids = [row.id for row in overlap] + late_ids
    plan_items, plan_examined = _plan_items(
        run,
        establishment.id,
        retained_signal_ids,
        ceiling,
    )
    reporting_items, reporting_examined, reporting_excluded = _prior_reportings(
        run,
        establishment.id,
        reporting.id,
        (previous, year_ago),
        ceiling,
    )
    objective_items, objective_examined, objective_excluded = _objectives(
        run,
        establishment.id,
        period,
        labels,
        capture_at,
        ceiling,
    )

    signal_search = SearchRecord(
        code=SEARCH_SIGNAL_OVERLAP,
        criteria=base,
        examined_count=len(overlap),
        retained_count=len(overlap_items),
    )
    late_search = SearchRecord(
        code=SEARCH_LATE_DECLARATIONS,
        criteria={
            **base,
            "recorded_after": period.end.isoformat(),
            "recorded_until": capture_at.isoformat(),
        },
        examined_count=len(late),
        retained_count=len(late_kept),
        exclusions=late_excluded,
    )
    execution_search = SearchRecord(
        code=SEARCH_EXECUTION_OVERLAP,
        criteria=base,
        examined_count=len(executions),
        retained_count=len(execution_items),
    )
    plan_search = SearchRecord(
        code=SEARCH_PLAN_LINKS,
        criteria={**base, "source": "source_signal"},
        examined_count=plan_examined,
        retained_count=len(plan_items),
    )
    reporting_search = SearchRecord(
        code=SEARCH_PRIOR_REPORTING,
        criteria={
            **base,
            "previous_period_start": previous.start_on.isoformat(),
            "previous_period_end": previous.end_on.isoformat(),
            "n1_period_start": year_ago.start_on.isoformat(),
            "n1_period_end": year_ago.end_on.isoformat(),
        },
        examined_count=reporting_examined,
        retained_count=len(reporting_items),
        exclusions=reporting_excluded,
    )
    n1_search = SearchRecord(
        code=SEARCH_N1,
        criteria={
            **base,
            "n1_period_start": year_ago.start_on.isoformat(),
            "n1_period_end": year_ago.end_on.isoformat(),
        },
        examined_count=len(n1_signals) + len(n1_executions),
        retained_count=len(n1_signal_items) + len(n1_execution_items),
    )
    objective_search = SearchRecord(
        code=SEARCH_OBJECTIVES,
        criteria=base,
        examined_count=objective_examined,
        retained_count=len(objective_items),
        exclusions=objective_excluded,
    )
    rows = [
        *_document_rows(extraction_payload),
        *overlap_items,
        *late_kept,
        *execution_items,
        *task_items,
        *plan_items,
        *reporting_items,
        *n1_signal_items,
        *n1_execution_items,
        *n1_task_items,
        *objective_items,
        _establishment_context(run, establishment),
    ]
    for row in rows:
        _reject_forbidden(row.payload)
    searches = [
        signal_search,
        late_search,
        execution_search,
        plan_search,
        reporting_search,
        n1_search,
        objective_search,
    ]
    return rows, searches


def signal_overlap_q(*, establishment_id, period_start: datetime, period_end: datetime) -> Q:
    non_terminal = Q(status__in=ACTIVE_SIGNAL_STATUSES)
    terminal_from_start = Q(status=Signal.Status.RESOLVED, resolved_at__gte=period_start) | Q(
        status=Signal.Status.CANCELED,
        canceled_at__gte=period_start,
    )
    created = Q(created_at__lt=period_end) & (non_terminal | terminal_from_start)
    event = SignalLifecycleEvent.objects.filter(
        signal_id=OuterRef("pk"),
        establishment_id=establishment_id,
        occurred_at__gte=period_start,
        occurred_at__lt=period_end,
    )
    return created | Exists(event)


def execution_overlap_q(window: _Window) -> Q:
    return (
        Q(occurrence_date__gte=window.start_on, occurrence_date__lt=window.end_on)
        | Q(start_at__gte=window.start, start_at__lt=window.end)
        | Q(end_at__gt=window.start, end_at__lt=window.end)
        | Q(start_at__lt=window.end, end_at__gt=window.start)
        | Q(started_at__gte=window.start, started_at__lt=window.end)
        | Q(marked_done_at__gte=window.start, marked_done_at__lt=window.end)
        | Q(validated_at__gte=window.start, validated_at__lt=window.end)
    )


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception as exc:
        raise BrainWorkError(
            code="establishment_timezone_invalid",
            message="Le fuseau de l'établissement est inutilisable.",
        ) from exc


def _window(start_on: date, end_on: date, tz: ZoneInfo) -> _Window:
    return _Window(
        start_on=start_on,
        end_on=end_on,
        start=datetime.combine(start_on, time.min, tzinfo=tz),
        end=datetime.combine(end_on, time.min, tzinfo=tz),
    )


def _base_criteria(
    establishment, timezone_name: str, period: _Window, capture_at: datetime
) -> dict:
    return {
        "establishment_id": str(establishment.id),
        "timezone": timezone_name,
        "period_start": period.start_on.isoformat(),
        "period_end": period.end_on.isoformat(),
        "capture_at": capture_at.isoformat(),
    }


def _load_signals(run, establishment_id, predicate: Q, ceiling: int, category: str) -> list[Signal]:
    def query():
        return list(
            Signal.objects.filter(establishment_id=establishment_id)
            .filter(predicate)
            .select_related(
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
                "operational_unit",
            )
            .order_by("created_at", "id")[: ceiling + 1]
        )

    return _bounded(run(query), ceiling, category)


def _load_executions(run, establishment_id, predicate: Q, ceiling: int, category: str):
    def query():
        return list(
            ActionPlanExecution.objects.filter(establishment_id=establishment_id)
            .filter(predicate)
            .select_related(
                "pilot_business_unit",
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
            )
            .order_by("created_at", "id")[: ceiling + 1]
        )

    return _bounded(run(query), ceiling, category)


def _bounded(rows, ceiling: int, category: str):
    if len(rows) > ceiling:
        raise CaptureVolumeExceeded(category)
    return rows


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
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.signal_id].append(row)
    return grouped


def _link_counts(run, establishment_id, signal_ids) -> dict:
    counts = {}
    if not signal_ids:
        return counts
    rows = run(
        lambda: list(
            SignalSourceObservation.objects.filter(
                signal_id__in=signal_ids,
                signal__establishment_id=establishment_id,
            )
            .values("signal_id", "link_type")
            .annotate(total=Count("id"))
        )
    )
    for row in rows:
        bucket = counts.setdefault(row["signal_id"], {name: 0 for name in _LINK_TYPES})
        if row["link_type"] in bucket:
            bucket[row["link_type"]] = row["total"]
    return counts


def _patterns(run, establishment_id, organization_id, signal_ids) -> dict:
    if not signal_ids:
        return {}
    rows = run(
        lambda: list(
            SignalPatternAssignment.objects.filter(
                signal_id__in=signal_ids,
                signal__establishment_id=establishment_id,
                pattern__organization_id=organization_id,
                pattern_id__isnull=False,
            ).values("id", "signal_id", "pattern_id", "pattern__label", "pattern__status")
        )
    )
    return {
        row["signal_id"]: {
            "assignment_id": str(row["id"]),
            "pattern_id": str(row["pattern_id"]),
            "label": row["pattern__label"],
            "status": row["pattern__status"],
        }
        for row in rows
    }


def _tasks(run, execution_ids, ceiling: int) -> dict:
    if not execution_ids:
        return {}
    rows = run(
        lambda: list(
            ActionPlanExecutionTask.objects.filter(action_plan_execution_id__in=execution_ids)
            .order_by("position", "id")
            .values(
                "id",
                "action_plan_execution_id",
                "task",
                "position",
                "status",
                "deadline_at",
                "completed_at",
                "execution_team__business_unit_id",
                "execution_team__business_unit__specific_name",
            )[: ceiling + 1]
        )
    )
    if len(rows) > ceiling:
        raise CaptureVolumeExceeded(CATEGORY_TASK)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["action_plan_execution_id"]].append(row)
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
    grouped = defaultdict(list)
    for row in rows:
        grouped[row.action_plan_execution_id].append(row)
    return grouped


def _late_items(late, *, overlap_ids, period, events, links, patterns, reliable_from):
    kept = []
    kept_ids = []
    excluded = []
    for row in late:
        if row.id in overlap_ids:
            excluded.append({"source_id": str(row.id), "reason": REASON_ALREADY_OVERLAP})
            continue
        mention = first_period_mention(
            title=row.title,
            structured_summary=row.structured_summary,
            period_start=period.start_on,
            period_end=period.end_on,
        )
        if mention is None:
            excluded.append({"source_id": str(row.id), "reason": REASON_NO_PERIOD_DATE})
            continue
        kept_ids.append(row.id)
        kept.append(
            _signal_item(
                row,
                stable_key=f"signal:{row.id}",
                role=ROLE_LATE,
                reason="date_mentionnee_dans_la_periode",
                period=period,
                events=events,
                links=links,
                patterns=patterns,
                reliable_from=reliable_from,
                mention=mention,
                keep_suivi=True,
            )
        )
    return kept, excluded, kept_ids


def _signal_item(
    signal: Signal,
    *,
    stable_key: str,
    role: str,
    reason: str,
    period: _Window,
    events,
    links,
    patterns,
    reliable_from,
    mention,
    keep_suivi: bool,
) -> DossierRow:
    journal = _journal_events(
        events.get(signal.id, []),
        period=period,
        allowed=SIGNAL_LIFECYCLE_METADATA_SAFE_KEYS,
        keep_suivi=keep_suivi,
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
        "recorded_at": _iso(signal.created_at),
        "title": signal.title,
        "structured_summary": signal.structured_summary,
        "issue_focus": signal.issue_focus,
        "location_text": signal.location_text,
        "expected_action": signal.expected_action,
        "business_units": {
            "affected": _named(
                signal.affected_business_unit_id, _specific(signal.affected_business_unit)
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
        "status_at_capture": {"value": signal.status, "as_of": "capture"},
        "routing_status_at_capture": {"value": signal.routing_status, "as_of": "capture"},
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
        "resolved_at": _iso(signal.resolved_at),
        "canceled_at": _iso(signal.canceled_at),
        "source_observation_link_counts": links.get(signal.id, {name: 0 for name in _LINK_TYPES}),
        "pattern_assignment": patterns.get(signal.id),
        "events": [_public_event(event) for event in journal],
    }
    if mention is not None:
        payload["phenomenon_mentioned_at"] = mention.civil_date.isoformat()
        payload["mention"] = mention.provenance()
    return DossierRow(CATEGORY_SIGNAL, stable_key, role, payload, reason)


def _execution_items(
    executions,
    *,
    tasks,
    events,
    period,
    capture_at,
    capture_on,
    reliable_from,
    role_for_period: bool,
):
    items = []
    task_items = []
    for execution in executions:
        if role_for_period:
            role = _execution_role(execution, period, capture_at, capture_on)
            suffix = ""
        else:
            role = ROLE_N1
            suffix = ":n_1"
        journal = _journal_events(
            events.get(execution.id, []),
            period=period,
            allowed=EXECUTION_LIFECYCLE_METADATA_SAFE_KEYS,
            keep_suivi=role_for_period,
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
            "action_plan_id": _str_or_none(execution.action_plan_id),
            "source_signal_id": _str_or_none(execution.source_signal_id),
            "title": execution.title,
            "status_at_capture": {"value": execution.status, "as_of": "capture"},
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
            "occurrence_date": _iso(execution.occurrence_date),
            "start_at": _iso(execution.start_at),
            "end_at": _iso(execution.end_at),
            "started_at": _iso(execution.started_at),
            "marked_done_at": _iso(execution.marked_done_at),
            "validated_at": _iso(execution.validated_at),
            "canceled_at": _iso(execution.canceled_at),
            "planned_after_capture": role == ROLE_INTENTION,
            "business_units": {
                "pilot": _named(
                    execution.pilot_business_unit_id, _specific(execution.pilot_business_unit)
                ),
                "affected": _named(
                    execution.affected_business_unit_id,
                    _specific(execution.affected_business_unit),
                ),
                "responsible": _named(
                    execution.responsible_business_unit_id,
                    _specific(execution.responsible_business_unit),
                ),
            },
            "activity_subject": _named(
                execution.activity_subject_id,
                getattr(execution.activity_subject, "label", None),
            ),
            "events": [_public_event(event) for event in journal],
        }
        items.append(
            DossierRow(
                CATEGORY_EXECUTION,
                f"execution:{execution.id}{suffix}",
                role,
                payload,
                "intention_planifiee" if role == ROLE_INTENTION else role,
            )
        )
        for task in tasks.get(execution.id, []):
            task_items.append(
                DossierRow(
                    CATEGORY_TASK,
                    f"execution-task:{task['id']}{suffix}",
                    role,
                    {
                        "source_id": str(task["id"]),
                        "execution_id": str(execution.id),
                        "task": task["task"],
                        "position": task["position"],
                        "status_at_capture": {"value": task["status"], "as_of": "capture"},
                        "deadline_at": _iso(task["deadline_at"]),
                        "completed_at": _iso(task["completed_at"]),
                        "business_unit": _named(
                            task["execution_team__business_unit_id"],
                            task["execution_team__business_unit__specific_name"],
                        ),
                    },
                    role,
                )
            )
    return items, task_items


def _execution_role(execution, period: _Window, capture_at: datetime, capture_on: date) -> str:
    actual = (
        _in_window(execution.started_at, period.start, period.end)
        or _in_window(execution.marked_done_at, period.start, period.end)
        or _in_window(execution.validated_at, period.start, period.end)
    )
    if actual:
        return ROLE_OVERLAP
    planned = []
    if execution.start_at is not None:
        planned.append(execution.start_at >= capture_at)
    if execution.end_at is not None:
        planned.append(execution.end_at >= capture_at)
    if execution.occurrence_date is not None:
        planned.append(execution.occurrence_date >= capture_on)
    if planned and all(planned):
        return ROLE_INTENTION
    return ROLE_OVERLAP


def _plan_items(run, establishment_id, signal_ids, ceiling: int):
    if not signal_ids:
        return [], 0
    rows = run(
        lambda: list(
            ActionPlanExecution.objects.filter(
                establishment_id=establishment_id,
                source_signal_id__in=signal_ids,
            )
            .order_by("created_at", "id")
            .values(
                "id",
                "source_signal_id",
                "action_plan_id",
                "title",
                "action_plan__title",
                "action_plan__catalog_status",
                "action_plan__pilot_business_unit_id",
                "action_plan__pilot_business_unit__specific_name",
            )[: ceiling + 1]
        )
    )
    if len(rows) > ceiling:
        raise CaptureVolumeExceeded(SEARCH_PLAN_LINKS)
    grouped: dict = {}
    for row in rows:
        key = ("plan", row["action_plan_id"]) if row["action_plan_id"] else ("execution", row["id"])
        bucket = grouped.setdefault(
            key,
            {
                "execution_ids": [],
                "source_signal_ids": [],
                "title": row["action_plan__title"] or row["title"],
                "catalog_status": row["action_plan__catalog_status"],
                "pilot": _named(
                    row["action_plan__pilot_business_unit_id"],
                    row["action_plan__pilot_business_unit__specific_name"],
                ),
            },
        )
        bucket["execution_ids"].append(str(row["id"]))
        bucket["source_signal_ids"].append(str(row["source_signal_id"]))
    items = []
    for key, bucket in grouped.items():
        kind, source = key
        stable = f"plan:{source}" if kind == "plan" else f"plan-link:{source}"
        source_id = str(source) if kind == "plan" else None
        items.append(
            DossierRow(
                CATEGORY_PLAN,
                stable,
                ROLE_LINK,
                {
                    "source_id": source_id,
                    "execution_ids": bucket["execution_ids"],
                    "source_signal_ids": bucket["source_signal_ids"],
                    "title": bucket["title"],
                    "catalog_status": bucket["catalog_status"],
                    "pilot_business_unit": bucket["pilot"],
                },
                "lien_direct_signal",
            )
        )
    return items, len(rows)


def _prior_reportings(
    run, establishment_id, current_id, windows: tuple[_Window, _Window], ceiling: int
):
    previous, year_ago = windows
    predicate = Q(period_start__lt=previous.end_on, period_end__gt=previous.start_on) | Q(
        period_start__lt=year_ago.end_on,
        period_end__gt=year_ago.start_on,
    )

    def query():
        return list(
            BrainReporting.objects.filter(
                establishment_id=establishment_id,
                status=BrainReporting.Status.READY,
                period_start__isnull=False,
                period_end__isnull=False,
            )
            .exclude(pk=current_id)
            .filter(predicate)
            .order_by("period_start", "id")[: ceiling + 1]
        )

    reportings = _bounded(run(query), ceiling, SEARCH_PRIOR_REPORTING)
    if not reportings:
        return [], 0, []
    ids = [row.id for row in reportings]
    extractions = run(
        lambda: list(
            BrainExtraction.objects.filter(reporting_id__in=ids).order_by(
                "reporting_id", "-created_at"
            )
        )
    )
    by_reporting = {}
    for extraction in extractions:
        by_reporting.setdefault(extraction.reporting_id, extraction)
    items = []
    excluded = []
    for reporting in reportings:
        extraction = by_reporting.get(reporting.id)
        measures = _measures(extraction.payload if extraction is not None else None)
        if not measures:
            excluded.append({"source_id": str(reporting.id), "reason": REASON_NO_MEASURE})
            continue
        items.append(
            DossierRow(
                CATEGORY_REPORTING,
                f"reporting:{reporting.id}",
                ROLE_PRIOR,
                {
                    "source_id": str(reporting.id),
                    "period_start": reporting.period_start.isoformat(),
                    "period_end": reporting.period_end.isoformat(),
                    "measures": measures,
                },
                "reporting_anterieur_comparable",
            )
        )
    return items, len(reportings), excluded


def _objectives(run, establishment_id, period: _Window, labels: set[str], capture_at, ceiling: int):
    def query():
        return list(
            BrainObjective.objects.filter(establishment_id=establishment_id)
            .select_related("current_revision")
            .order_by("created_at", "id")[: ceiling + 1]
        )

    objectives = _bounded(run(query), ceiling, SEARCH_OBJECTIVES)
    items = []
    excluded = []
    for objective in objectives:
        revision = objective.current_revision
        if revision is None or revision.created_at > capture_at:
            excluded.append({"source_id": str(objective.id), "reason": REASON_NOT_COMPARABLE})
            continue
        indicator = revision.indicator.strip().casefold()
        comparable = revision_overlaps_period(
            revision,
            period_start=period.start_on,
            period_end=period.end_on,
        ) or (bool(indicator) and indicator in labels)
        if not comparable:
            excluded.append(
                {
                    "source_id": str(objective.id),
                    "revision_id": str(revision.id),
                    "reason": REASON_NOT_COMPARABLE,
                }
            )
            continue
        items.append(
            DossierRow(
                CATEGORY_OBJECTIVE,
                f"objective-revision:{revision.id}",
                ROLE_OVERLAP
                if revision_overlaps_period(
                    revision,
                    period_start=period.start_on,
                    period_end=period.end_on,
                )
                else "mesure_extraite",
                {
                    "source_id": str(objective.id),
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
                },
                "objectif_pertinent",
            )
        )
    return items, len(objectives), excluded


def _journal_events(rows, *, period: _Window, allowed: frozenset, keep_suivi: bool) -> list[dict]:
    journal = []
    for row in rows:
        occurred_at = row.occurred_at
        if occurred_at >= period.end and not keep_suivi:
            continue
        if occurred_at >= period.end:
            role = ROLE_SUIVI
        elif occurred_at >= period.start:
            role = ROLE_PERIOD
        else:
            role = ROLE_BEFORE
        metadata = row.metadata_safe if isinstance(row.metadata_safe, dict) else {}
        journal.append(
            {
                "id": str(row.id),
                "event_type": row.event_type,
                "occurred_at": occurred_at,
                "role": role,
                "actor_membership_id": _str_or_none(row.actor_membership_id),
                "metadata": {
                    key: metadata[key]
                    for key in allowed
                    if key in metadata and metadata[key] is not None
                },
            }
        )
    return journal


def _public_event(event: dict) -> dict:
    return {
        "id": event["id"],
        "event_type": event["event_type"],
        "occurred_at": _iso(event["occurred_at"]),
        "role": event["role"],
        "actor_membership_id": event["actor_membership_id"],
        "metadata": event["metadata"],
    }


def _status_at(at, reliable_from, events, reconstruct) -> dict:
    if reliable_from is None:
        return {"value": NOT_RECONSTRUCTABLE}
    status = reconstruct(at=at, reliable_from=reliable_from, events=events)
    if status is None:
        return {"value": NOT_RECONSTRUCTABLE}
    return {"value": status}


def _establishment_context(run, establishment) -> DossierRow:
    """Copy the living activity description. A later edit does not rewrite this row."""

    def query():
        return EstablishmentActivityDescription.objects.filter(
            establishment_id=establishment.id
        ).first()

    description = run(query)
    text = (description.description if description is not None else "").strip()
    if description is None or not text:
        return DossierRow(
            CATEGORY_CONTEXT,
            "establishment-context",
            "absent",
            {"present": False},
            "contexte_etablissement",
        )
    return DossierRow(
        CATEGORY_CONTEXT,
        "establishment-context",
        "copie",
        {
            "source_id": str(description.id),
            "text": text,
            "content_hash": hashlib.sha256(text.encode()).hexdigest(),
            "source_updated_at": description.updated_at.isoformat(),
        },
        "contexte_etablissement",
    )


def document_stable_key(kind: str, index: int) -> str:
    """Source-list index shared by capture and lot binding. Skipped rows keep their index."""
    return f"document:{kind}:{index:04d}"


def _document_rows(payload: dict) -> list[DossierRow]:
    """Current reporting, copied from the extraction already loaded for this capture."""
    if not isinstance(payload, dict):
        return []
    rows = []
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
                    "kind": str(block.get("kind") or "paragraph"),
                    "text": text,
                    "locator": locator,
                },
                "reporting_courant",
            )
        )
    for index, measure in enumerate(_measures(payload)):
        rows.append(
            DossierRow(
                CATEGORY_DOCUMENT,
                document_stable_key("measure", index),
                ROLE_CURRENT_MEASURE,
                measure,
                "reporting_courant",
            )
        )
    return rows


def _measures(payload) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    measures = []
    for measure in payload.get("measures") or []:
        if not isinstance(measure, dict):
            continue
        measures.append({key: measure.get(key) for key in _MEASURE_KEYS if key in measure})
    return measures


def _measure_labels(payload: dict) -> set[str]:
    labels = set()
    for measure in _measures(payload):
        label = (measure.get("label") or "").strip().casefold()
        if label:
            labels.add(label)
    return labels


def _named(identifier, name):
    if identifier is None:
        return None
    return {"id": str(identifier), "name": name}


def _specific(unit):
    if unit is None:
        return None
    return unit.specific_name


def _str_or_none(value):
    if value is None:
        return None
    return str(value)


def _iso(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _in_window(value, start: datetime, end: datetime) -> bool:
    return value is not None and start <= value < end


def _reject_forbidden(payload) -> None:
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in _FORBIDDEN_KEYS:
                    raise BrainWorkError(
                        code="capture_forbidden_field",
                        message="Un champ interdit a été sélectionné.",
                    )
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
