"""Bounded investigation loop.

The versioned executor calls this after the period dossier is closed. A reading
sees frozen copies only. A deepening either opens an identifier already in the
period index, or appends one closed-menu search. Nothing here admits an
analysis, writes the public result, or calls a paid provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db import transaction

from houston.brain.configuration import digest, json_token_count
from houston.brain.deepening import (
    LIMIT_MEMORY_TRUNCATED,
    LIMIT_SAMPLE_TRUNCATED,
    LIMIT_SEASONAL_TRUNCATED,
    DeepeningOpen,
    open_deepening,
)
from houston.brain.dossier import open_indexed_copy, reload_period_dossier
from houston.brain.errors import BrainWorkError
from houston.brain.investigation import (
    DEEPEN_PERIOD_INDEX,
    DEEPENING_MENU,
    MAX_DEEPENINGS,
    TREATMENT_CANCELED,
    TREATMENT_COMPLETED,
    TREATMENT_FAILED,
    DeepeningDecision,
    InvestigationFacts,
    SubjectFinding,
    accept_deepening,
    investigation_ceilings,
    investigation_timing,
    qualify,
)
from houston.brain.investigation_contract import (
    SCHEMA_VERSION,
    InvestigationReading,
    assess_reading,
    causal_evidence_issue,
    cited_item_ids,
    correction_rules,
    investigation_call_tokens,
    investigation_prompt,
    investigation_response_schema,
    output_token_count,
    subject_figures_verified,
)
from houston.brain.models import BrainAnalysis, BrainDossier, BrainSearchRun
from houston.brain.period import (
    CATEGORY_EXECUTION,
    CATEGORY_MEMORY,
    CATEGORY_PLAN,
    CATEGORY_SIGNAL,
    DISCOVERED_NOT_EXAMINED,
    LIMIT_PERIOD_EXCEEDS_CALL,
    PeriodCopy,
    PeriodSnapshot,
    PeriodSnapshotError,
    reading_allowance,
    select_first_reading,
)
from houston.brain.provider import BrainProvider, BrainProviderUnavailable

STOP_CODE = "investigation_stop"
_CORRECTION_CODE = "correction:1"


def public_search_code(code: str) -> bool:
    """Searches the analysis API may show. Engine steps stay on the dossier."""
    if code == STOP_CODE or code == _CORRECTION_CODE:
        return False
    return not code.startswith(("lecture:", "decision:"))
_TREATMENT_INTERRUPTED = "interrupted"
_COVERAGE_CODES = frozenset(
    {
        "modified_after_capture",
        LIMIT_SEASONAL_TRUNCATED,
        LIMIT_SAMPLE_TRUNCATED,
        LIMIT_MEMORY_TRUNCATED,
    }
)


@dataclass(frozen=True)
class InvestigationOutcome:
    """What the loop decided. ``published`` stays false until publication."""

    treatment: str
    code: str
    qualification: str | None
    investigation_succeeded: bool
    semantic_readings: int
    provider_calls: int
    corrections: int
    examined_ids: tuple[str, ...]
    discovered_not_examined: tuple[str, ...]
    contradictions: tuple[dict, ...]
    full_text_ids: tuple[str, ...]
    withheld_contradiction_ids: tuple[str, ...]
    limits: tuple[dict, ...] = ()
    replay_step: str = ""
    published: bool = False


@dataclass(frozen=True)
class _PreparedCall:
    payload: dict
    full_text_ids: tuple[str, ...]
    withheld_ids: tuple[str, ...]
    input_tokens: int
    limit: str | None
    examined_ids: tuple[str, ...]
    discovered: tuple[dict, ...]
    representative_ids: tuple[str, ...]
    competing: bool
    omitted_ids: tuple[str, ...] = ()


def run_investigation(
    analysis_id,
    *,
    provider: BrainProvider,
    subject_pole: str,
    subject_start,
    subject_end,
    ceilings: dict | None = None,
    clock=None,
) -> InvestigationOutcome:
    """Run the readings that fit the budget. A transport failure does not finish the dossier."""
    analysis = (
        BrainAnalysis.objects.filter(id=analysis_id)
        .only(
            "id",
            "establishment_id",
            "configuration",
            "cancel_requested_at",
            "result",
        )
        .first()
    )
    if analysis is None:
        return _bare(TREATMENT_FAILED, "analysis_missing")
    resolved = _ceilings(ceilings, analysis)
    timing = investigation_timing(resolved)
    if not timing.coherent:
        return _bare(TREATMENT_FAILED, "timing_incoherent")
    if _canceled(analysis_id):
        return _bare(TREATMENT_CANCELED, "cancel_requested")
    try:
        snapshot = reload_period_dossier(analysis_id)
    except BrainWorkError as exc:
        return _bare(TREATMENT_FAILED, exc.code)
    dossier_id = (
        BrainDossier.objects.filter(analysis_id=analysis_id).values_list("id", flat=True).get()
    )
    state = _load(dossier_id)
    if state["stop"] is not None:
        return _outcome_from(state["stop"])
    tick = clock or _monotonic
    started = tick()
    while True:
        if _canceled(analysis_id):
            return _save_stop(
                dossier_id,
                _conclusion(
                    state,
                    snapshot=snapshot,
                    treatment=TREATMENT_CANCELED,
                    code="cancel_requested",
                    qualification=None,
                    succeeded=False,
                ),
            )
        if _pending_request(state):
            decision, opened = _deepen(
                snapshot,
                analysis,
                _parsed_output(state),
                state,
                subject_start=subject_start,
                subject_end=subject_end,
            )
            _store_decision(dossier_id, state, decision, _parsed_output(state), opened)
            if decision is None or not decision.accepted:
                return _save_stop(
                    dossier_id,
                    _accepted_conclusion(
                        state,
                        snapshot,
                        competing=bool(_last_withheld(state)),
                        code="" if decision is None else decision.code,
                        withheld=_last_withheld(state),
                    ),
                )
            snapshot = reload_period_dossier(analysis_id)
            continue
        if state["readings"] >= resolved["max_semantic_readings"] or not _needs_provider_call(
            state
        ):
            return _save_stop(
                dossier_id,
                _accepted_conclusion(
                    state,
                    snapshot,
                    competing=bool(_last_withheld(state)),
                    code=_stop_code(state, resolved["max_semantic_readings"]),
                    withheld=_last_withheld(state),
                ),
            )
        prepared = _prepare(
            snapshot,
            state,
            subject_pole=subject_pole,
            subject_start=subject_start,
            subject_end=subject_end,
            ceilings=resolved,
        )
        if prepared.payload is None:
            code = prepared.limit or "budget_exceeded"
            if state["readings"] == 0:
                return _save_stop(
                    dossier_id,
                    _refused(state, code, competing=prepared.competing),
                )
            previous = set(state["lectures"][-1]["examined_ids"])
            unread = tuple(
                source_id for source_id in prepared.examined_ids if source_id not in previous
            )
            return _save_stop(
                dossier_id,
                _accepted_conclusion(
                    state,
                    snapshot,
                    competing=prepared.competing or bool(unread),
                    code=code,
                    withheld=prepared.withheld_ids,
                    unread=unread,
                ),
            )
        if state["calls"] >= resolved["max_provider_calls"]:
            return _save_stop(dossier_id, _failed(state, "budget_exceeded"))
        if state["tokens"] + prepared.input_tokens > resolved["total_input_tokens"]:
            return _save_stop(dossier_id, _failed(state, "budget_exceeded"))
        if (
            tick() - started + resolved["provider_timeout_seconds"]
            > resolved["attempt_hard_seconds"]
        ):
            return _save_stop(dossier_id, _failed(state, "attempt_exceeded"))
        step = f"lecture:{state['readings'] + 1}"
        result = _invoke(
            provider,
            analysis_id=analysis_id,
            step=step,
            payload=prepared.payload,
            timeout_seconds=resolved["provider_timeout_seconds"],
        )
        if result is None:
            return _interrupted(state, step)
        state["calls"] += 1
        state["tokens"] += prepared.input_tokens
        if result.input_tokens is not None and (
            result.input_tokens > resolved["per_call_input_tokens"]
            or state["tokens"] - prepared.input_tokens + result.input_tokens
            > resolved["total_input_tokens"]
        ):
            return _save_stop(dossier_id, _failed(state, "budget_exceeded"))
        if not _output_within(result, resolved):
            return _save_stop(dossier_id, _failed(state, "provider_output_rejected"))
        assessment = _assess(result.output, snapshot, prepared)
        correction = None
        if not assessment.ok:
            corrected = _correct(
                provider,
                analysis_id=analysis_id,
                dossier_id=dossier_id,
                state=state,
                prepared=prepared,
                errors=assessment.errors,
                ceilings=resolved,
                snapshot=snapshot,
                tick=tick,
                started=started,
            )
            if isinstance(corrected, InvestigationOutcome):
                return corrected
            assessment_output, correction = corrected
        else:
            assessment_output = assessment.parsed
        _store_reading(dossier_id, state, prepared, assessment_output, correction=correction)


def _ceilings(overrides: dict | None, analysis: BrainAnalysis) -> dict:
    """V3 call budgets. Lease and attempt come from the frozen copy when present."""
    resolved = investigation_ceilings()
    configuration = analysis.configuration if isinstance(analysis.configuration, dict) else {}
    frozen = configuration.get("ceilings")
    if isinstance(frozen, dict):
        for key in (
            "lease_seconds",
            "provider_timeout_seconds",
            "attempt_soft_seconds",
            "attempt_hard_seconds",
        ):
            if key in frozen:
                resolved[key] = int(frozen[key])
    if overrides:
        resolved.update(overrides)
    return resolved


def _prepare(
    snapshot, state, *, subject_pole, subject_start, subject_end, ceilings
) -> _PreparedCall:
    provider = "fake"
    model = "fake"
    if not state["lectures"]:
        allowance = reading_allowance(
            instructions=investigation_prompt(),
            schema=investigation_response_schema(),
            per_call_input_tokens=ceilings["per_call_input_tokens"],
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
        if not reading.launched:
            return _PreparedCall(
                payload=None,
                full_text_ids=(),
                withheld_ids=(),
                input_tokens=reading.input_tokens,
                limit=reading.limit,
                examined_ids=(),
                discovered=tuple(item.as_record() for item in reading.discovered_not_examined),
                representative_ids=reading.representative_ids,
                competing=reading.competing_period_lead_excluded,
            )
        examined = reading.examined_ids
        discovered = tuple(item.as_record() for item in reading.discovered_not_examined)
        representatives = reading.representative_ids
        competing = False
    else:
        last = state["lectures"][-1]
        examined = _examined_after(last, state["decisions"])
        discovered = tuple(
            row for row in last["discovered_not_examined"] if row["source_id"] not in set(examined)
        )
        representatives = tuple(last["representative_ids"])
        competing = False
    protected = set(representatives)
    protected.update(_prior_evidence(state["lectures"]))
    protected.update(_opened_ids(state["decisions"]))
    if state["lectures"]:
        previous = set(state["lectures"][-1]["examined_ids"])
        protected.update(source_id for source_id in examined if source_id not in previous)
    contradictions = _contradictions(state["lectures"])
    protected.update(row["item_id"] for row in contradictions)
    return _fit_call(
        snapshot,
        examined_ids=tuple(examined),
        protected_ids=protected,
        contradictions=contradictions,
        discovered=discovered,
        representative_ids=representatives,
        competing=competing,
        reading_index=state["readings"] + 1,
        deepenings_remaining=MAX_DEEPENINGS - _accepted_count(state),
        per_call=ceilings["per_call_input_tokens"],
        limits=_limits(snapshot, state),
    )


def _fit_call(
    snapshot: PeriodSnapshot,
    *,
    examined_ids: tuple[str, ...],
    protected_ids: set[str],
    contradictions: list[dict],
    discovered: tuple[dict, ...],
    representative_ids: tuple[str, ...],
    competing: bool,
    reading_index: int,
    deepenings_remaining: int,
    per_call: int,
    limits: list[dict],
) -> _PreparedCall:
    """Send a copy only with its text. A text that does not fit is not examined."""
    by_id = {item.source_id: item for item in snapshot.copies}

    def pack(
        examined: tuple[str, ...],
        discovered_rows: tuple[dict, ...],
        withheld: tuple[str, ...],
    ) -> tuple[dict, int]:
        payload = _payload(
            snapshot,
            reading_index=reading_index,
            examined_ids=examined,
            full_ids=set(examined),
            withheld_ids=set(withheld),
            by_id=by_id,
            contradictions=contradictions,
            discovered=discovered_rows,
            deepenings_remaining=deepenings_remaining,
            limits=limits,
        )
        return payload, investigation_call_tokens(payload)

    payload, spent = pack(examined_ids, discovered, ())
    if spent <= per_call:
        return _ready(
            payload,
            set(examined_ids),
            (),
            spent,
            examined_ids,
            discovered,
            representative_ids,
            competing,
            (),
        )
    kept = tuple(source_id for source_id in examined_ids if source_id in protected_ids)
    dropped = tuple(source_id for source_id in examined_ids if source_id not in protected_ids)
    discovered_kept = _discover(discovered, dropped, by_id)
    payload, spent = pack(kept, discovered_kept, ())
    if spent <= per_call:
        return _ready(
            payload,
            set(kept),
            (),
            spent,
            kept,
            discovered_kept,
            representative_ids,
            competing,
            dropped,
        )
    withheld: list[str] = []
    kept_ids = set(kept)
    contradiction_ids = {row["item_id"] for row in contradictions}
    candidates = [
        source_id
        for source_id in kept
        if source_id in contradiction_ids and source_id not in representative_ids
    ]
    candidates.sort(key=lambda source_id: _copy_tokens(by_id[source_id]), reverse=True)
    for source_id in candidates:
        kept_ids.discard(source_id)
        withheld.append(source_id)
        current = tuple(item_id for item_id in kept if item_id in kept_ids)
        discovered_now = _discover(discovered_kept, tuple(withheld), by_id)
        payload, spent = pack(current, discovered_now, tuple(withheld))
        if spent <= per_call:
            return _ready(
                payload,
                set(current),
                tuple(withheld),
                spent,
                current,
                discovered_now,
                representative_ids,
                competing,
                dropped + tuple(withheld),
            )
    limit = LIMIT_PERIOD_EXCEEDS_CALL if reading_index == 1 else "budget_exceeded"
    return _PreparedCall(
        payload=None,
        full_text_ids=tuple(kept_ids),
        withheld_ids=tuple(withheld),
        input_tokens=spent,
        limit=limit,
        examined_ids=examined_ids,
        discovered=discovered,
        representative_ids=representative_ids,
        competing=competing or bool(withheld),
    )


def _discover(
    rows: tuple[dict, ...],
    source_ids: tuple[str, ...],
    by_id: dict[str, PeriodCopy],
) -> tuple[dict, ...]:
    known = {str(row.get("source_id") or "") for row in rows}
    merged = list(rows)
    for source_id in source_ids:
        if not source_id or source_id in known:
            continue
        item = by_id.get(source_id)
        merged.append(
            {
                "source_id": source_id,
                "pole": item.pole if item is not None else "",
                "category": item.category if item is not None else "",
                "disposition": DISCOVERED_NOT_EXAMINED,
            }
        )
        known.add(source_id)
    return tuple(merged)


def _ready(
    payload,
    full_ids,
    withheld,
    spent,
    examined,
    discovered,
    representatives,
    competing,
    omitted,
):
    return _PreparedCall(
        payload=payload,
        full_text_ids=tuple(full_ids),
        withheld_ids=withheld,
        input_tokens=spent,
        limit=None,
        examined_ids=examined,
        discovered=discovered,
        representative_ids=representatives,
        competing=competing,
        omitted_ids=tuple(omitted),
    )


def _payload(
    snapshot: PeriodSnapshot,
    *,
    reading_index: int,
    examined_ids: tuple[str, ...],
    full_ids: set[str],
    withheld_ids: set[str],
    by_id: dict[str, PeriodCopy],
    contradictions: list[dict],
    discovered: tuple[dict, ...],
    deepenings_remaining: int,
    limits: list[dict],
) -> dict:
    examined = []
    for source_id in examined_ids:
        if source_id in withheld_ids or source_id not in full_ids:
            continue
        examined.append(_full_text(by_id[source_id]))
    visible = []
    for row in contradictions:
        marked = {"subject_key": row["subject_key"], "item_id": row["item_id"]}
        if row["item_id"] in withheld_ids:
            marked["text_withheld"] = True
        visible.append(marked)
    return {
        "contract": SCHEMA_VERSION,
        "reading": reading_index,
        "proposed_subjects": _proposed(snapshot),
        "reporting": snapshot.reporting,
        "series": list(snapshot.series),
        "objectives": list(snapshot.objectives),
        "examined": examined,
        "contradictions": visible,
        "discovered_not_examined": list(discovered),
        "deepening_menu": sorted(DEEPENING_MENU),
        "deepenings_remaining": deepenings_remaining,
        "limits": limits,
        "memory": [
            dict(item.payload) for item in snapshot.copies if item.category == CATEGORY_MEMORY
        ],
    }


def _rejected_correction(errors, cost, rejected) -> dict:
    """Codes of both refusals. The rejected output itself is not stored."""
    return {
        "errors": list(errors),
        "rejected_errors": list(rejected),
        "input_tokens": cost,
        "accepted": False,
    }


def _correct(
    provider,
    *,
    analysis_id,
    dossier_id,
    state,
    prepared,
    errors,
    ceilings,
    snapshot,
    tick,
    started,
):
    if (
        state["corrections"] >= ceilings["max_corrections"]
        or state["calls"] >= ceilings["max_provider_calls"]
    ):
        return _save_stop(dossier_id, _failed(state, "response_invalid"))
    if tick() - started + ceilings["provider_timeout_seconds"] > ceilings["attempt_hard_seconds"]:
        return _save_stop(dossier_id, _failed(state, "attempt_exceeded"))
    payload = {
        **prepared.payload,
        "correction": {
            "errors": list(errors),
            "rules": list(correction_rules(errors)),
        },
    }
    cost = investigation_call_tokens(payload)
    if (
        cost > ceilings["per_call_input_tokens"]
        or state["tokens"] + cost > ceilings["total_input_tokens"]
    ):
        return _save_stop(dossier_id, _failed(state, "budget_exceeded"))
    step = _CORRECTION_CODE
    result = _invoke(
        provider,
        analysis_id=analysis_id,
        step=step,
        payload=payload,
        timeout_seconds=ceilings["provider_timeout_seconds"],
    )
    if result is None:
        return _interrupted(state, step)
    state["calls"] += 1
    state["tokens"] += cost
    if not _output_within(result, ceilings):
        state["corrections"] += 1
        return _save_stop(
            dossier_id,
            _failed(state, "provider_output_rejected"),
            correction=_rejected_correction(errors, cost, ("provider_output_rejected",)),
        )
    assessment = _assess(result.output, snapshot, prepared)
    if not assessment.ok:
        state["corrections"] += 1
        return _save_stop(
            dossier_id,
            _failed(state, "response_invalid"),
            correction=_rejected_correction(errors, cost, assessment.errors),
        )
    return assessment.parsed, {
        "errors": list(errors),
        "input_tokens": cost,
        "accepted": True,
    }


def _deepen(snapshot, analysis, parsed, state, *, subject_start, subject_end):
    request = parsed.deepening
    if request is None:
        return None, None
    target_at = _parse_target(request.target_at)
    requested_establishment = request.establishment_id or str(analysis.establishment_id)
    decision = accept_deepening(
        kind=request.kind,
        already_done=_accepted_count(state),
        establishment_id=str(analysis.establishment_id),
        request_establishment_id=requested_establishment,
        target_at=target_at,
        capture_at=snapshot.capture_at,
    )
    if not decision.accepted:
        return decision, None
    if request.kind == DEEPEN_PERIOD_INDEX:
        examined = set(_examined_ids(state))
        if not request.source_id or request.source_id in examined:
            code = "already_examined" if request.source_id else "outside_index"
            return DeepeningDecision(False, code), None
        try:
            opened = open_indexed_copy(snapshot, request.source_id)
        except PeriodSnapshotError:
            return DeepeningDecision(False, "outside_index"), None
        return DeepeningDecision(True, "accepted"), DeepeningOpen(
            True,
            "accepted",
            opened_source_ids=(opened.source_id,),
        )
    opened = open_deepening(
        analysis=analysis,
        snapshot=snapshot,
        kind=request.kind,
        subject_key=request.subject_key,
        activity_subject=request.activity_subject,
        reading_index=state["readings"],
        subject_start=subject_start,
        subject_end=subject_end,
    )
    if not opened.accepted:
        return DeepeningDecision(False, opened.code), None
    return DeepeningDecision(True, "accepted"), opened


def _assess(output, snapshot: PeriodSnapshot, prepared: _PreparedCall):
    signal_ids, action_ids, reporting_ids, measures = _source_classes(snapshot)
    citable = set(prepared.full_text_ids)
    citable.update(measures)
    citable.update(reporting_ids)
    proposed = {row["key"] for row in _proposed(snapshot)}
    memory_ids = {item.source_id for item in snapshot.copies if item.category == CATEGORY_MEMORY}
    return assess_reading(
        output,
        citable_ids=citable,
        signal_ids=signal_ids,
        action_ids=action_ids,
        proposed_keys=proposed,
        measures=measures,
        memory_ids=memory_ids,
        reporting_ids=reporting_ids,
    )


def _invoke(provider, *, analysis_id, step, payload, timeout_seconds):
    try:
        return provider.complete(
            analysis_id=str(analysis_id),
            lot_key=step,
            payload=payload,
            timeout_seconds=timeout_seconds,
        )
    except BrainProviderUnavailable:
        return None


def _output_within(result, ceilings) -> bool:
    if result.truncated or not isinstance(result.output, dict):
        return False
    counted = result.output_tokens
    if counted is None:
        counted = output_token_count(result.output)
    return counted <= ceilings["per_call_output_tokens"]


def _store_reading(dossier_id, state, prepared: _PreparedCall, parsed, correction=None) -> None:
    output = parsed.model_dump()
    record = {
        "input_hash": digest(prepared.payload),
        "input_tokens": prepared.input_tokens,
        "payload": prepared.payload,
        "output": output,
        "examined_ids": list(prepared.examined_ids),
        "full_text_ids": list(prepared.full_text_ids),
        "withheld_ids": list(prepared.withheld_ids),
        "omitted_ids": list(prepared.omitted_ids),
        "discovered_not_examined": list(prepared.discovered),
        "representative_ids": list(prepared.representative_ids),
    }
    index = state["readings"] + 1
    with transaction.atomic():
        _write_row(dossier_id, f"lecture:{index}", record, examined=len(prepared.examined_ids))
        if correction is not None:
            _write_row(
                dossier_id,
                _CORRECTION_CODE,
                {
                    **correction,
                    "reading_index": index,
                    "reading": record,
                },
                examined=1,
                retained=0,
            )
    state["lectures"].append(record)
    state["readings"] = index
    if correction is not None:
        state["corrections"] += 1


def _store_decision(dossier_id, state, decision, parsed, opened) -> None:
    if decision is None:
        return
    request = parsed.deepening
    record = {
        "kind": request.kind if request is not None else "",
        "source_id": request.source_id if request is not None else "",
        "subject_key": request.subject_key if request is not None else "",
        "code": decision.code,
        "accepted": decision.accepted,
        "after_reading": state["readings"],
        "opened_source_ids": [],
        "memory_ids": [],
        "exclusions": [],
        "limits": [],
    }
    if opened is not None:
        record["opened_source_ids"] = list(opened.opened_source_ids)
        record["memory_ids"] = list(opened.memory_ids)
        record["exclusions"] = list(opened.exclusions)
        record["limits"] = list(opened.limits)
        if opened.opened_source_ids:
            record["opened_source_id"] = opened.opened_source_ids[0]
    _write(
        dossier_id,
        f"decision:{state['readings']}",
        record,
        examined=1,
        retained=1 if decision.accepted else 0,
    )
    state["decisions"].append(record)


def _save_stop(dossier_id, outcome: InvestigationOutcome, correction=None) -> InvestigationOutcome:
    with transaction.atomic():
        if correction is not None:
            _write_row(
                dossier_id,
                _CORRECTION_CODE,
                correction,
                examined=1,
                retained=0,
            )
        _write_row(
            dossier_id,
            STOP_CODE,
            _stop_record(outcome),
            examined=outcome.semantic_readings,
        )
    return outcome


def _load(dossier_id) -> dict:
    rows = {
        row.code: row
        for row in BrainSearchRun.objects.filter(dossier_id=dossier_id).only("code", "criteria")
    }
    lectures = []
    index = 1
    while f"lecture:{index}" in rows:
        lectures.append(rows[f"lecture:{index}"].criteria)
        index += 1
    decisions = []
    index = 1
    while f"decision:{index}" in rows:
        decisions.append(rows[f"decision:{index}"].criteria)
        index += 1
    correction = rows.get(_CORRECTION_CODE)
    stop = rows.get(STOP_CODE)
    correction_body = correction.criteria if correction is not None else {}
    if not isinstance(correction_body, dict):
        correction_body = {}
    restored = _restore_reading(lectures, correction_body)
    if restored is not None:
        lectures.append(restored)
    paired = _correction_paired(lectures, correction_body)
    tokens = sum(int(row.get("input_tokens") or 0) for row in lectures)
    if paired:
        tokens += int(correction_body.get("input_tokens") or 0)
    return {
        "lectures": lectures,
        "decisions": decisions,
        "readings": len(lectures),
        "corrections": 1 if paired else 0,
        "calls": len(lectures) + (1 if paired else 0),
        "tokens": tokens,
        "stop": None if stop is None else stop.criteria,
    }


def _restore_reading(lectures: list[dict], correction: dict) -> dict | None:
    """A corrected reading stored without its lecture row is still the same step."""
    if not correction.get("accepted") or not isinstance(correction.get("reading"), dict):
        return None
    try:
        index = int(correction.get("reading_index") or 0)
    except (TypeError, ValueError):
        return None
    if index != len(lectures) + 1:
        return None
    return correction["reading"]


def _correction_paired(lectures: list[dict], correction: dict) -> bool:
    if not correction:
        return False
    if not correction.get("accepted"):
        return False
    try:
        index = int(correction.get("reading_index") or 0)
    except (TypeError, ValueError):
        return False
    return 0 < index <= len(lectures)


def _write(
    dossier_id, code: str, criteria: dict, *, examined: int, retained: int | None = None
) -> None:
    with transaction.atomic():
        _write_row(dossier_id, code, criteria, examined=examined, retained=retained)


def _write_row(
    dossier_id, code: str, criteria: dict, *, examined: int, retained: int | None = None
) -> None:
    BrainSearchRun.objects.update_or_create(
        dossier_id=dossier_id,
        code=code,
        defaults={
            "criteria": criteria,
            "examined_count": examined,
            "retained_count": examined if retained is None else retained,
        },
    )


def _accepted_conclusion(
    state,
    snapshot,
    *,
    competing,
    code,
    withheld,
    unread: tuple[str, ...] = (),
) -> InvestigationOutcome:
    last = state["lectures"][-1]
    withheld_ids = set(withheld)
    blocked_subjects = {
        row["subject_key"]
        for row in _contradictions(state["lectures"])
        if row["item_id"] in withheld_ids
    }
    discovered = _with_unread(last["discovered_not_examined"], unread, snapshot)
    facts = _facts(
        last["output"],
        snapshot,
        withheld=withheld,
        competing=competing,
        discovered=discovered,
        blocked_subjects=blocked_subjects,
        modified_subjects=_modified_subjects(state),
        unscoped_exclusion=_unscoped_exclusion(state),
        coverage_incomplete=_coverage_incomplete(state, unread),
    )
    verdict = qualify(facts)
    return InvestigationOutcome(
        treatment=TREATMENT_COMPLETED,
        code=code,
        qualification=verdict.qualification,
        investigation_succeeded=verdict.investigation_succeeded,
        semantic_readings=state["readings"],
        provider_calls=state["calls"],
        corrections=state["corrections"],
        examined_ids=tuple(last["examined_ids"]),
        discovered_not_examined=tuple(row["source_id"] for row in discovered),
        contradictions=tuple(_contradictions(state["lectures"])),
        full_text_ids=tuple(last["full_text_ids"]),
        withheld_contradiction_ids=tuple(withheld),
        limits=tuple(_limits(snapshot, state)),
    )


def _refused(state, code, *, competing) -> InvestigationOutcome:
    facts = InvestigationFacts(
        subjects=(),
        competing_period_lead_excluded=competing,
        treatment=TREATMENT_COMPLETED,
        checks_impossible=code == LIMIT_PERIOD_EXCEEDS_CALL,
    )
    verdict = qualify(facts)
    return InvestigationOutcome(
        treatment=TREATMENT_COMPLETED,
        code=code,
        qualification=verdict.qualification,
        investigation_succeeded=False,
        semantic_readings=state["readings"],
        provider_calls=state["calls"],
        corrections=state["corrections"],
        examined_ids=(),
        discovered_not_examined=(),
        contradictions=(),
        full_text_ids=(),
        withheld_contradiction_ids=(),
    )


def _failed(state, code) -> InvestigationOutcome:
    return _conclusion(
        state,
        treatment=TREATMENT_FAILED,
        code=code,
        qualification=None,
        succeeded=False,
    )


def _conclusion(
    state, *, treatment, code, qualification, succeeded, snapshot=None
) -> InvestigationOutcome:
    last = state["lectures"][-1] if state["lectures"] else None
    limits = tuple(_limits(snapshot, state)) if snapshot is not None else ()
    return InvestigationOutcome(
        treatment=treatment,
        code=code,
        qualification=qualification,
        investigation_succeeded=succeeded,
        semantic_readings=state["readings"],
        provider_calls=state["calls"],
        corrections=state["corrections"],
        examined_ids=tuple(last["examined_ids"]) if last else (),
        discovered_not_examined=tuple(
            row["source_id"] for row in (last or {}).get("discovered_not_examined") or []
        ),
        contradictions=tuple(_contradictions(state["lectures"])),
        full_text_ids=tuple(last["full_text_ids"]) if last else (),
        withheld_contradiction_ids=tuple(last["withheld_ids"]) if last else (),
        limits=limits,
    )


def _interrupted(state, step: str) -> InvestigationOutcome:
    outcome = _conclusion(
        state,
        treatment=_TREATMENT_INTERRUPTED,
        code="provider_unavailable",
        qualification=None,
        succeeded=False,
    )
    return InvestigationOutcome(
        treatment=outcome.treatment,
        code=outcome.code,
        qualification=None,
        investigation_succeeded=False,
        semantic_readings=outcome.semantic_readings,
        provider_calls=outcome.provider_calls,
        corrections=outcome.corrections,
        examined_ids=outcome.examined_ids,
        discovered_not_examined=outcome.discovered_not_examined,
        contradictions=outcome.contradictions,
        full_text_ids=outcome.full_text_ids,
        withheld_contradiction_ids=outcome.withheld_contradiction_ids,
        replay_step=step,
    )


def _facts(
    output,
    snapshot,
    *,
    withheld,
    competing,
    discovered,
    blocked_subjects: set[str] | None = None,
    modified_subjects: set[str] | None = None,
    unscoped_exclusion: bool = False,
    coverage_incomplete: bool = False,
) -> InvestigationFacts:
    withheld_ids = set(withheld)
    blocked_keys = blocked_subjects or set()
    modified = modified_subjects or set()
    proposed = {row["key"] for row in _proposed(snapshot)}
    signal_ids, action_ids, reporting_ids, measures = _source_classes(snapshot)
    measure_ids = set(measures)
    subjects = []
    usable_arithmetic = False
    for subject in output.get("subjects") or []:
        cause = _cause_verified(
            subject,
            signal_ids=signal_ids,
            action_ids=action_ids,
            measure_ids=measure_ids,
            reporting_ids=reporting_ids,
        )
        blocked = subject["key"] in blocked_keys or bool(
            withheld_ids.intersection(subject.get("contradiction_ids") or [])
        )
        if cause and (unscoped_exclusion or subject["key"] in modified or competing):
            blocked = True
        arithmetic = (
            subject_figures_verified(
                subject,
                measures=measures,
                signal_ids=signal_ids,
                action_ids=action_ids,
            )
            and not blocked
        )
        usable_arithmetic = usable_arithmetic or arithmetic
        subjects.append(
            SubjectFinding(
                key=subject["key"],
                significant=True,
                examined=bool(subject.get("examined")),
                cause_established=cause and not blocked,
                verified_analytical=arithmetic,
                affirmative=cause and not blocked,
                unexamined_contradiction=blocked,
                undermines_published=False,
                named=subject["key"] in proposed or bool(subject.get("examined")),
            )
        )
    rows = [row for row in output.get("subjects") or [] if isinstance(row, dict)]
    reported_only = bool(rows) and not usable_arithmetic
    reported_only = reported_only and not any(
        _cause_verified(
            row,
            signal_ids=signal_ids,
            action_ids=action_ids,
            measure_ids=measure_ids,
            reporting_ids=reporting_ids,
        )
        for row in rows
    )
    reported_only = reported_only and not any(
        subject.unexamined_contradiction for subject in subjects
    )
    return InvestigationFacts(
        subjects=tuple(subjects),
        discovered_not_examined=tuple(row["source_id"] for row in discovered),
        competing_period_lead_excluded=competing,
        reported_only=reported_only,
        accepted_decomposition=usable_arithmetic,
        treatment=TREATMENT_COMPLETED,
        coverage_incomplete=coverage_incomplete,
    )


def _stop_record(outcome: InvestigationOutcome) -> dict:
    return {
        "treatment": outcome.treatment,
        "code": outcome.code,
        "qualification": outcome.qualification,
        "investigation_succeeded": outcome.investigation_succeeded,
        "semantic_readings": outcome.semantic_readings,
        "provider_calls": outcome.provider_calls,
        "corrections": outcome.corrections,
        "examined_ids": list(outcome.examined_ids),
        "discovered_not_examined": list(outcome.discovered_not_examined),
        "contradictions": list(outcome.contradictions),
        "full_text_ids": list(outcome.full_text_ids),
        "withheld_contradiction_ids": list(outcome.withheld_contradiction_ids),
        "limits": list(outcome.limits),
        "published": False,
    }


def _outcome_from(record: dict) -> InvestigationOutcome:
    return InvestigationOutcome(
        treatment=str(record.get("treatment") or TREATMENT_FAILED),
        code=str(record.get("code") or ""),
        qualification=record.get("qualification"),
        investigation_succeeded=bool(record.get("investigation_succeeded")),
        semantic_readings=int(record.get("semantic_readings") or 0),
        provider_calls=int(record.get("provider_calls") or 0),
        corrections=int(record.get("corrections") or 0),
        examined_ids=tuple(record.get("examined_ids") or []),
        discovered_not_examined=tuple(record.get("discovered_not_examined") or []),
        contradictions=tuple(record.get("contradictions") or []),
        full_text_ids=tuple(record.get("full_text_ids") or []),
        withheld_contradiction_ids=tuple(record.get("withheld_contradiction_ids") or []),
        limits=tuple(record.get("limits") or []),
        published=False,
    )


def _last_withheld(state) -> tuple[str, ...]:
    if not state["lectures"]:
        return ()
    return tuple(state["lectures"][-1].get("withheld_ids") or [])


def _pending_request(state) -> bool:
    if not state["lectures"]:
        return False
    if not state["lectures"][-1].get("output", {}).get("deepening"):
        return False
    return not any(
        int(decision.get("after_reading") or 0) == state["readings"]
        for decision in state["decisions"]
    )


def _needs_provider_call(state) -> bool:
    if state["readings"] == 0:
        return True
    return any(
        decision.get("accepted") and int(decision.get("after_reading") or 0) == state["readings"]
        for decision in state["decisions"]
    )


def _stop_code(state, max_readings: int) -> str:
    for decision in reversed(state["decisions"]):
        if int(decision.get("after_reading") or 0) != state["readings"]:
            continue
        if not decision.get("accepted"):
            return str(decision.get("code") or "")
        return ""
    lectures = state["lectures"]
    if (
        state["readings"] >= max_readings
        and lectures
        and lectures[-1].get("output", {}).get("deepening")
    ):
        return "deepen_budget_exhausted"
    return ""


def _parsed_output(state) -> InvestigationReading:
    return InvestigationReading.model_validate(state["lectures"][-1]["output"])


def _examined_ids(state) -> tuple[str, ...]:
    if not state["lectures"]:
        return ()
    return _examined_after(state["lectures"][-1], state["decisions"])


def _modified_subjects(state) -> set[str]:
    found = set()
    for decision in state["decisions"]:
        if not _has_code(decision.get("exclusions"), "modified_after_capture"):
            continue
        key = str(decision.get("subject_key") or "")
        if key:
            found.add(key)
    return found


def _unscoped_exclusion(state) -> bool:
    for decision in state["decisions"]:
        if not _has_code(decision.get("exclusions"), "modified_after_capture"):
            continue
        if not str(decision.get("subject_key") or ""):
            return True
    return False


def _coverage_incomplete(state, unread: tuple[str, ...]) -> bool:
    if unread:
        return True
    if state["lectures"] and (state["lectures"][-1].get("omitted_ids") or []):
        return True
    for decision in state["decisions"]:
        rows = list(decision.get("exclusions") or []) + list(decision.get("limits") or [])
        if _has_code(rows, *_COVERAGE_CODES):
            return True
    return False


def _has_code(rows, *codes: str) -> bool:
    wanted = set(codes)
    return any(isinstance(row, dict) and row.get("code") in wanted for row in rows or [])


def _with_unread(discovered, unread: tuple[str, ...], snapshot: PeriodSnapshot) -> list[dict]:
    rows = [dict(row) for row in discovered if isinstance(row, dict)]
    known = {str(row.get("source_id") or "") for row in rows}
    by_id = {item.source_id: item for item in snapshot.copies}
    for source_id in unread:
        if not source_id or source_id in known:
            continue
        item = by_id.get(source_id)
        rows.append(
            {
                "source_id": source_id,
                "pole": item.pole if item is not None else "",
                "category": item.category if item is not None else "",
                "disposition": DISCOVERED_NOT_EXAMINED,
            }
        )
        known.add(source_id)
    return rows


def _examined_after(last: dict, decisions: list[dict]) -> tuple[str, ...]:
    """Examined copies plus an opening journaled after that reading and not yet re-read."""
    examined = list(last["examined_ids"])
    known = set(examined)
    reading_index = int(last.get("payload", {}).get("reading") or 0)
    for decision in decisions:
        if not decision.get("accepted"):
            continue
        if int(decision.get("after_reading") or 0) != reading_index:
            continue
        for source_id in _decision_source_ids(decision):
            if source_id and source_id not in known:
                examined.append(source_id)
                known.add(source_id)
    return tuple(examined)


def _prior_evidence(lectures: list[dict]) -> set[str]:
    found: set[str] = set()
    for reading in lectures:
        for subject in reading.get("output", {}).get("subjects") or []:
            found.update(cited_item_ids(subject))
    return found


def _source_classes(snapshot: PeriodSnapshot):
    """Classes the backend assigns. The model's wording does not choose them."""
    signal_ids = set()
    action_ids = set()
    for item in snapshot.copies:
        if item.category == CATEGORY_SIGNAL:
            signal_ids.add(item.source_id)
        elif item.category in {CATEGORY_EXECUTION, CATEGORY_PLAN}:
            action_ids.add(item.source_id)
    reporting_id = str(snapshot.reporting.get("source_id") or "")
    measures = {
        str(row.get("measure_id")): row
        for row in snapshot.reporting.get("measures") or []
        if isinstance(row, dict) and row.get("measure_id")
    }
    return signal_ids, action_ids, ({reporting_id} if reporting_id else set()), measures


def _cause_verified(
    subject: dict,
    *,
    signal_ids: set[str],
    action_ids: set[str],
    measure_ids: set[str],
    reporting_ids: set[str],
) -> bool:
    if subject.get("cause") != "established":
        return False
    evidence = [item for item in subject.get("evidence_ids") or [] if isinstance(item, str)]
    return (
        causal_evidence_issue(
            evidence,
            signal_ids=signal_ids,
            action_ids=action_ids,
            measure_ids=measure_ids,
            reporting_ids=reporting_ids,
        )
        is None
    )


def _contradictions(lectures: list[dict]) -> list[dict]:
    seen: set[tuple[str, str]] = set()
    rows = []
    for reading in lectures:
        for mark in reading.get("output", {}).get("contradictions") or []:
            key = (str(mark.get("subject_key") or ""), str(mark.get("item_id") or ""))
            if not key[0] or not key[1] or key in seen:
                continue
            seen.add(key)
            rows.append({"subject_key": key[0], "item_id": key[1]})
    return rows


def _opened_ids(decisions: list[dict]) -> set[str]:
    found = set()
    for decision in decisions:
        if not decision.get("accepted"):
            continue
        found.update(_decision_source_ids(decision))
    found.discard("")
    return found


def _decision_source_ids(decision: dict) -> tuple[str, ...]:
    identifiers = [str(item) for item in decision.get("opened_source_ids") or [] if item]
    legacy = str(decision.get("opened_source_id") or "")
    if legacy and legacy not in identifiers:
        identifiers.append(legacy)
    return tuple(identifiers)


def _accepted_count(state) -> int:
    return sum(1 for decision in state["decisions"] if decision.get("accepted"))


def _proposed(snapshot: PeriodSnapshot) -> list[dict]:
    rows = []
    for series in snapshot.series:
        key = str(series.get("series_key") or "")
        if not key:
            continue
        rows.append(
            {
                "key": key,
                "label": str(series.get("label") or ""),
                "unit": str(series.get("unit") or ""),
                "scope": str(series.get("scope") or ""),
            }
        )
    return rows


def _limits(snapshot: PeriodSnapshot, state) -> list[dict]:
    rows = [{"code": item.code, "source_id": item.source_id} for item in snapshot.omissions]
    for decision in state["decisions"]:
        if not decision.get("accepted"):
            rows.append(
                {"code": decision.get("code") or "", "source_id": decision.get("source_id") or ""}
            )
        for exclusion in decision.get("exclusions") or []:
            if isinstance(exclusion, dict):
                rows.append(
                    {
                        "code": exclusion.get("code") or "",
                        "source_id": exclusion.get("source_id") or "",
                    }
                )
        for limit in decision.get("limits") or []:
            if isinstance(limit, dict):
                rows.append(
                    {"code": limit.get("code") or "", "source_id": limit.get("source_id") or ""}
                )
    return rows


def _full_text(item: PeriodCopy) -> dict:
    payload = dict(item.payload)
    payload["pole"] = item.pole
    payload["role"] = item.role
    payload["start"] = item.start.isoformat() if item.start else None
    payload["end"] = item.end.isoformat() if item.end else None
    return payload


def _copy_tokens(item: PeriodCopy) -> int:
    return json_token_count(
        {
            "title": item.title,
            "structured_summary": str(item.payload.get("structured_summary") or ""),
        }
    )


def _parse_target(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _canceled(analysis_id) -> bool:
    return BrainAnalysis.objects.filter(
        id=analysis_id,
        cancel_requested_at__isnull=False,
    ).exists()


def _bare(treatment: str, code: str) -> InvestigationOutcome:
    return InvestigationOutcome(
        treatment=treatment,
        code=code,
        qualification=None,
        investigation_succeeded=False,
        semantic_readings=0,
        provider_calls=0,
        corrections=0,
        examined_ids=(),
        discovered_not_examined=(),
        contradictions=(),
        full_text_ids=(),
        withheld_contradiction_ids=(),
    )


def _monotonic() -> float:
    import time

    return time.monotonic()
