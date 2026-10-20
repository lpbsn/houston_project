"""Closed-menu deepenings. Each one is a short transaction that appends copies.

The model names a menu entry. It does not name a query. A row already in the
dossier is left untouched. A row changed after ``capture_at`` is noted by
identifier and is not copied. A completed analysis is decision memory: the
copy says so, and it is not field evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from dateutil.relativedelta import relativedelta
from django.db import connection, transaction
from django.db.models import Exists, OuterRef, Q
from django.db.utils import OperationalError

from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionLifecycleEvent
from houston.analytics.journal import get_history_reliable_from
from houston.brain.capture import CaptureTimeout
from houston.brain.collection import _window, _zone
from houston.brain.configuration import json_token_count
from houston.brain.dossier import (
    CATEGORY_INDEX,
    _execution_source,
    _signal_source,
)
from houston.brain.investigation import (
    ACTIVITY_SAMPLE_LIMIT,
    DEEPEN_ACTIVITY_SUBJECT,
    DEEPEN_COMPLETED_MEMORY,
    DEEPEN_SEASONAL_WINDOW,
    FORBIDDEN_SIGNAL_KEYS,
    MEMORY_SAMPLE_LIMIT,
    historical_copy_decision,
)
from houston.brain.models import BrainAnalysis, BrainDossier, BrainDossierItem, BrainSearchRun
from houston.brain.period import CATEGORY_MEMORY, PeriodCopy, PeriodSnapshot
from houston.signals.models import Signal, SignalLifecycleEvent

ROLE_SEASONAL = "saison"
ROLE_ACTIVITY = "echantillon_activite"
ROLE_MEMORY = "memoire"

LIMIT_SEASONAL_EMPTY = "seasonal_window_empty"
LIMIT_SEASONAL_TRUNCATED = "seasonal_truncated"
LIMIT_ACTIVITY_EMPTY = "activity_sample_empty"
LIMIT_SAMPLE_TRUNCATED = "sample_truncated"
LIMIT_MEMORY_EMPTY = "no_completed_analysis"
LIMIT_MEMORY_TRUNCATED = "memory_truncated"
LIMIT_UNKNOWN_ACTIVITY = "unknown_activity_subject"

_MEMORY_TEXT = 500


@dataclass(frozen=True)
class DeepeningOpen:
    accepted: bool
    code: str
    opened_source_ids: tuple[str, ...] = ()
    memory_ids: tuple[str, ...] = ()
    exclusions: tuple[dict, ...] = ()
    limits: tuple[dict, ...] = ()


def open_deepening(
    *,
    analysis: BrainAnalysis,
    snapshot: PeriodSnapshot,
    kind: str,
    subject_key: str,
    activity_subject: str,
    reading_index: int,
    subject_start: date,
    subject_end: date,
) -> DeepeningOpen:
    """Copy one accepted search, or return the refusal. A stored search is not run again."""
    dossier = (
        BrainDossier.objects.filter(analysis_id=analysis.id, closed_at__isnull=False)
        .only("id", "establishment_id", "timezone", "capture_started_at")
        .first()
    )
    if dossier is None:
        return DeepeningOpen(False, "dossier_not_closed")
    code = f"approfondissement:{reading_index}:{kind}"
    existing = (
        BrainSearchRun.objects.filter(dossier_id=dossier.id, code=code).only("criteria").first()
    )
    if existing is not None:
        return _from_criteria(existing.criteria if isinstance(existing.criteria, dict) else {})
    ceiling, timeout = _search_budget(analysis)
    if ceiling <= 0 or timeout <= 0:
        return DeepeningOpen(False, "configuration_unusable")
    if kind == DEEPEN_ACTIVITY_SUBJECT:
        activity_id = _resolve_activity(snapshot, activity_subject)
        if activity_id is None:
            return DeepeningOpen(False, LIMIT_UNKNOWN_ACTIVITY)
    else:
        activity_id = ""
    try:
        return _search(
            analysis=analysis,
            dossier=dossier,
            snapshot=snapshot,
            kind=kind,
            subject_key=subject_key,
            activity_id=activity_id,
            code=code,
            ceiling=ceiling,
            timeout_seconds=timeout,
            subject_start=subject_start,
            subject_end=subject_end,
        )
    except CaptureTimeout:
        return DeepeningOpen(False, "search_timeout")


def _search(
    *,
    analysis,
    dossier,
    snapshot: PeriodSnapshot,
    kind: str,
    subject_key: str,
    activity_id: str,
    code: str,
    ceiling: int,
    timeout_seconds: int,
    subject_start: date,
    subject_end: date,
) -> DeepeningOpen:
    known = {item.source_id for item in snapshot.copies}
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        budget = _Budget(timeout_seconds)
        reliable_from = budget.run(get_history_reliable_from)
        tz = _zone(dossier.timezone)
        studied = _window(snapshot.period_start, snapshot.period_end, tz)
        if kind == DEEPEN_SEASONAL_WINDOW:
            window = _seasonal_window(snapshot, tz, subject_start, subject_end)
            copies, exclusions, limits, examined = _seasonal_copies(
                budget,
                establishment_id=dossier.establishment_id,
                capture_at=snapshot.capture_at,
                window=window,
                studied=studied,
                known=known,
                ceiling=ceiling,
                reliable_from=reliable_from,
                tz=tz,
            )
            criteria_window = {
                "window_start": window.start_on.isoformat(),
                "window_end": window.end_on.isoformat(),
            }
        elif kind == DEEPEN_ACTIVITY_SUBJECT:
            copies, exclusions, limits, examined = _activity_copies(
                budget,
                establishment_id=dossier.establishment_id,
                capture_at=snapshot.capture_at,
                activity_id=activity_id,
                known=known,
                studied=studied,
                reliable_from=reliable_from,
                tz=tz,
            )
            criteria_window = {"activity_subject_id": activity_id}
        elif kind == DEEPEN_COMPLETED_MEMORY:
            copies, exclusions, limits, examined = _memory_copies(
                budget,
                establishment_id=dossier.establishment_id,
                capture_at=snapshot.capture_at,
                analysis_id=analysis.id,
            )
            criteria_window = {}
        else:
            return DeepeningOpen(False, "outside_menu")
        _persist(dossier, copies)
        opened = tuple(copy.source_id for copy in copies if copy.category != CATEGORY_MEMORY)
        memory_ids = tuple(copy.source_id for copy in copies if copy.category == CATEGORY_MEMORY)
        criteria = {
            "kind": kind,
            "subject_key": subject_key,
            **criteria_window,
            "opened_source_ids": list(opened),
            "memory_ids": list(memory_ids),
            "exclusions": list(exclusions),
            "limits": list(limits),
        }
        budget.run(
            lambda: BrainSearchRun.objects.create(
                dossier=dossier,
                code=code,
                criteria=criteria,
                examined_count=examined,
                retained_count=len(copies),
            )
        )
        budget.arm()
    return DeepeningOpen(
        True,
        "accepted",
        opened_source_ids=opened,
        memory_ids=memory_ids,
        exclusions=tuple(exclusions),
        limits=tuple(limits),
    )


def _seasonal_copies(
    budget,
    *,
    establishment_id,
    capture_at,
    window,
    studied,
    known,
    ceiling,
    reliable_from,
    tz,
):
    signal_stubs, signal_truncated = _stubs(
        budget,
        _seasonal_signals(establishment_id, capture_at, window).exclude(id__in=known),
        ceiling,
    )
    execution_stubs, execution_truncated = _stubs(
        budget,
        _seasonal_executions(establishment_id, capture_at, window).exclude(id__in=known),
        ceiling,
    )
    exclusions, signal_ids = _split(signal_stubs, capture_at, ceiling)
    more_exclusions, execution_ids = _split(execution_stubs, capture_at, ceiling)
    exclusions.extend(more_exclusions)
    copies = _project_signals(
        budget,
        signal_ids,
        establishment_id=establishment_id,
        capture_at=capture_at,
        studied=studied,
        reliable_from=reliable_from,
        tz=tz,
        role=ROLE_SEASONAL,
    )
    copies.extend(
        _project_executions(
            budget,
            execution_ids,
            establishment_id=establishment_id,
            capture_at=capture_at,
            studied=studied,
            reliable_from=reliable_from,
            tz=tz,
            role=ROLE_SEASONAL,
        )
    )
    limits = []
    if signal_truncated or execution_truncated:
        limits.append({"code": LIMIT_SEASONAL_TRUNCATED, "source_id": ""})
    if not copies and not exclusions:
        limits.append({"code": LIMIT_SEASONAL_EMPTY, "source_id": ""})
    examined = len(signal_stubs) + len(execution_stubs)
    return copies, exclusions, limits, examined


def _activity_copies(
    budget,
    *,
    establishment_id,
    capture_at,
    activity_id,
    known,
    studied,
    reliable_from,
    tz,
):
    signal_stubs, signal_truncated = _stubs(
        budget,
        Signal.objects.filter(
            establishment_id=establishment_id,
            activity_subject_id=activity_id,
            created_at__lte=capture_at,
        )
        .exclude(id__in=known)
        .order_by("-created_at", "id"),
        ACTIVITY_SAMPLE_LIMIT,
    )
    execution_stubs, execution_truncated = _stubs(
        budget,
        ActionPlanExecution.objects.filter(
            establishment_id=establishment_id,
            activity_subject_id=activity_id,
            created_at__lte=capture_at,
        )
        .exclude(id__in=known)
        .order_by("-created_at", "id"),
        ACTIVITY_SAMPLE_LIMIT,
    )
    exclusions, signal_ids = _split(signal_stubs, capture_at, ACTIVITY_SAMPLE_LIMIT)
    more_exclusions, execution_ids = _split(execution_stubs, capture_at, ACTIVITY_SAMPLE_LIMIT)
    exclusions.extend(more_exclusions)
    copies = _project_signals(
        budget,
        signal_ids,
        establishment_id=establishment_id,
        capture_at=capture_at,
        studied=studied,
        reliable_from=reliable_from,
        tz=tz,
        role=ROLE_ACTIVITY,
    )
    copies.extend(
        _project_executions(
            budget,
            execution_ids,
            establishment_id=establishment_id,
            capture_at=capture_at,
            studied=studied,
            reliable_from=reliable_from,
            tz=tz,
            role=ROLE_ACTIVITY,
        )
    )
    limits = []
    if signal_truncated or execution_truncated:
        limits.append({"code": LIMIT_SAMPLE_TRUNCATED, "source_id": ""})
    if not copies and not exclusions:
        limits.append({"code": LIMIT_ACTIVITY_EMPTY, "source_id": ""})
    return copies, exclusions, limits, len(signal_stubs) + len(execution_stubs)


def _memory_copies(budget, *, establishment_id, capture_at, analysis_id):
    stubs, truncated = _stubs(
        budget,
        BrainAnalysis.objects.filter(
            establishment_id=establishment_id,
            status=BrainAnalysis.Status.COMPLETED,
            created_at__lte=capture_at,
        )
        .exclude(id=analysis_id)
        .order_by("-created_at", "id"),
        MEMORY_SAMPLE_LIMIT,
    )
    exclusions, identifiers = _split(stubs, capture_at, MEMORY_SAMPLE_LIMIT)
    rows = {}
    if identifiers:
        rows = {
            row.id: row
            for row in budget.run(
                lambda: list(
                    BrainAnalysis.objects.filter(id__in=identifiers).only(
                        "id",
                        "result",
                        "published_at",
                        "created_at",
                        "updated_at",
                    )
                )
            )
        }
    copies = []
    for identifier in identifiers:
        row = rows.get(identifier)
        projected = _memory_payload(row) if row is not None else None
        if projected is None:
            exclusions.append({"source_id": str(identifier), "code": "memory_unreadable"})
            continue
        copies.append(
            PeriodCopy(
                source_id=str(identifier),
                category=CATEGORY_MEMORY,
                pole="",
                role=ROLE_MEMORY,
                title=str(projected.get("title") or ""),
                start=None,
                end=None,
                payload=projected,
            )
        )
    limits = []
    if truncated:
        limits.append({"code": LIMIT_MEMORY_TRUNCATED, "source_id": ""})
    if not copies and not exclusions:
        limits.append({"code": LIMIT_MEMORY_EMPTY, "source_id": ""})
    return copies, exclusions, limits, len(stubs)


def _seasonal_signals(establishment_id, capture_at, window):
    event = SignalLifecycleEvent.objects.filter(
        signal_id=OuterRef("pk"),
        establishment_id=establishment_id,
        occurred_at__gte=window.start,
        occurred_at__lt=window.end,
        occurred_at__lte=capture_at,
    )
    return (
        Signal.objects.filter(establishment_id=establishment_id, created_at__lte=capture_at)
        .filter(Q(created_at__gte=window.start, created_at__lt=window.end) | Exists(event))
        .order_by("created_at", "id")
    )


def _seasonal_executions(establishment_id, capture_at, window):
    event = ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution_id=OuterRef("pk"),
        establishment_id=establishment_id,
        occurred_at__gte=window.start,
        occurred_at__lt=window.end,
        occurred_at__lte=capture_at,
    )
    return (
        ActionPlanExecution.objects.filter(
            establishment_id=establishment_id,
            created_at__lte=capture_at,
        )
        .filter(
            Q(created_at__gte=window.start, created_at__lt=window.end)
            | Q(occurrence_date__gte=window.start_on, occurrence_date__lt=window.end_on)
            | Exists(event)
        )
        .order_by("created_at", "id")
    )


def _project_signals(
    budget, identifiers, *, establishment_id, capture_at, studied, reliable_from, tz, role
):
    if not identifiers:
        return []
    rows = budget.run(
        lambda: list(
            Signal.objects.filter(id__in=identifiers)
            .select_related(
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
                "operational_unit",
            )
            .order_by("created_at", "id")
        )
    )
    events = _events(
        budget,
        SignalLifecycleEvent.objects.filter(
            establishment_id=establishment_id,
            signal_id__in=identifiers,
            occurred_at__lte=capture_at,
        ).order_by("occurred_at", "id"),
        "signal_id",
    )
    copies = []
    for row in rows:
        source = _signal_source(
            row,
            tz=tz,
            period=studied,
            capture_at=capture_at,
            events=events.get(row.id, []),
            reliable_from=reliable_from,
            span_end=capture_at.astimezone(tz).date(),
        )
        copies.append(_as_copy(source, role))
    return copies


def _project_executions(
    budget, identifiers, *, establishment_id, capture_at, studied, reliable_from, tz, role
):
    if not identifiers:
        return []
    rows = budget.run(
        lambda: list(
            ActionPlanExecution.objects.filter(id__in=identifiers)
            .defer("description")
            .select_related(
                "pilot_business_unit",
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
            )
            .order_by("created_at", "id")
        )
    )
    events = _events(
        budget,
        ActionPlanExecutionLifecycleEvent.objects.filter(
            establishment_id=establishment_id,
            action_plan_execution_id__in=identifiers,
            occurred_at__lte=capture_at,
        ).order_by("occurred_at", "id"),
        "action_plan_execution_id",
    )
    copies = []
    for row in rows:
        source = _execution_source(
            row,
            tz=tz,
            period=studied,
            capture_at=capture_at,
            events=events.get(row.id, []),
            reliable_from=reliable_from,
            span_end=capture_at.astimezone(tz).date(),
        )
        copies.append(_as_copy(source, role))
    return copies


def _stubs(budget, queryset, ceiling: int):
    rows = budget.run(
        lambda: list(queryset.values("id", "created_at", "updated_at")[: ceiling + 1])
    )
    return rows, len(rows) > ceiling


def _split(stubs, capture_at, ceiling: int):
    exclusions = []
    identifiers = []
    for stub in stubs:
        decision = historical_copy_decision(
            created_at=stub["created_at"],
            updated_at=stub["updated_at"],
            capture_at=capture_at,
        )
        if not decision.copied:
            if decision.exclusion and decision.exclusion != "absent_at_capture":
                exclusions.append({"source_id": str(stub["id"]), "code": decision.exclusion})
            continue
        if len(identifiers) < ceiling:
            identifiers.append(stub["id"])
    return exclusions, identifiers


def _events(budget, queryset, attribute: str) -> dict:
    grouped: dict = {}
    for row in budget.run(lambda: list(queryset)):
        grouped.setdefault(getattr(row, attribute), []).append(row)
    return grouped


def _as_copy(source, role: str) -> PeriodCopy:
    return PeriodCopy(
        source_id=source.source_id,
        category=source.category,
        pole=source.pole,
        role=role,
        title=str(source.payload.get("title") or ""),
        start=source.start,
        end=source.end,
        payload=source.payload,
    )


def _memory_payload(row) -> dict | None:
    result = row.result if isinstance(row.result, dict) else None
    if result is None:
        return None
    subjects = []
    for subject in result.get("subjects") or []:
        if not isinstance(subject, dict):
            continue
        subjects.append(
            {
                "key": _clip(subject.get("key"), 80),
                "statement": _clip(subject.get("statement"), _MEMORY_TEXT),
                "orientation": _clip(subject.get("orientation"), 32),
                "limits": [
                    _clip(item, 500)
                    for item in (subject.get("limits") or [])
                    if isinstance(item, str)
                ][:12],
                "prior_reading": _clip(subject.get("interpretation"), _MEMORY_TEXT),
            }
        )
    limits = []
    for item in result.get("limits") or []:
        if isinstance(item, dict):
            limits.append(
                {
                    "code": _clip(item.get("code"), 80),
                    "message": _clip(item.get("message"), _MEMORY_TEXT),
                }
            )
        elif isinstance(item, str):
            limits.append({"code": "limit", "message": _clip(item, _MEMORY_TEXT)})
    title = subjects[0]["statement"] if subjects else "Analyse terminée"
    payload = {
        "source_id": str(row.id),
        "title": _clip(title, 120),
        "not_evidence": True,
        "schema_version": _clip(result.get("schema_version"), 64),
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "subjects": subjects[:12],
        "limits": limits[:12],
    }
    return _strip_forbidden(payload)


def _persist(dossier, copies: list[PeriodCopy]) -> None:
    if not copies:
        return
    pending = []
    keys = []
    for copy in copies:
        stable = f"{copy.category}:{copy.source_id}"
        keys.append(stable)
        pending.append((stable, copy, False))
        if copy.category == CATEGORY_MEMORY:
            continue
        index_key = f"index:{copy.source_id}"
        keys.append(index_key)
        pending.append((index_key, copy, True))
    existing = set(
        BrainDossierItem.objects.filter(dossier_id=dossier.id, stable_key__in=keys).values_list(
            "stable_key",
            flat=True,
        )
    )
    items = []
    for stable, copy, is_index in pending:
        if stable in existing:
            continue
        if is_index:
            category = CATEGORY_INDEX
            reason = "index_approfondissement"
            payload = {
                "source_id": copy.source_id,
                "category": copy.category,
                "pole": copy.pole,
                "start": copy.start.isoformat() if copy.start else None,
                "end": copy.end.isoformat() if copy.end else None,
                "title": copy.title,
                "text_tokens": json_token_count(
                    {
                        "title": copy.title,
                        "structured_summary": str(copy.payload.get("structured_summary") or ""),
                    }
                ),
            }
        else:
            category = copy.category
            reason = "copie_approfondissement"
            payload = copy.payload
        items.append(
            BrainDossierItem(
                dossier=dossier,
                category=category,
                stable_key=stable,
                role=copy.role,
                payload=payload,
                reason=reason,
            )
        )
    if items:
        BrainDossierItem.objects.bulk_create(items)


def _seasonal_window(snapshot: PeriodSnapshot, tz, subject_start: date, subject_end: date):
    start = subject_start
    end = subject_end
    if end <= start:
        start = snapshot.period_start
        end = snapshot.period_end
    return _window(start - relativedelta(years=1), end - relativedelta(years=1), tz)


def _resolve_activity(snapshot: PeriodSnapshot, requested: str) -> str | None:
    wanted = requested.strip()
    if not wanted:
        return None
    for item in snapshot.copies:
        raw = item.payload.get("activity_subject")
        if not isinstance(raw, dict):
            continue
        identifier = str(raw.get("id") or "")
        name = str(raw.get("name") or "")
        if identifier and wanted in {identifier, name}:
            return identifier
    return None


def _search_budget(analysis: BrainAnalysis) -> tuple[int, int]:
    configuration = analysis.configuration if isinstance(analysis.configuration, dict) else {}
    ceilings = configuration.get("ceilings")
    if not isinstance(ceilings, dict):
        return 0, 0
    try:
        ceiling = int(ceilings["max_candidates_per_category"])
        timeout = int(ceilings["capture_timeout_seconds"])
    except (KeyError, TypeError, ValueError):
        return 0, 0
    if ceiling <= 0 or timeout <= 0:
        return 0, 0
    return ceiling, timeout


def _from_criteria(criteria: dict) -> DeepeningOpen:
    return DeepeningOpen(
        True,
        "accepted",
        opened_source_ids=tuple(str(item) for item in criteria.get("opened_source_ids") or []),
        memory_ids=tuple(str(item) for item in criteria.get("memory_ids") or []),
        exclusions=tuple(row for row in criteria.get("exclusions") or [] if isinstance(row, dict)),
        limits=tuple(row for row in criteria.get("limits") or [] if isinstance(row, dict)),
    )


def _clip(value, limit: int) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit]


def _strip_forbidden(value):
    if isinstance(value, dict):
        return {
            str(key): _strip_forbidden(child)
            for key, child in value.items()
            if str(key) not in FORBIDDEN_SIGNAL_KEYS
        }
    if isinstance(value, list):
        return [_strip_forbidden(child) for child in value]
    return value


class _Budget:
    """Deadline checked before each statement. Python between checks is not preempted."""

    def __init__(self, timeout_seconds: int):
        import time

        self._time = time
        self.deadline = time.monotonic() + timeout_seconds

    def arm(self) -> None:
        remaining = self.deadline - self._time.monotonic()
        if remaining <= 0:
            raise CaptureTimeout()
        millis = max(1, int(remaining * 1000))
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('statement_timeout', %s, true)", [str(millis)])

    def run(self, fn):
        self.arm()
        try:
            return fn()
        except OperationalError as exc:
            if _statement_timeout(exc):
                raise CaptureTimeout() from exc
            raise


def _statement_timeout(exc: BaseException) -> bool:
    seen: BaseException | None = exc
    while seen is not None:
        sqlstate = getattr(seen, "sqlstate", None) or getattr(seen, "pgcode", None)
        if sqlstate == "57014" or "statement timeout" in str(seen).lower():
            return True
        seen = seen.__cause__
    return False
