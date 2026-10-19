"""Bounded investigation loop. The current executor does not call it.

A reading sees frozen copies only. A deepening opens an identifier already
in the period index, or it is refused. Nothing here admits an analysis,
writes a published result, or calls a paid provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db import transaction

from houston.brain.configuration import digest, json_token_count
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
    assess_reading,
    grounded_blob,
    investigation_call_tokens,
    investigation_prompt,
    investigation_response_schema,
    output_token_count,
)
from houston.brain.models import BrainAnalysis, BrainDossier, BrainSearchRun
from houston.brain.period import (
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
_TREATMENT_INTERRUPTED = "interrupted"


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
                    treatment=TREATMENT_CANCELED,
                    code="cancel_requested",
                    qualification=None,
                    succeeded=False,
                ),
            )
        if state["readings"] >= resolved["max_semantic_readings"]:
            pending = state["lectures"][-1]["output"].get("deepening")
            return _save_stop(
                dossier_id,
                _accepted_conclusion(
                    state,
                    snapshot,
                    competing=False,
                    code="deepen_budget_exhausted" if pending else "",
                    withheld=(),
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
            return _save_stop(
                dossier_id,
                _accepted_conclusion(
                    state,
                    snapshot,
                    competing=prepared.competing,
                    code=code,
                    withheld=prepared.withheld_ids,
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
            assessment_output = corrected
        else:
            assessment_output = assessment.parsed
        _store_reading(dossier_id, state, prepared, assessment_output)
        decision, opened = _deepen(snapshot, analysis, assessment_output, state, prepared)
        _store_decision(dossier_id, state, decision, assessment_output, opened)
        if decision is None or not decision.accepted:
            return _save_stop(
                dossier_id,
                _accepted_conclusion(
                    state,
                    snapshot,
                    competing=prepared.competing,
                    code="" if decision is None else decision.code,
                    withheld=prepared.withheld_ids,
                ),
            )


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
    by_id = {item.source_id: item for item in snapshot.copies}

    def build(full_ids: set[str], withheld: tuple[str, ...]) -> dict:
        return _payload(
            snapshot,
            reading_index=reading_index,
            examined_ids=examined_ids,
            full_ids=full_ids,
            withheld_ids=set(withheld),
            by_id=by_id,
            contradictions=contradictions,
            discovered=discovered,
            deepenings_remaining=deepenings_remaining,
            limits=limits,
        )

    def cost(payload: dict) -> int:
        return investigation_call_tokens(payload)

    full_ids = set(examined_ids)
    payload = build(full_ids, ())
    spent = cost(payload)
    if spent <= per_call:
        return _ready(
            payload, full_ids, (), spent, examined_ids, discovered, representative_ids, competing
        )
    kept = set(protected_ids).intersection(examined_ids)
    payload = build(kept, ())
    spent = cost(payload)
    if spent <= per_call:
        return _ready(
            payload, kept, (), spent, examined_ids, discovered, representative_ids, competing
        )
    withheld: list[str] = []
    contradiction_ids = {row["item_id"] for row in contradictions}
    candidates = [
        source_id
        for source_id in kept
        if source_id in contradiction_ids and source_id not in representative_ids
    ]
    candidates.sort(key=lambda source_id: _copy_tokens(by_id[source_id]), reverse=True)
    for source_id in candidates:
        kept.discard(source_id)
        withheld.append(source_id)
        payload = build(kept, tuple(withheld))
        spent = cost(payload)
        if spent <= per_call:
            return _ready(
                payload,
                kept,
                tuple(withheld),
                spent,
                examined_ids,
                discovered,
                representative_ids,
                competing,
            )
    limit = LIMIT_PERIOD_EXCEEDS_CALL if reading_index == 1 else "budget_exceeded"
    return _PreparedCall(
        payload=None,
        full_text_ids=tuple(kept),
        withheld_ids=tuple(withheld),
        input_tokens=spent,
        limit=limit,
        examined_ids=examined_ids,
        discovered=discovered,
        representative_ids=representative_ids,
        competing=competing or bool(withheld),
    )


def _ready(payload, full_ids, withheld, spent, examined, discovered, representatives, competing):
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
        item = by_id[source_id]
        if source_id in withheld_ids:
            examined.append(_card(item, withheld=True))
        elif source_id in full_ids:
            examined.append(_full_text(item))
        else:
            examined.append(_card(item, withheld=False))
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
    payload = {**prepared.payload, "correction": {"errors": list(errors)}}
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
    state["corrections"] += 1
    _store_correction(dossier_id, errors, cost)
    if not _output_within(result, ceilings):
        return _save_stop(dossier_id, _failed(state, "provider_output_rejected"))
    assessment = _assess(result.output, snapshot, prepared)
    if not assessment.ok:
        return _save_stop(dossier_id, _failed(state, "response_invalid"))
    return assessment.parsed


def _deepen(snapshot, analysis, parsed, state, prepared):
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
    if request.kind != DEEPEN_PERIOD_INDEX:
        return DeepeningDecision(False, "not_in_frozen_dossier"), None
    if not request.source_id or request.source_id in prepared.examined_ids:
        code = "already_examined" if request.source_id else "outside_index"
        return DeepeningDecision(False, code), None
    try:
        opened = open_indexed_copy(snapshot, request.source_id)
    except PeriodSnapshotError:
        return DeepeningDecision(False, "outside_index"), None
    return DeepeningDecision(True, "accepted"), opened


def _assess(output, snapshot: PeriodSnapshot, prepared: _PreparedCall):
    full = [
        item.payload for item in snapshot.copies if item.source_id in set(prepared.full_text_ids)
    ]
    signal_ids = {
        item.source_id
        for item in snapshot.copies
        if item.source_id in set(prepared.full_text_ids) and item.category == "signal"
    }
    reporting_id = str(snapshot.reporting.get("source_id") or "")
    citable = set(prepared.full_text_ids)
    if reporting_id:
        citable.add(reporting_id)
    proposed = {row["key"] for row in _proposed(snapshot)}
    return assess_reading(
        output,
        citable_ids=citable,
        signal_ids=signal_ids,
        proposed_keys=proposed,
        grounded_text=grounded_blob(snapshot.reporting, full),
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


def _store_reading(dossier_id, state, prepared: _PreparedCall, parsed) -> None:
    output = parsed.model_dump()
    record = {
        "input_hash": digest(prepared.payload),
        "input_tokens": prepared.input_tokens,
        "payload": prepared.payload,
        "output": output,
        "examined_ids": list(prepared.examined_ids),
        "full_text_ids": list(prepared.full_text_ids),
        "withheld_ids": list(prepared.withheld_ids),
        "discovered_not_examined": list(prepared.discovered),
        "representative_ids": list(prepared.representative_ids),
    }
    index = state["readings"] + 1
    _write(dossier_id, f"lecture:{index}", record, examined=len(prepared.examined_ids))
    state["lectures"].append(record)
    state["readings"] = index


def _store_decision(dossier_id, state, decision, parsed, opened) -> None:
    if decision is None:
        return
    record = {
        "kind": parsed.deepening.kind if parsed.deepening is not None else "",
        "source_id": parsed.deepening.source_id if parsed.deepening is not None else "",
        "code": decision.code,
        "accepted": decision.accepted,
        "after_reading": state["readings"],
    }
    if opened is not None:
        record["opened_source_id"] = opened.source_id
    _write(
        dossier_id,
        f"decision:{state['readings']}",
        record,
        examined=1,
        retained=1 if decision.accepted else 0,
    )
    state["decisions"].append(record)


def _store_correction(dossier_id, errors, cost) -> None:
    _write(
        dossier_id,
        _CORRECTION_CODE,
        {"errors": list(errors), "input_tokens": cost},
        examined=1,
        retained=0,
    )


def _save_stop(dossier_id, outcome: InvestigationOutcome) -> InvestigationOutcome:
    _write(dossier_id, STOP_CODE, _stop_record(outcome), examined=outcome.semantic_readings)
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
    tokens = sum(int(row.get("input_tokens") or 0) for row in lectures)
    if correction is not None:
        tokens += int(correction.criteria.get("input_tokens") or 0)
    return {
        "lectures": lectures,
        "decisions": decisions,
        "readings": len(lectures),
        "corrections": 1 if correction is not None else 0,
        "calls": len(lectures) + (1 if correction is not None else 0),
        "tokens": tokens,
        "stop": None if stop is None else stop.criteria,
    }


def _write(
    dossier_id, code: str, criteria: dict, *, examined: int, retained: int | None = None
) -> None:
    with transaction.atomic():
        BrainSearchRun.objects.update_or_create(
            dossier_id=dossier_id,
            code=code,
            defaults={
                "criteria": criteria,
                "examined_count": examined,
                "retained_count": examined if retained is None else retained,
            },
        )


def _accepted_conclusion(state, snapshot, *, competing, code, withheld) -> InvestigationOutcome:
    last = state["lectures"][-1]
    withheld_ids = set(withheld)
    blocked_subjects = {
        row["subject_key"]
        for row in _contradictions(state["lectures"])
        if row["item_id"] in withheld_ids
    }
    facts = _facts(
        last["output"],
        snapshot,
        withheld=withheld,
        competing=competing,
        discovered=last["discovered_not_examined"],
        blocked_subjects=blocked_subjects,
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
        discovered_not_examined=tuple(row["source_id"] for row in last["discovered_not_examined"]),
        contradictions=tuple(_contradictions(state["lectures"])),
        full_text_ids=tuple(last["full_text_ids"]),
        withheld_contradiction_ids=tuple(withheld),
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


def _conclusion(state, *, treatment, code, qualification, succeeded) -> InvestigationOutcome:
    last = state["lectures"][-1] if state["lectures"] else None
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
) -> InvestigationFacts:
    withheld_ids = set(withheld)
    blocked_keys = blocked_subjects or set()
    proposed = {row["key"] for row in _proposed(snapshot)}
    subjects = []
    for subject in output.get("subjects") or []:
        blocked = subject["key"] in blocked_keys or bool(
            withheld_ids.intersection(subject.get("contradiction_ids") or [])
        )
        subjects.append(
            SubjectFinding(
                key=subject["key"],
                significant=True,
                examined=bool(subject.get("examined")),
                cause_established=subject.get("cause") == "established",
                verified_analytical=False,
                affirmative=subject.get("cause") == "established",
                unexamined_contradiction=blocked,
                undermines_published=blocked,
                named=subject["key"] in proposed or bool(subject.get("examined")),
            )
        )
    blocked = any(subject.undermines_published for subject in subjects)
    reported_only = (
        bool(subjects)
        and not blocked
        and all(
            subject.get("cause") != "established" and subject.get("calculation") is None
            for subject in output.get("subjects") or []
        )
    )
    return InvestigationFacts(
        subjects=tuple(subjects),
        discovered_not_examined=tuple(row["source_id"] for row in discovered),
        competing_period_lead_excluded=competing,
        reported_only=reported_only,
        accepted_decomposition=False,
        treatment=TREATMENT_COMPLETED,
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
        published=False,
    )


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
        source_id = str(decision.get("opened_source_id") or "")
        if source_id and source_id not in known:
            examined.append(source_id)
            known.add(source_id)
    return tuple(examined)


def _prior_evidence(lectures: list[dict]) -> set[str]:
    found: set[str] = set()
    for reading in lectures:
        for subject in reading.get("output", {}).get("subjects") or []:
            found.update(subject.get("evidence_ids") or [])
            found.update(subject.get("contradiction_ids") or [])
    return found


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
    return {
        str(decision.get("opened_source_id") or "")
        for decision in decisions
        if decision.get("accepted") and decision.get("opened_source_id")
    }


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
    return rows


def _full_text(item: PeriodCopy) -> dict:
    payload = dict(item.payload)
    payload["pole"] = item.pole
    payload["start"] = item.start.isoformat() if item.start else None
    payload["end"] = item.end.isoformat() if item.end else None
    return payload


def _card(item: PeriodCopy, *, withheld: bool) -> dict:
    return {
        "source_id": item.source_id,
        "pole": item.pole,
        "title": item.title,
        "start": item.start.isoformat() if item.start else None,
        "end": item.end.isoformat() if item.end else None,
        "reduced": True,
        "text_withheld": withheld,
    }


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
