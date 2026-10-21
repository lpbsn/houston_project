"""Searches over a sealed dossier. Live tables are not read.

An incomplete capture or a window outside the reference is unavailable.
An empty page of a complete capture means nothing matched that scope.
"""

from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from houston.analytics.journal import JournalEvent, execution_status_at, signal_status_at
from houston.brain.comparability import (
    compare_measures,
    kpi_from_frozen,
    measured_difference,
    measured_variation,
)
from houston.brain.configuration import canonical_json, json_token_count
from houston.brain.models import BrainDossier, BrainDossierItem
from houston.brain.numbers import decimal_text
from houston.brain.objectives import single_sealed_measure_reading

PAGE_SIZE = 10
QUERY_CHAR_LIMIT = 200
MEMORY_RESULT_TOKEN_CAP = 4_000
NOTE_UNAVAILABLE = (
    "Source non capturée ou hors périmètre : indisponible. "
    "Ce n'est pas une absence dans le métier."
)
NOTE_EMPTY = "Aucun élément dans le périmètre recherché."

TOOL_SCHEMAS = (
    {
        "name": "compare",
        "description": "Verdict de comparabilité entre deux mesures scellées.",
        "parameters": {
            "left_item_id": "Identifiant de mesure.",
            "right_item_id": "Identifiant de mesure.",
            "kind": "temporal ou actual_vs_reference.",
        },
    },
    {
        "name": "search_signals",
        "description": (
            "Signaux structurés scellés. match_count est le total du filtre, "
            "returned_count la page. Le texte ne porte que sur le titre et le résumé."
        ),
        "parameters": {
            "window_start": "Date inclusive.",
            "window_end": "Date exclusive.",
            "temporal_basis": "declaration ou occurrence.",
            "pole": "Pôle, facultatif.",
            "activity": "Activité, facultative.",
            "text": "Texte facultatif, titre et résumé seulement.",
            "cursor": "Page suivante, facultatif.",
        },
    },
    {
        "name": "search_actions",
        "description": (
            "Plans et exécutions scellés : titre, description, dates et liens. "
            "match_count est distinct de returned_count."
        ),
        "parameters": {
            "window_start": "Date inclusive.",
            "window_end": "Date exclusive.",
            "kind": "plan, execution ou all.",
            "pole": "Pôle, facultatif.",
            "activity": "Activité, facultative.",
            "text": "Texte facultatif, titre et description.",
            "cursor": "Page suivante, facultatif.",
        },
    },
    {
        "name": "search_objectives",
        "description": (
            "Révisions d'objectifs acceptées. Une seule mesure correspondante "
            "du reporting joint le résultat numérique déjà calculé."
        ),
        "parameters": {
            "window_start": "Date inclusive, facultative.",
            "window_end": "Date exclusive, facultative.",
            "text": "Texte facultatif sur l'indicateur.",
            "cursor": "Page suivante, facultatif.",
        },
    },
    {
        "name": "search_reportings",
        "description": "Mesures des reportings antérieurs confirmés, marquées comme documents.",
        "parameters": {
            "window_start": "Date inclusive, facultative.",
            "window_end": "Date exclusive, facultative.",
            "text": "Texte facultatif sur le libellé.",
            "cursor": "Page suivante, facultatif.",
        },
    },
    {
        "name": "search_memory",
        "description": (
            "Résultats publiés d'analyses antérieures, marqués comme mémoire décisionnelle."
        ),
        "parameters": {
            "window_start": "Date inclusive, facultative.",
            "window_end": "Date exclusive, facultative.",
            "text": "Texte facultatif.",
            "cursor": "Page suivante, facultatif.",
        },
    },
)


class SealedView:
    """Copies of one closed dossier, indexed for the tools."""

    def __init__(self, dossier: BrainDossier, items: list[BrainDossierItem]):
        self.dossier = dossier
        self.items = items
        self.by_id = {str(item.id): item for item in items}
        self.tz = ZoneInfo(dossier.timezone or "UTC")
        self.capture_at = dossier.capture_started_at
        coverage_item = next((item for item in items if item.category == "coverage"), None)
        payload = coverage_item.payload if coverage_item is not None else {}
        self.coverage = payload if isinstance(payload, dict) else {}
        raw_reliable = self.coverage.get("reliable_from")
        self.reliable_from = _parse_dt(raw_reliable) if raw_reliable else None

    def of(self, category: str) -> list[BrainDossierItem]:
        return [item for item in self.items if item.category == category]

    def family_complete(self, name: str) -> bool:
        families = self.coverage.get("families")
        if not isinstance(families, dict):
            return False
        family = families.get(name)
        return isinstance(family, dict) and bool(family.get("complete"))


def execute_tool(
    view: SealedView,
    name: str,
    arguments: dict,
    *,
    examined: set[str],
    remaining_copies: int,
    consultations_remaining: int,
) -> dict:
    """Run one tool against the sealed copies and return a trace entry body."""
    arguments = arguments if isinstance(arguments, dict) else {}
    handlers = {
        "compare": lambda: _compare(view, arguments),
        "search_signals": lambda: _search_signals(view, arguments, examined, remaining_copies),
        "search_actions": lambda: _search_actions(view, arguments, examined, remaining_copies),
        "search_objectives": lambda: _search_objectives(
            view, arguments, examined, remaining_copies
        ),
        "search_reportings": lambda: _search_reportings(
            view, arguments, examined, remaining_copies
        ),
        "search_memory": lambda: _search_memory(view, arguments, examined, remaining_copies),
    }
    body = handlers.get(name, lambda: _unavailable("unknown_tool"))()
    body["envelope"]["consultations_remaining"] = consultations_remaining
    return {"tool": name, "arguments": arguments, **body}


def render_tool_result(view: SealedView, entry: dict) -> dict:
    """Rebuild the text of one committed call from the sealed copies."""
    name = str(entry.get("tool") or "")
    envelope = dict(entry.get("envelope") or {})
    rows = []
    for item_id in entry.get("item_ids") or []:
        item = view.by_id.get(str(item_id))
        if item is None:
            rows.append(
                {
                    "item_id": str(item_id),
                    "availability": "unavailable",
                    "reason": "copy_missing",
                    "note": NOTE_UNAVAILABLE,
                }
            )
            continue
        rows.append(_render_row(view, name, item, entry.get("arguments") or {}))
    envelope["returned_count"] = len(rows)
    envelope["rows"] = rows
    return envelope


def _search_signals(view, arguments, examined, remaining_copies) -> dict:
    omitted = _omitted(view, "signal")
    if not view.family_complete("signal") and omitted == 0:
        return _unavailable("capture_incomplete")
    window = _required_window(view, arguments, clip=True)
    if window.get("unavailable"):
        return _unavailable(window["reason"])
    basis = str(arguments.get("temporal_basis") or "declaration")
    if basis not in {"declaration", "occurrence"}:
        return _unavailable("temporal_basis_invalid")
    query, truncated_query = _query(arguments.get("text"))
    pole = str(arguments.get("pole") or "").strip()
    activity = str(arguments.get("activity") or "").strip()
    matched = []
    undated = 0
    for item in view.of("signal"):
        payload = _payload(item)
        created = _parse_dt(payload.get("created_at"))
        if basis == "declaration":
            if created is None or not _in_datetime(created, window):
                continue
        else:
            occurred = _parse_date(payload.get("occurrence_date"))
            if occurred is None:
                if created is not None and _in_datetime(created, window):
                    undated += 1
                continue
            if not _in_dates(occurred, window):
                continue
        if not _pole_matches(payload, pole) or not _activity_matches(payload, activity):
            continue
        if query and query.casefold() not in _signal_text(payload).casefold():
            continue
        matched.append(item)
    matched.sort(key=_created_sort)
    partial = False
    if omitted:
        oldest = _captured_from(view, "signal")
        if basis != "declaration" or oldest is None:
            partial = True
        else:
            partial = window["start_dt"] < oldest.astimezone(window["start_dt"].tzinfo)
    return _apply_capture_limit(
        _page(
            matched,
            arguments,
            examined,
            remaining_copies,
            extra={
                "temporal_basis": basis,
                "clipped_to_reference": bool(window.get("clipped")),
                "excluded_without_occurrence_date": undated if basis == "occurrence" else 0,
                "query_truncated": truncated_query,
                "window_applied": window.get("applied"),
            },
        ),
        omitted,
        partial=partial,
    )


def _search_actions(view, arguments, examined, remaining_copies) -> dict:
    kind = str(arguments.get("kind") or "all")
    if kind not in {"plan", "execution", "all"}:
        return _unavailable("action_kind_invalid")
    window = _required_window(view, arguments, clip=False)
    if window.get("unavailable"):
        return _unavailable(window["reason"])
    query, truncated_query = _query(arguments.get("text"))
    pole = str(arguments.get("pole") or "").strip()
    activity = str(arguments.get("activity") or "").strip()
    incomplete = []
    omitted = 0
    for family in ("plan", "execution"):
        if kind not in {family, "all"}:
            continue
        if not view.family_complete(family):
            incomplete.append(family)
            omitted += _omitted(view, family)
    collected = []
    for family, category in (("plan", "plan"), ("execution", "execution")):
        if kind not in {family, "all"}:
            continue
        if family in incomplete and _omitted(view, family) == 0:
            continue
        for item in view.of(category):
            payload = _payload(item)
            if not _action_in_window(payload, window):
                continue
            if not _pole_matches(payload, pole) or not _activity_matches(payload, activity):
                continue
            if query and query.casefold() not in _action_text(payload).casefold():
                continue
            collected.append(item)
    if incomplete and not collected:
        return _unavailable("capture_incomplete")
    collected.sort(key=_created_sort)
    cursor = _cursor(arguments.get("cursor"))
    if cursor.get("unavailable"):
        return _unavailable(cursor["reason"])
    page = _slice_page(collected, cursor["offset"], examined, remaining_copies)
    envelope = _page_envelope(
        len(collected),
        page,
        extra={
            "query_truncated": truncated_query,
            "window_applied": window.get("applied"),
            "unavailable_families": incomplete,
        },
    )
    if incomplete and omitted == 0:
        envelope["note"] = NOTE_UNAVAILABLE
    return _apply_capture_limit(
        {"item_ids": page["item_ids"], "envelope": envelope},
        omitted,
        partial=omitted > 0,
    )


def _search_objectives(view, arguments, examined, remaining_copies) -> dict:
    omitted = _omitted(view, "objective")
    if not view.family_complete("objective") and omitted == 0:
        return _unavailable("capture_incomplete")
    window = _optional_window(arguments, view.tz)
    if window.get("unavailable"):
        return _unavailable(window["reason"])
    query, truncated_query = _query(arguments.get("text"))
    matched = []
    unspecified = 0
    for item in view.of("objective"):
        payload = _payload(item)
        if query and query.casefold() not in str(payload.get("indicator") or "").casefold():
            continue
        if window.get("active") and not _objective_overlaps(payload, window):
            if not payload.get("measurement_period_start"):
                unspecified += 1
            continue
        matched.append(item)
    matched.sort(key=lambda item: str(_payload(item).get("indicator") or ""))
    return _apply_capture_limit(
        _page(
            matched,
            arguments,
            examined,
            remaining_copies,
            extra={
                "query_truncated": truncated_query,
                "omitted_without_measurement_period": unspecified,
                "window_applied": window.get("applied"),
            },
        ),
        omitted,
        partial=omitted > 0,
    )


def _search_reportings(view, arguments, examined, remaining_copies) -> dict:
    omitted = _omitted(view, "reporting")
    if not view.family_complete("reporting") and omitted == 0:
        return _unavailable("capture_incomplete")
    window = _optional_window(arguments, view.tz)
    if window.get("unavailable"):
        return _unavailable(window["reason"])
    query, truncated_query = _query(arguments.get("text"))
    matched = []
    for item in view.of("reporting"):
        payload = _payload(item)
        if window.get("active") and not _reporting_overlaps(payload, window):
            continue
        if query and payload.get("availability") != "unavailable":
            if query.casefold() not in str(payload.get("label") or "").casefold():
                continue
        matched.append(item)
    matched.sort(
        key=lambda item: str(
            _payload(item).get("reporting_period_start") or _payload(item).get("period_start") or ""
        )
    )
    return _apply_capture_limit(
        _page(
            matched,
            arguments,
            examined,
            remaining_copies,
            extra={"query_truncated": truncated_query, "window_applied": window.get("applied")},
        ),
        omitted,
        partial=omitted > 0,
    )


def _search_memory(view, arguments, examined, remaining_copies) -> dict:
    omitted = _omitted(view, "memory")
    if not view.family_complete("memory") and omitted == 0:
        return _unavailable("capture_incomplete")
    window = _optional_window(arguments, view.tz)
    if window.get("unavailable"):
        return _unavailable(window["reason"])
    query, truncated_query = _query(arguments.get("text"))
    matched = []
    for item in view.of("analysis_memory"):
        payload = _payload(item)
        published = _parse_dt(payload.get("published_at"))
        if window.get("active") and (published is None or not _in_datetime(published, window)):
            continue
        if query and query.casefold() not in canonical_json(payload.get("result")).casefold():
            continue
        matched.append(item)
    matched.sort(key=lambda item: str(_payload(item).get("published_at") or ""))
    return _apply_capture_limit(
        _page(
            matched,
            arguments,
            examined,
            remaining_copies,
            extra={"query_truncated": truncated_query, "window_applied": window.get("applied")},
        ),
        omitted,
        partial=omitted > 0,
    )


def _compare(view, arguments) -> dict:
    left = view.by_id.get(str(arguments.get("left_item_id") or ""))
    right = view.by_id.get(str(arguments.get("right_item_id") or ""))
    kind = str(arguments.get("kind") or "")
    if left is None or right is None:
        return _unavailable("measure_not_captured")
    left_code, left_measure = kpi_from_frozen(_payload(left))
    right_code, right_measure = kpi_from_frozen(_payload(right))
    if left_measure is None or right_measure is None:
        return _unavailable(left_code or right_code or "measure_unreadable")
    verdict = compare_measures(left_measure, right_measure, kind)
    difference = None
    variation = None
    if verdict.accepted:
        gap = measured_difference(left_measure, right_measure, kind=kind)
        if gap.accepted and gap.value is not None:
            difference = decimal_text(gap.value)
        if kind == "temporal":
            if left_measure.period_start <= right_measure.period_start:
                base, current = left_measure, right_measure
            else:
                base, current = right_measure, left_measure
            relative = measured_variation(base, current)
            if relative.accepted and relative.value is not None:
                variation = decimal_text(relative.value)
    return {
        "item_ids": [str(left.id), str(right.id)],
        "envelope": {
            "availability": "available",
            "unavailable_reason": "",
            "match_count": 2,
            "returned_count": 2,
            "next_cursor": None,
            "truncation": "",
            "empty_means": None,
            "note": "",
            "compare": {
                "accepted": verdict.accepted,
                "code": verdict.code,
                "kind": kind,
                "reserve": verdict.reserve,
                "left_item_id": str(left.id),
                "right_item_id": str(right.id),
                "difference": difference,
                "variation": variation,
            },
        },
    }


def _page(matched, arguments, examined, remaining_copies, *, extra) -> dict:
    cursor = _cursor(arguments.get("cursor"))
    if cursor.get("unavailable"):
        return _unavailable(cursor["reason"])
    page = _slice_page(matched, cursor["offset"], examined, remaining_copies)
    return {
        "item_ids": page["item_ids"],
        "envelope": _page_envelope(len(matched), page, extra=extra),
    }


def _slice_page(matched, offset, examined, remaining_copies) -> dict:
    item_ids = []
    index = offset
    truncation = ""
    fresh = 0
    while index < len(matched) and len(item_ids) < PAGE_SIZE:
        item_id = str(matched[index].id)
        if item_id not in examined:
            if fresh >= remaining_copies:
                truncation = "copy_budget"
                break
            fresh += 1
        item_ids.append(item_id)
        index += 1
    return {
        "item_ids": item_ids,
        "next_cursor": str(index) if index < len(matched) else None,
        "truncation": truncation,
    }


def _page_envelope(match_count, page, *, extra) -> dict:
    envelope = {
        "availability": "available",
        "unavailable_reason": "",
        "match_count": match_count,
        "returned_count": len(page["item_ids"]),
        "next_cursor": page["next_cursor"],
        "truncation": page["truncation"],
        "empty_means": "none_in_searched_scope" if match_count == 0 else None,
        "note": NOTE_EMPTY if match_count == 0 else "",
    }
    if page["truncation"]:
        envelope["note"] = "Page tronquée : la suite n'a pas été renvoyée."
    envelope.update(extra)
    return envelope


def _apply_capture_limit(body: dict, omitted: int, *, partial: bool) -> dict:
    """Keep sealed rows usable when older copies were left out of the dossier."""
    envelope = body.get("envelope") or {}
    if envelope.get("availability") != "available" or omitted <= 0:
        return body
    envelope["capture_omitted"] = omitted
    if not partial:
        return body
    if not body.get("item_ids") and not envelope.get("truncation"):
        return _unavailable("capture_incomplete")
    envelope["empty_means"] = None
    note = NOTE_UNAVAILABLE
    if envelope.get("truncation"):
        note = f"{note} Page tronquée : la suite n'a pas été renvoyée."
    envelope["note"] = note
    return body


def _omitted(view, family: str) -> int:
    families = view.coverage.get("families")
    if not isinstance(families, dict):
        return 0
    raw = families.get(family)
    if not isinstance(raw, dict):
        return 0
    try:
        return max(0, int(raw.get("omitted") or 0))
    except (TypeError, ValueError):
        return 0


def _captured_from(view, category: str) -> datetime | None:
    moments = []
    for item in view.of(category):
        moment = _parse_dt(_payload(item).get("created_at"))
        if moment is not None:
            moments.append(moment)
    if not moments:
        return None
    return min(moments)


def _unavailable(reason: str) -> dict:
    return {
        "item_ids": [],
        "envelope": {
            "availability": "unavailable",
            "unavailable_reason": reason,
            "match_count": None,
            "returned_count": 0,
            "next_cursor": None,
            "truncation": "",
            "empty_means": None,
            "note": NOTE_UNAVAILABLE,
        },
    }


def _render_row(view, name, item, arguments) -> dict:
    payload = _payload(item)
    if name == "search_signals":
        return _signal_row(view, item, payload, arguments)
    if name == "search_actions":
        return _action_row(view, item, payload, arguments)
    if name == "search_objectives":
        return _objective_row(view, item, payload)
    if name == "search_reportings":
        return _reporting_row(item, payload)
    if name == "search_memory":
        return _memory_row(item, payload)
    return {
        "item_id": str(item.id),
        "label": payload.get("label"),
        "value": payload.get("value"),
        "unit": payload.get("unit"),
        "period_start": payload.get("period_start"),
        "period_end": payload.get("period_end"),
    }


def _signal_row(view, item, payload, arguments) -> dict:
    window = _required_window(view, arguments, clip=True)
    status = None
    if not window.get("unavailable"):
        status = _status(view, payload, window.get("status_at"), "signal")
    return {
        "item_id": str(item.id),
        "source_kind": "signal",
        "title": payload.get("title"),
        "structured_summary": payload.get("structured_summary"),
        "created_at": payload.get("created_at"),
        "occurrence_date": payload.get("occurrence_date"),
        "occurrence_provenance": payload.get("occurrence_provenance"),
        "affected_business_unit": payload.get("affected_business_unit"),
        "responsible_business_unit": payload.get("responsible_business_unit"),
        "activity_subject": payload.get("activity_subject"),
        "location_text": payload.get("location_text"),
        "issue_focus": payload.get("issue_focus"),
        "expected_action": payload.get("expected_action"),
        "status_at_window": status,
    }


def _action_row(view, item, payload, arguments) -> dict:
    window = _required_window(view, arguments, clip=False)
    kind = "execution" if item.category == "execution" else "plan"
    status = None
    if kind == "execution" and not window.get("unavailable"):
        status = _status(view, payload, window.get("status_at"), "execution")
    row = {
        "item_id": str(item.id),
        "source_kind": kind,
        "title": payload.get("title"),
        "description": payload.get("description"),
        "created_at": payload.get("created_at"),
        "occurrence_date": payload.get("occurrence_date"),
        "start_at": payload.get("start_at"),
        "end_at": payload.get("end_at"),
        "pilot_business_unit": payload.get("pilot_business_unit"),
        "affected_business_unit": payload.get("affected_business_unit"),
        "responsible_business_unit": payload.get("responsible_business_unit"),
        "activity_subject": payload.get("activity_subject"),
        "action_plan_id": payload.get("action_plan_id"),
        "source_signal_id": payload.get("source_signal_id"),
        "execution_ids": payload.get("execution_ids"),
        "source_signal_ids": payload.get("source_signal_ids"),
        "links_complete": payload.get("links_complete"),
        "catalog_status_at_reference": payload.get("catalog_status_at_reference"),
        "status_at_window": status,
    }
    if kind == "plan" and payload.get("links_complete") is False:
        row["links_note"] = NOTE_UNAVAILABLE
    return row


def _objective_row(view, item, payload) -> dict:
    measures = [
        (str(measure.id), _payload(measure))
        for measure in view.of("document")
        if measure.role == "mesure"
    ]
    return {
        "item_id": str(item.id),
        "source_kind": "objective",
        "indicator": payload.get("indicator"),
        "unit": payload.get("unit"),
        "scope": payload.get("scope"),
        "target": payload.get("target"),
        "success_condition": payload.get("success_condition"),
        "decision": payload.get("decision"),
        "due_on": payload.get("due_on"),
        "measurement_period_start": payload.get("measurement_period_start"),
        "measurement_period_end": payload.get("measurement_period_end"),
        "method": payload.get("method"),
        "numeric_result": single_sealed_measure_reading(payload, measures),
    }


def _reporting_row(item, payload) -> dict:
    if payload.get("availability") == "unavailable":
        return {
            "item_id": str(item.id),
            "source_kind": "document",
            "availability": "unavailable",
            "reason": payload.get("reason") or "measures_not_captured",
            "note": NOTE_UNAVAILABLE,
            "period_start": payload.get("period_start"),
            "period_end": payload.get("period_end"),
        }
    return {
        "item_id": str(item.id),
        "source_kind": "document",
        "availability": "available",
        "label": payload.get("label"),
        "value": payload.get("value"),
        "unit": payload.get("unit"),
        "definition": payload.get("definition"),
        "scope": payload.get("scope"),
        "period_start": payload.get("period_start"),
        "period_end": payload.get("period_end"),
        "reporting_id": payload.get("reporting_id"),
        "reporting_period_start": payload.get("reporting_period_start"),
        "reporting_period_end": payload.get("reporting_period_end"),
    }


def _memory_row(item, payload) -> dict:
    if payload.get("availability") == "unavailable":
        return {
            "item_id": str(item.id),
            "source_kind": "decision_memory",
            "availability": "unavailable",
            "reason": payload.get("reason") or "result_not_captured",
            "note": NOTE_UNAVAILABLE,
            "published_at": payload.get("published_at"),
        }
    result = payload.get("result")
    if json_token_count(result) > MEMORY_RESULT_TOKEN_CAP:
        return {
            "item_id": str(item.id),
            "source_kind": "decision_memory",
            "availability": "unavailable",
            "reason": "payload_exceeds_call",
            "note": NOTE_UNAVAILABLE,
            "published_at": payload.get("published_at"),
        }
    return {
        "item_id": str(item.id),
        "source_kind": "decision_memory",
        "availability": "available",
        "published_at": payload.get("published_at"),
        "result": result,
    }


def _status(view, payload, at, kind: str) -> dict:
    if at is None:
        return {"availability": "unavailable", "reason": "window_required"}
    if at > view.capture_at:
        return {"availability": "unavailable", "reason": "after_reference"}
    if view.reliable_from is None or at < view.reliable_from:
        return {"availability": "unavailable", "reason": "history_unreliable"}
    events = []
    for raw in payload.get("events") or []:
        if not isinstance(raw, dict):
            continue
        occurred = _parse_dt(raw.get("occurred_at"))
        if occurred is None:
            continue
        metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
        events.append(JournalEvent(str(raw.get("event_type") or ""), occurred, metadata))
    reconstruct = signal_status_at if kind == "signal" else execution_status_at
    value = reconstruct(at=at, reliable_from=view.reliable_from, events=events)
    if value is None:
        return {"availability": "unavailable", "reason": "history_unreliable"}
    return {"availability": "available", "value": value}


def _required_window(view, arguments, *, clip: bool) -> dict:
    start = _parse_date(arguments.get("window_start"))
    end = _parse_date(arguments.get("window_end"))
    if start is None or end is None or end <= start:
        return {"unavailable": True, "reason": "window_required"}
    start_dt = datetime.combine(start, time.min, tzinfo=view.tz)
    end_dt = datetime.combine(end, time.min, tzinfo=view.tz)
    clipped = False
    applied_end = end_dt
    status_at_value = end_dt
    if clip and end_dt > view.capture_at:
        if start_dt >= view.capture_at:
            return {"unavailable": True, "reason": "after_reference"}
        applied_end = view.capture_at
        status_at_value = view.capture_at
        clipped = True
    if not clip and end_dt > view.capture_at:
        status_at_value = view.capture_at if start_dt < view.capture_at else end_dt
    return {
        "unavailable": False,
        "start": start,
        "end": end,
        "start_dt": start_dt,
        "end_dt": applied_end,
        "clipped": clipped,
        "status_at": status_at_value,
        "applied": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "clipped_to_reference": clipped,
        },
    }


def _optional_window(arguments, tz) -> dict:
    raw_start = arguments.get("window_start")
    raw_end = arguments.get("window_end")
    if raw_start in (None, "") and raw_end in (None, ""):
        return {"unavailable": False, "active": False, "applied": None}
    start = _parse_date(raw_start)
    end = _parse_date(raw_end)
    if start is None or end is None or end <= start:
        return {"unavailable": True, "reason": "window_invalid"}
    return {
        "unavailable": False,
        "active": True,
        "start": start,
        "end": end,
        "start_dt": datetime.combine(start, time.min, tzinfo=tz),
        "end_dt": datetime.combine(end, time.min, tzinfo=tz),
        "applied": {"start": start.isoformat(), "end": end.isoformat()},
    }


def _in_datetime(moment: datetime, window: dict) -> bool:
    zone = window["start_dt"].tzinfo
    return window["start_dt"] <= moment.astimezone(zone) < window["end_dt"]


def _in_dates(day: date, window: dict) -> bool:
    return window["start"] <= day < window["end"]


def _action_in_window(payload, window) -> bool:
    """Match a civil occurrence, a timestamp in the establishment zone, or a covering interval.

    The UTC calendar date of an aware timestamp is not the establishment's day.
    An execution that starts before the window and ends after it is in that window.
    """
    occurred = _parse_date(payload.get("occurrence_date"))
    if occurred is not None and _in_dates(occurred, window):
        return True
    start = _parse_dt(payload.get("start_at"))
    end = _parse_dt(payload.get("end_at"))
    for moment in (start, end, _parse_dt(payload.get("created_at"))):
        if moment is not None and _moment_in_window(moment, window):
            return True
    if start is not None and end is not None and _interval_overlaps(start, end, window):
        return True
    return False


def _as_window_time(moment: datetime, window: dict) -> datetime:
    zone = window["start_dt"].tzinfo
    if moment.tzinfo is None:
        return moment.replace(tzinfo=zone)
    return moment.astimezone(zone)


def _moment_in_window(moment: datetime, window: dict) -> bool:
    local = _as_window_time(moment, window)
    return window["start_dt"] <= local < window["end_dt"]


def _interval_overlaps(start: datetime, end: datetime, window: dict) -> bool:
    local_start = _as_window_time(start, window)
    local_end = _as_window_time(end, window)
    return local_start < window["end_dt"] and local_end > window["start_dt"]


def _objective_overlaps(payload, window) -> bool:
    start = _parse_date(payload.get("measurement_period_start"))
    end = _parse_date(payload.get("measurement_period_end"))
    if start is None or end is None:
        return False
    return start < window["end"] and end > window["start"]


def _reporting_overlaps(payload, window) -> bool:
    start = _parse_date(payload.get("reporting_period_start") or payload.get("period_start"))
    end = _parse_date(payload.get("reporting_period_end") or payload.get("period_end"))
    if start is None or end is None:
        return False
    return start < window["end"] and end > window["start"]


def _pole_matches(payload, pole: str) -> bool:
    if not pole:
        return True
    wanted = pole.casefold()
    for key in (
        "affected_business_unit",
        "responsible_business_unit",
        "pilot_business_unit",
    ):
        block = payload.get(key) or {}
        if not isinstance(block, dict):
            continue
        if str(block.get("id") or "").casefold() == wanted:
            return True
        if str(block.get("name") or "").casefold() == wanted:
            return True
    return False


def _activity_matches(payload, activity: str) -> bool:
    if not activity:
        return True
    block = payload.get("activity_subject") or {}
    if not isinstance(block, dict):
        return False
    wanted = activity.casefold()
    return str(block.get("id") or "").casefold() == wanted or str(
        block.get("label") or ""
    ).casefold() == wanted


def _signal_text(payload) -> str:
    return f"{payload.get('title') or ''}\n{payload.get('structured_summary') or ''}"


def _action_text(payload) -> str:
    return f"{payload.get('title') or ''}\n{payload.get('description') or ''}"


def _query(value) -> tuple[str, bool]:
    text = str(value or "").strip()
    if len(text) <= QUERY_CHAR_LIMIT:
        return text, False
    return text[:QUERY_CHAR_LIMIT], True


def _cursor(value) -> dict:
    if value in (None, ""):
        return {"offset": 0}
    try:
        offset = int(str(value))
    except (TypeError, ValueError):
        return {"unavailable": True, "reason": "cursor_invalid"}
    if offset < 0:
        return {"unavailable": True, "reason": "cursor_invalid"}
    return {"offset": offset}


def _created_sort(item: BrainDossierItem):
    payload = _payload(item)
    return (str(payload.get("created_at") or ""), str(item.id))


def _payload(item) -> dict:
    payload = item.payload
    return payload if isinstance(payload, dict) else {}


def _parse_date(value) -> date | None:
    if value in (None, ""):
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_dt(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None
