"""Period snapshot and the first reading selection.

The current executor still captures through ``capture_dossier``. This module
does not query live tables and does not admit an analysis. It freezes copies
the future investigation will store, then chooses the first reading inside
the call window.

The index lists every period copy. It is not the text sent onward. A later
step may append a copy. It does not rewrite one, and a resume reloads the
frozen dossier.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta

from houston.brain.configuration import json_token_count
from houston.brain.investigation import (
    FORBIDDEN_SIGNAL_KEYS,
    PER_CALL_INPUT_TOKENS,
    events_visible_at_capture,
    historical_copy_decision,
    project_signal_copy,
)
from houston.brain.mentions import first_period_mention

LIMIT_PERIOD_EXCEEDS_CALL = "period_exceeds_call"
DISCOVERED_NOT_EXAMINED = "discovered_not_examined"

CATEGORY_SIGNAL = "signal"
CATEGORY_EXECUTION = "execution"
CATEGORY_PLAN = "plan"
CATEGORY_OBJECTIVE = "objective"
_FIELD_CATEGORIES = frozenset({CATEGORY_SIGNAL, CATEGORY_EXECUTION})
_INDEX_CATEGORIES = frozenset({CATEGORY_SIGNAL, CATEGORY_EXECUTION, CATEGORY_PLAN})
_COPY_CATEGORIES = frozenset(
    {CATEGORY_SIGNAL, CATEGORY_EXECUTION, CATEGORY_PLAN, CATEGORY_OBJECTIVE}
)

ROLE_OVERLAP = "chevauchement"
ROLE_LATE = "declaration_tardive"
ROLE_PLAN = "lien_direct"
ROLE_OBJECTIVE = "serie_correspondante"

EXECUTION_COPY_KEYS = frozenset(
    {
        "source_id",
        "title",
        "structured_summary",
        "business_units",
        "activity_subject",
        "occurrence_date",
        "start_at",
        "end_at",
        "status_at_period_start",
        "status_at_period_end",
        "events",
        "action_plan_id",
        "source_signal_id",
    }
)
PLAN_COPY_KEYS = frozenset(
    {
        "source_id",
        "title",
        "structured_summary",
        "pilot_business_unit",
        "source_signal_ids",
        "execution_ids",
        "catalog_status",
    }
)
OBJECTIVE_COPY_KEYS = frozenset(
    {
        "source_id",
        "series_key",
        "indicator",
        "unit",
        "scope",
        "target",
        "period_start",
        "period_end",
    }
)
_ALLOWLIST = {
    CATEGORY_EXECUTION: EXECUTION_COPY_KEYS,
    CATEGORY_PLAN: PLAN_COPY_KEYS,
    CATEGORY_OBJECTIVE: OBJECTIVE_COPY_KEYS,
}


class PeriodSnapshotError(Exception):
    """The snapshot was refused. The code carries no field text."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class PeriodSource:
    """One candidate visible to the capture transaction. Not a live query."""

    source_id: str
    category: str
    pole: str
    start: date | None
    end: date | None
    created_at: datetime
    updated_at: datetime
    payload: dict
    linked_source_ids: tuple[str, ...] = ()
    series_key: str = ""


@dataclass(frozen=True)
class PeriodCopy:
    source_id: str
    category: str
    pole: str
    role: str
    title: str
    start: date | None
    end: date | None
    payload: dict


@dataclass(frozen=True)
class PeriodIndexEntry:
    """Identifier, pole, dates, title, and the cost of title plus summary.

    The summary itself stays on the dossier copy. It is not an index field.
    """

    source_id: str
    category: str
    pole: str
    start: date | None
    end: date | None
    title: str
    text_tokens: int

    def as_record(self) -> dict:
        return {
            "source_id": self.source_id,
            "category": self.category,
            "pole": self.pole,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "title": self.title,
            "text_tokens": self.text_tokens,
        }


@dataclass(frozen=True)
class PeriodOmission:
    source_id: str
    code: str


@dataclass(frozen=True)
class PeriodSnapshot:
    capture_at: datetime
    period_start: date
    period_end: date
    reporting: dict
    series: tuple[dict, ...]
    objectives: tuple[dict, ...]
    copies: tuple[PeriodCopy, ...]
    index: tuple[PeriodIndexEntry, ...]
    omissions: tuple[PeriodOmission, ...]


@dataclass(frozen=True)
class DiscoveredItem:
    source_id: str
    pole: str
    category: str

    def as_record(self) -> dict:
        return {
            "source_id": self.source_id,
            "pole": self.pole,
            "category": self.category,
            "disposition": DISCOVERED_NOT_EXAMINED,
        }


@dataclass(frozen=True)
class FirstReading:
    launched: bool
    limit: str | None
    payload: dict | None
    examined_ids: tuple[str, ...]
    representative_ids: tuple[str, ...]
    discovered_not_examined: tuple[DiscoveredItem, ...]
    competing_period_lead_excluded: bool
    input_tokens: int

    def search_record(self) -> dict:
        """Search note. Unexamined rows keep their pole and not their summary."""
        return {
            "code": "premiere_lecture",
            "limit": self.limit,
            "examined_ids": list(self.examined_ids),
            "discovered_not_examined": [
                item.as_record() for item in self.discovered_not_examined
            ],
        }


class MemoryDossier:
    """Sealed copies. Resume reads this store and has no live-table argument."""

    def __init__(self) -> None:
        self._stored: PeriodSnapshot | None = None

    def save(self, snapshot: PeriodSnapshot) -> None:
        if self._stored is not None:
            raise PeriodSnapshotError("dossier_already_frozen")
        self._stored = resume_period_snapshot(snapshot)

    def load(self) -> PeriodSnapshot:
        if self._stored is None:
            raise PeriodSnapshotError("dossier_missing")
        return resume_period_snapshot(self._stored)

    def add_copies(self, items: tuple[PeriodCopy, ...]) -> None:
        """Append copies. An identifier already stored is left unchanged."""
        current = self.load()
        known = _known_ids(current)
        fresh: list[PeriodCopy] = []
        for item in items:
            if item.source_id in known:
                raise PeriodSnapshotError("copy_already_frozen")
            known.add(item.source_id)
            fresh.append(_clone_copy(item))
        copies = tuple(sorted((*current.copies, *fresh), key=_copy_order))
        self._stored = replace(current, copies=copies, index=_index_for(copies))


def freeze_period_snapshot(
    *,
    capture_at: datetime,
    period_start: date,
    period_end: date,
    reporting: dict,
    series: tuple[dict, ...] = (),
    sources: tuple[PeriodSource, ...] = (),
) -> PeriodSnapshot:
    """Copy the period universe at ``capture_at``. Prior years are not kept.

    A row whose ``updated_at`` is after ``capture_at`` is omitted. Its live
    text is not written down. Events after ``capture_at`` are not kept on a
    row that is copied. Forbidden observation keys refuse the row.
    """
    if period_end <= period_start:
        raise PeriodSnapshotError("period_invalid")
    _require_clean(reporting, "reporting_forbidden")
    for item in series:
        _require_clean(item, "series_forbidden")
    reporting_copy = _json_ready(reporting)
    series_copy = tuple(_json_ready(item) for item in series)
    series_keys = {
        str(item.get("series_key") or "") for item in series_copy if item.get("series_key")
    }

    seen: set[str] = set()
    prepared: list[tuple[PeriodSource, dict]] = []
    omissions: list[PeriodOmission] = []
    for source in sources:
        if source.source_id in seen:
            raise PeriodSnapshotError("duplicate_source")
        seen.add(source.source_id)
        decision = historical_copy_decision(
            created_at=source.created_at,
            updated_at=source.updated_at,
            capture_at=capture_at,
        )
        if not decision.copied:
            code = decision.exclusion or "timestamp_unusable"
            omissions.append(PeriodOmission(source.source_id, code))
            continue
        if source.category not in _COPY_CATEGORIES:
            omissions.append(PeriodOmission(source.source_id, "outside_period"))
            continue
        projected, issues = _project(source, capture_at)
        if issues or projected is None:
            omissions.append(PeriodOmission(source.source_id, "copy_boundary"))
            continue
        prepared.append((source, projected))

    copies: list[PeriodCopy] = []
    kept_field_ids: set[str] = set()
    for source, projected in prepared:
        if source.category not in _FIELD_CATEGORIES:
            continue
        placed = _place_field(source, projected, period_start, period_end)
        if placed is None:
            omissions.append(PeriodOmission(source.source_id, "outside_period"))
            continue
        copies.append(placed)
        kept_field_ids.add(source.source_id)

    objectives: list[dict] = []
    for source, projected in prepared:
        if source.category == CATEGORY_OBJECTIVE:
            if source.series_key not in series_keys:
                omissions.append(PeriodOmission(source.source_id, "series_mismatch"))
                continue
            objectives.append(projected)
            continue
        if source.category != CATEGORY_PLAN:
            continue
        if not any(link in kept_field_ids for link in source.linked_source_ids):
            omissions.append(PeriodOmission(source.source_id, "unlinked_plan"))
            continue
        copies.append(_as_copy(source, projected, ROLE_PLAN, source.start, source.end))

    ordered = tuple(sorted(copies, key=_copy_order))
    return PeriodSnapshot(
        capture_at=capture_at,
        period_start=period_start,
        period_end=period_end,
        reporting=reporting_copy,
        series=series_copy,
        objectives=tuple(objectives),
        copies=ordered,
        index=_index_for(ordered),
        omissions=tuple(sorted(omissions, key=lambda item: item.source_id)),
    )


def resume_period_snapshot(snapshot: PeriodSnapshot) -> PeriodSnapshot:
    """Reload frozen copies. The caller supplies the dossier, not live rows."""
    return PeriodSnapshot(
        capture_at=snapshot.capture_at,
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        reporting=_json_ready(snapshot.reporting),
        series=tuple(_json_ready(item) for item in snapshot.series),
        objectives=tuple(_json_ready(item) for item in snapshot.objectives),
        copies=tuple(_clone_copy(item) for item in snapshot.copies),
        index=tuple(snapshot.index),
        omissions=tuple(snapshot.omissions),
    )


def stored_view(snapshot: PeriodSnapshot) -> dict:
    """JSON view of the dossier. Index records do not carry summaries."""
    return {
        "capture_at": snapshot.capture_at.isoformat(),
        "period_start": snapshot.period_start.isoformat(),
        "period_end": snapshot.period_end.isoformat(),
        "reporting": _json_ready(snapshot.reporting),
        "series": [_json_ready(item) for item in snapshot.series],
        "objectives": [_json_ready(item) for item in snapshot.objectives],
        "copies": [_json_ready(item.payload) for item in snapshot.copies],
        "index": [entry.as_record() for entry in snapshot.index],
        "omissions": [
            {"source_id": item.source_id, "code": item.code} for item in snapshot.omissions
        ],
    }


def reading_payload(snapshot: PeriodSnapshot, examined_ids: tuple[str, ...]) -> dict:
    """Reporting, series, matching objectives, and the selected full texts."""
    by_id = {item.source_id: item for item in snapshot.copies}
    examined = []
    for source_id in examined_ids:
        item = by_id.get(source_id)
        if item is None:
            raise PeriodSnapshotError("unknown_copy")
        examined.append(_json_ready(item.payload))
    return {
        "reporting": _json_ready(snapshot.reporting),
        "series": [_json_ready(item) for item in snapshot.series],
        "objectives": [_json_ready(item) for item in snapshot.objectives],
        "examined": examined,
    }


def reading_input_tokens(
    snapshot: PeriodSnapshot,
    examined_ids: tuple[str, ...],
    *,
    provider: str = "fake",
    model: str = "fake",
) -> int:
    """Token cost of one reading packet. The index is not part of the packet."""
    return json_token_count(
        reading_payload(snapshot, examined_ids),
        provider=provider,
        model=model,
    )


def select_first_reading(
    snapshot: PeriodSnapshot,
    *,
    subject_pole: str,
    subject_start: date,
    subject_end: date,
    input_token_budget: int = PER_CALL_INPUT_TOKENS,
    provider: str = "fake",
    model: str = "fake",
) -> FirstReading:
    """Choose the first reading without dropping another pole.

    Order: reporting and series (and matching objectives), then one full text
    per pole that has a signal or an execution, then the remaining budget.
    Same-pole texts fill that remainder before other poles. A representative
    already chosen is not removed to make room. When the reporting plus one
    text per pole exceeds the window, no packet is built.
    """
    representatives = _representatives(snapshot, subject_pole, subject_start, subject_end)
    representative_ids = tuple(item.source_id for item in representatives)
    mandatory = reading_input_tokens(
        snapshot,
        representative_ids,
        provider=provider,
        model=model,
    )
    if mandatory > input_token_budget:
        discovered = _blocked_discovered(
            snapshot,
            representatives,
            subject_pole,
            subject_start,
            subject_end,
        )
        return FirstReading(
            launched=False,
            limit=LIMIT_PERIOD_EXCEEDS_CALL,
            payload=None,
            examined_ids=(),
            representative_ids=representative_ids,
            discovered_not_examined=discovered,
            competing_period_lead_excluded=bool(representatives),
            input_tokens=mandatory,
        )

    selected = list(representatives)
    discovered_copies: list[PeriodCopy] = []
    for candidate in _extras(snapshot, selected, subject_pole, subject_start, subject_end):
        trial = tuple(item.source_id for item in selected) + (candidate.source_id,)
        cost = reading_input_tokens(snapshot, trial, provider=provider, model=model)
        if cost <= input_token_budget:
            selected.append(candidate)
        else:
            discovered_copies.append(candidate)
    examined_ids = tuple(item.source_id for item in selected)
    return FirstReading(
        launched=True,
        limit=None,
        payload=reading_payload(snapshot, examined_ids),
        examined_ids=examined_ids,
        representative_ids=representative_ids,
        discovered_not_examined=tuple(_discovered(item) for item in discovered_copies),
        competing_period_lead_excluded=False,
        input_tokens=reading_input_tokens(
            snapshot,
            examined_ids,
            provider=provider,
            model=model,
        ),
    )


def _representatives(snapshot, subject_pole, subject_start, subject_end) -> list[PeriodCopy]:
    grouped: dict[str, list[PeriodCopy]] = {}
    for item in snapshot.copies:
        if item.category not in _FIELD_CATEGORIES:
            continue
        grouped.setdefault(item.pole, []).append(item)
    chosen = []
    for pole in sorted(grouped, key=lambda name: (name != subject_pole, name)):
        best = min(
            grouped[pole],
            key=lambda item: _overlap_rank(item, subject_start, subject_end),
        )
        chosen.append(best)
    return chosen


def _extras(snapshot, selected, subject_pole, subject_start, subject_end) -> list[PeriodCopy]:
    selected_ids = {item.source_id for item in selected}
    pending = [
        item
        for item in snapshot.copies
        if item.source_id not in selected_ids and item.category in _INDEX_CATEGORIES
    ]
    return sorted(
        pending,
        key=lambda item: (
            item.pole != subject_pole,
            item.pole,
            *_overlap_rank(item, subject_start, subject_end),
        ),
    )


def _blocked_discovered(snapshot, representatives, subject_pole, subject_start, subject_end):
    extras = _extras(snapshot, representatives, subject_pole, subject_start, subject_end)
    return tuple(_discovered(item) for item in (*representatives, *extras))


def _overlap_rank(item: PeriodCopy, subject_start: date, subject_end: date):
    overlap = _overlap_days(item.start, item.end, subject_start, subject_end)
    return (-overlap, item.start or date.max, item.source_id)


def _overlap_days(
    start: date | None,
    end: date | None,
    window_start: date,
    window_end: date,
) -> int:
    if start is None:
        return 0
    if end is None:
        end = start + timedelta(days=1)
    left = max(start, window_start)
    right = min(end, window_end)
    if right <= left:
        return 0
    return (right - left).days


def _place_field(source: PeriodSource, projected: dict, period_start: date, period_end: date):
    if _overlap_days(source.start, source.end, period_start, period_end) > 0:
        return _as_copy(source, projected, ROLE_OVERLAP, source.start, source.end)
    if source.category != CATEGORY_SIGNAL:
        return None
    mention = _period_mention(projected, period_start, period_end)
    created_on = _civil_date(source.created_at)
    if mention is None or created_on < period_end:
        return None
    payload = dict(projected)
    payload["phenomenon_mentioned_at"] = mention.civil_date.isoformat()
    payload["mention"] = mention.provenance()
    ready = _json_ready(payload)
    return _as_copy(
        source,
        ready,
        ROLE_LATE,
        mention.civil_date,
        mention.civil_date + timedelta(days=1),
    )


def _period_mention(payload: dict, period_start: date, period_end: date):
    return first_period_mention(
        title=str(payload.get("title") or ""),
        structured_summary=str(payload.get("structured_summary") or ""),
        period_start=period_start,
        period_end=period_end,
    )


def _as_copy(source: PeriodSource, payload: dict, role: str, start, end) -> PeriodCopy:
    ready = _json_ready(payload)
    return PeriodCopy(
        source_id=source.source_id,
        category=source.category,
        pole=source.pole,
        role=role,
        title=str(ready.get("title") or ""),
        start=start,
        end=end,
        payload=ready,
    )


def _project(source: PeriodSource, capture_at: datetime) -> tuple[dict | None, tuple[str, ...]]:
    if source.category == CATEGORY_SIGNAL:
        return _project_signal(source.payload, capture_at)
    allowed = _ALLOWLIST.get(source.category)
    if allowed is None:
        return None, ("copy_boundary",)
    return _project_allowlist(source.payload, allowed, capture_at)


def _project_signal(payload: dict, capture_at: datetime) -> tuple[dict | None, tuple[str, ...]]:
    if not isinstance(payload, dict):
        return None, ("payload_invalid",)
    prepared, issue = _prepare_events(payload, capture_at)
    if issue:
        return None, (issue,)
    projected, issues = project_signal_copy(prepared, capture_at=capture_at)
    if projected is None:
        return None, issues
    return _json_ready(projected), ()


def _project_allowlist(payload, allowed, capture_at: datetime):
    if not isinstance(payload, dict):
        return None, ("payload_invalid",)
    prepared, issue = _prepare_events(payload, capture_at)
    if issue:
        return None, (issue,)
    issues: list[str] = []
    for key in prepared:
        if key not in allowed:
            issues.append(f"disallowed:{key}")
    for key in _walk_keys(prepared):
        if key in FORBIDDEN_SIGNAL_KEYS:
            issues.append(f"forbidden:{key}")
    if issues:
        return None, tuple(dict.fromkeys(issues))
    return _json_ready(prepared), ()


def _prepare_events(payload: dict, capture_at: datetime) -> tuple[dict, str | None]:
    if "events" not in payload:
        return payload, None
    events = payload.get("events")
    if not isinstance(events, list):
        return payload, None
    normalized = []
    for event in events:
        if isinstance(event, dict) and isinstance(event.get("occurred_at"), str):
            parsed = _parse_occurred(event["occurred_at"])
            if parsed is None:
                continue
            event = {**event, "occurred_at": parsed}
        normalized.append(event)
    try:
        visible = list(events_visible_at_capture(normalized, capture_at))
    except TypeError:
        return payload, "timestamp_unusable"
    prepared = dict(payload)
    prepared["events"] = visible
    return prepared, None


def _parse_occurred(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _require_clean(payload: object, code: str) -> None:
    if not isinstance(payload, dict):
        raise PeriodSnapshotError(code)
    for key in _walk_keys(payload):
        if key in FORBIDDEN_SIGNAL_KEYS:
            raise PeriodSnapshotError(code)


def _index_for(copies: tuple[PeriodCopy, ...]) -> tuple[PeriodIndexEntry, ...]:
    entries = []
    for item in copies:
        if item.category not in _INDEX_CATEGORIES:
            continue
        summary = str(item.payload.get("structured_summary") or "")
        entries.append(
            PeriodIndexEntry(
                source_id=item.source_id,
                category=item.category,
                pole=item.pole,
                start=item.start,
                end=item.end,
                title=item.title,
                text_tokens=json_token_count(
                    {"title": item.title, "structured_summary": summary}
                ),
            )
        )
    return tuple(entries)


def _known_ids(snapshot: PeriodSnapshot) -> set[str]:
    known = {item.source_id for item in snapshot.copies}
    known.update(str(item.get("source_id") or "") for item in snapshot.objectives)
    reporting_id = snapshot.reporting.get("source_id")
    if reporting_id:
        known.add(str(reporting_id))
    known.discard("")
    return known


def _clone_copy(item: PeriodCopy) -> PeriodCopy:
    return PeriodCopy(
        source_id=item.source_id,
        category=item.category,
        pole=item.pole,
        role=item.role,
        title=item.title,
        start=item.start,
        end=item.end,
        payload=_json_ready(item.payload),
    )


def _copy_order(item: PeriodCopy):
    return (item.category, item.pole, item.source_id)


def _discovered(item: PeriodCopy) -> DiscoveredItem:
    return DiscoveredItem(item.source_id, item.pole, item.category)


def _civil_date(value: datetime) -> date:
    return value.date()


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _json_ready(value):
    return json.loads(json.dumps(value, default=_iso))


def _iso(value):
    if isinstance(value, datetime | date):
        return value.isoformat()
    raise TypeError(type(value).__name__)
