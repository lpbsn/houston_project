"""Lot 10 — evaluate S15 acceptance corpus against V6 runtime with independent fake fixtures."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from houston.ai.observation_pipeline import (
    ObservationPipelineSkippedError,
    call_observation_pipeline,
    evaluate_observation_pipeline_precondition,
)
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import Establishment
from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
)
from houston.signals.models import CandidateSignal, Signal
from houston.signals.pipeline_corpus_eval import assert_openai_eval_opt_in
from houston.signals.pipeline_v6_smoke_archive import write_eval_archive
from houston.signals.services import apply_pipeline_output
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership
from houston.testing.pipeline_v6_acceptance import (
    get_pipeline_v6_acceptance_case,
    list_pipeline_v6_acceptance_case_ids,
    load_pipeline_v6_acceptance_corpus,
)
from houston.testing.pipeline_v6_metrics import (
    LOT_ACCEPTANCE,
    METRIC_IDS,
    METRIC_SPECS,
)
from houston.testing.taxonomy import create_activity_subject, create_business_unit

FIXTURES_PATH = (
    Path(__file__).resolve().parents[1] / "testing" / "pipeline_v6_fake_provider_fixtures.json"
)

# Deterministic metrics computable from fake apply/precondition runs.
DETERMINISTIC_METRICS = frozenset({"A", "D", "E", "F", "G", "H", "J"})
# LLM-understanding metrics: scored in fake CI when fixture drives apply outcome;
# live-only quality is marked separately for OpenAI business smoke.
LLM_LIVE_METRICS = frozenset({"B", "C"})


@dataclass
class V6CaseEvalResult:
    case_id: str
    title: str
    passed: bool
    diffs: tuple[str, ...] = ()
    metrics: tuple[str, ...] = ()
    mode: str = ""
    actual: dict[str, Any] = field(default_factory=dict)


@dataclass
class V6CorpusEvalReport:
    provider: str
    case_results: tuple[V6CaseEvalResult, ...] = ()
    errors: tuple[str, ...] = ()
    metrics_summary: dict[str, Any] = field(default_factory=dict)
    archive_path: str | None = None


@lru_cache(maxsize=1)
def load_pipeline_v6_fake_provider_fixtures() -> dict[str, Any]:
    with FIXTURES_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_fake_provider_fixture(case_id: str) -> dict[str, Any]:
    fixtures = load_pipeline_v6_fake_provider_fixtures()["fixtures"]
    if case_id not in fixtures:
        raise KeyError(f"No fake provider fixture for case {case_id}")
    return fixtures[case_id]


def list_v6_eval_case_ids(*, lot: str | None = "lot10") -> list[str]:
    if lot is None:
        return list_pipeline_v6_acceptance_case_ids()
    if lot == "lot10":
        return list(LOT_ACCEPTANCE["lot10"]["case_ids"])
    return [
        case["id"]
        for case in load_pipeline_v6_acceptance_corpus()["cases"]
        if lot in case.get("lots", [])
    ]


def _assert_fixture_independent_of_expected_v6(case_id: str, fixture: dict[str, Any]) -> None:
    """Guard against tautological fixtures copied from expected_v6."""
    case = get_pipeline_v6_acceptance_case(case_id)
    expected = case["expected_v6"]
    if fixture.get("mode") == "precondition_only":
        return
    fixture_candidates = fixture.get("candidates", [])
    expected_candidates = expected.get("candidates", [])
    if not fixture_candidates and not expected_candidates:
        return
    # Backend-only fields must never appear in fake LLM fixtures.
    for raw in fixture_candidates:
        for forbidden in ("routing_status", "resolution_audit", "rejection_code"):
            if forbidden in raw:
                raise ValueError(
                    f"{case_id}: fake fixture candidate must not include {forbidden!r}"
                )
    # Structural identity with expected_v6 candidates is forbidden.
    if fixture_candidates == expected_candidates:
        raise ValueError(
            f"{case_id}: fake fixture candidates must not be identical to expected_v6.candidates"
        )


def _setup_taxonomy_from_case_context(
    *,
    establishment: Establishment,
    context: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    business_units: dict[str, Any] = {}
    for bu_spec in context.get("active_business_units", []):
        business_units[bu_spec["key"]] = create_business_unit(
            establishment=establishment,
            key=bu_spec["key"],
            label=bu_spec.get("label", bu_spec["key"]),
        )
    activity_subjects: dict[str, Any] = {}
    for tax in context.get("routing_taxonomy", []):
        bu_key = tax["business_unit_key"]
        if bu_key not in business_units:
            business_units[bu_key] = create_business_unit(
                establishment=establishment,
                key=bu_key,
                label=bu_key,
            )
        for subject_spec in tax.get("activity_subjects", []):
            subject = create_activity_subject(
                establishment=establishment,
                business_unit=business_units[bu_key],
                label=subject_spec["label"],
            )
            activity_subjects[subject_spec["key"]] = subject
    return business_units, activity_subjects


def remap_v6_fixture_candidates_to_routing_keys(
    *,
    candidates: list[dict[str, Any]],
    business_units: dict[str, Any],
    activity_subjects: dict[str, Any],
) -> list[dict[str, Any]]:
    """Map logical fixture keys to runtime routing keys; nulls stay null."""
    remapped: list[dict[str, Any]] = []
    for raw in candidates:
        affected_logical = raw.get(
            "affected_business_unit_key",
            raw.get("affected_business_unit_routing_key"),
        )
        responsible_logical = raw.get(
            "responsible_business_unit_key",
            raw.get("responsible_business_unit_routing_key"),
        )
        subject_logical = raw.get(
            "activity_subject_key",
            raw.get("activity_subject_routing_key"),
        )
        cleaned = {
            key: value
            for key, value in raw.items()
            if key
            not in {
                "affected_business_unit_key",
                "responsible_business_unit_key",
                "activity_subject_key",
                "affected_business_unit_routing_key",
                "responsible_business_unit_routing_key",
                "activity_subject_routing_key",
            }
        }
        cleaned["affected_business_unit_routing_key"] = (
            None if affected_logical is None else business_units[affected_logical].routing_key
        )
        cleaned["responsible_business_unit_routing_key"] = (
            None
            if responsible_logical is None
            else business_units[responsible_logical].routing_key
        )
        cleaned["activity_subject_routing_key"] = (
            None if subject_logical is None else activity_subjects[subject_logical].routing_key
        )
        remapped.append(cleaned)
    return remapped


def _logical_key_for_business_unit(
    business_unit_id: uuid.UUID | None,
    business_units: dict[str, Any],
) -> str | None:
    if business_unit_id is None:
        return None
    for key, bu in business_units.items():
        if bu.id == business_unit_id:
            return key
    return None


def _logical_key_for_subject(
    subject_id: uuid.UUID | None,
    activity_subjects: dict[str, Any],
) -> str | None:
    if subject_id is None:
        return None
    for key, subject in activity_subjects.items():
        if subject.id == subject_id:
            return key
    return None


def _compare_apply_to_expected_v6(
    *,
    case: dict[str, Any],
    result: Any,
    signals: list[Signal],
    candidates: list[CandidateSignal],
    business_units: dict[str, Any],
    activity_subjects: dict[str, Any],
) -> list[str]:
    expected = case["expected_v6"]
    diffs: list[str] = []

    if expected.get("pipeline_started") is not True:
        diffs.append("expected pipeline_started=true for apply case")

    expected_outcome = expected.get("outcome")
    actual_outcome = result.outcome.value if result.outcome is not None else None
    if expected_outcome != actual_outcome:
        diffs.append(f"outcome: expected {expected_outcome!r}, got {actual_outcome!r}")

    expected_routing = expected.get("routing_status")
    if expected_routing is None:
        if signals:
            diffs.append(
                f"routing_status: expected no signals, got "
                f"{[s.routing_status for s in signals]!r}"
            )
    else:
        if not signals:
            diffs.append(f"routing_status: expected {expected_routing!r}, got no signals")
        else:
            for signal in signals:
                if signal.routing_status != expected_routing:
                    diffs.append(
                        f"routing_status: expected {expected_routing!r}, "
                        f"got {signal.routing_status!r} on signal {signal.id}"
                    )
                if (
                    signal.activity_subject_id is not None
                    and signal.responsible_business_unit_id is not None
                    and signal.activity_subject.business_unit_id
                    != signal.responsible_business_unit_id
                ):
                    diffs.append(
                        f"signal {signal.id}: subject→responsible invariant violated"
                    )

    expected_candidates = expected.get("candidates") or []
    if len(expected_candidates) != len(candidates):
        diffs.append(
            f"candidate_count: expected {len(expected_candidates)}, got {len(candidates)}"
        )

    if expected_candidates:
        expected_signatures = [
            (
                expected_cand.get("signal_kind"),
                expected_cand.get("expected_action"),
                expected_cand.get("affected_key"),
                expected_cand.get("responsible_key"),
                expected_cand.get("subject_key"),
            )
            for expected_cand in expected_candidates
        ]
        actual_signatures: list[tuple[Any, ...]] = []
        for cand in candidates:
            signal = cand.result_signal
            if signal is None:
                continue
            action = (
                signal.expected_action
                if signal.expected_action is not None
                else cand.expected_action
            )
            actual_signatures.append(
                (
                    cand.signal_kind,
                    action,
                    _logical_key_for_business_unit(
                        signal.affected_business_unit_id,
                        business_units,
                    ),
                    _logical_key_for_business_unit(
                        signal.responsible_business_unit_id,
                        business_units,
                    ),
                    _logical_key_for_subject(signal.activity_subject_id, activity_subjects),
                )
            )
        if Counter(expected_signatures) != Counter(actual_signatures):
            diffs.append(
                f"candidate_signatures: expected {sorted(expected_signatures)!r}, "
                f"got {sorted(actual_signatures)!r}"
            )

        first = expected_candidates[0]
        if "active_business_units_includes" in first:
            for key in first["active_business_units_includes"]:
                if key not in business_units:
                    diffs.append(f"active_business_units missing {key!r}")

    return diffs


def evaluate_v6_case_fake(case_id: str) -> V6CaseEvalResult:
    case = get_pipeline_v6_acceptance_case(case_id)
    fixture = get_fake_provider_fixture(case_id)
    _assert_fixture_independent_of_expected_v6(case_id, fixture)
    expected = case["expected_v6"]
    metrics = tuple(str(m).upper() for m in case.get("metrics", []))

    if fixture.get("mode") == "precondition_only":
        diffs: list[str] = []
        actual: dict[str, Any] = {"pipeline_started": False}
        membership = build_membership()
        if case_id == "S15-01":
            missing_id = uuid.uuid4()
            try:
                evaluate_observation_pipeline_precondition(establishment_id=missing_id)
                diffs.append("expected ObservationPipelineSkippedError for missing establishment")
            except ObservationPipelineSkippedError as exc:
                actual["error_code"] = exc.error_code
                if exc.error_code != expected.get("error_code"):
                    diffs.append(
                        f"error_code: expected {expected.get('error_code')!r}, "
                        f"got {exc.error_code!r}"
                    )
            # Also deactivated establishment path from existing Lot2 coverage.
            create_business_unit(
                establishment=membership.establishment,
                key="hotel",
                label="Hôtel",
            )
            establishment = membership.establishment
            establishment.status = Establishment.Status.DEACTIVATED
            establishment.save(update_fields=["status", "updated_at"])
            observation = create_observation(
                membership=membership,
                text=case["observation_text"],
            )
            try:
                call_observation_pipeline(observation=observation)
                diffs.append("expected skip for deactivated establishment")
            except ObservationPipelineSkippedError as exc:
                if exc.error_code != expected.get("error_code"):
                    diffs.append(
                        f"deactivated error_code: expected {expected.get('error_code')!r}, "
                        f"got {exc.error_code!r}"
                    )
        elif case_id == "S15-02":
            observation = create_observation(
                membership=membership,
                text=case["observation_text"],
            )
            try:
                call_observation_pipeline(observation=observation)
                diffs.append("expected ObservationPipelineSkippedError for no active BU")
            except ObservationPipelineSkippedError as exc:
                actual["error_code"] = exc.error_code
                if exc.error_code != expected.get("error_code"):
                    diffs.append(
                        f"error_code: expected {expected.get('error_code')!r}, "
                        f"got {exc.error_code!r}"
                    )
        else:
            diffs.append(f"unsupported precondition_only case {case_id}")

        if expected.get("pipeline_started") is not False:
            diffs.append("expected pipeline_started=false")
        return V6CaseEvalResult(
            case_id=case_id,
            title=case["title"],
            passed=not diffs,
            diffs=tuple(diffs),
            metrics=metrics,
            mode="precondition_only",
            actual=actual,
        )

    # Apply path with independent fake LLM payload.
    membership = build_membership()
    establishment = membership.establishment
    business_units, activity_subjects = _setup_taxonomy_from_case_context(
        establishment=establishment,
        context=case["context"],
    )
    observation = create_observation(
        membership=membership,
        text=case["observation_text"],
    )
    remapped = remap_v6_fixture_candidates_to_routing_keys(
        candidates=list(fixture.get("candidates") or []),
        business_units=business_units,
        activity_subjects=activity_subjects,
    )
    output = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[PipelineCandidateOutput(**raw) for raw in remapped],
    )
    result = apply_pipeline_output(observation=observation, output=output)
    signals = list(Signal.objects.filter(establishment=establishment).order_by("created_at"))
    candidates = list(
        CandidateSignal.objects.filter(observation=observation).order_by("created_at")
    )
    diffs = _compare_apply_to_expected_v6(
        case=case,
        result=result,
        signals=signals,
        candidates=candidates,
        business_units=business_units,
        activity_subjects=activity_subjects,
    )
    actual = {
        "pipeline_started": True,
        "outcome": result.outcome.value if result.outcome else None,
        "signal_count": len(signals),
        "routing_statuses": [s.routing_status for s in signals],
    }
    return V6CaseEvalResult(
        case_id=case_id,
        title=case["title"],
        passed=not diffs,
        diffs=tuple(diffs),
        metrics=metrics,
        mode="apply",
        actual=actual,
    )


def _build_metrics_summary(case_results: tuple[V6CaseEvalResult, ...]) -> dict[str, Any]:
    by_metric: dict[str, dict[str, Any]] = {}
    for metric_id in METRIC_IDS:
        related = [r for r in case_results if metric_id in r.metrics]
        if not related:
            by_metric[metric_id] = {
                "name": METRIC_SPECS[metric_id]["name"],
                "layer": METRIC_SPECS[metric_id]["layer"],
                "status": "unscored",
                "note": "no lot10 eval cases tagged",
                "case_ids": [],
                "passed": 0,
                "failed": 0,
            }
            continue
        passed = sum(1 for r in related if r.passed)
        failed = len(related) - passed
        if metric_id in LLM_LIVE_METRICS:
            status = "pass" if failed == 0 else "fail"
            note = (
                "fake fixture drives apply; live LLM quality signed via business smoke"
            )
        elif metric_id in DETERMINISTIC_METRICS:
            status = "pass" if failed == 0 else "fail"
            note = "deterministic fake eval"
        else:
            status = "pass" if failed == 0 else "fail"
            note = ""
        by_metric[metric_id] = {
            "name": METRIC_SPECS[metric_id]["name"],
            "layer": METRIC_SPECS[metric_id]["layer"],
            "status": status,
            "note": note,
            "case_ids": [r.case_id for r in related],
            "passed": passed,
            "failed": failed,
        }
    return by_metric


def evaluate_v6_corpus_cases(
    *,
    case_ids: list[str] | None = None,
    provider_name: str = "fake",
    archive: bool = True,
) -> V6CorpusEvalReport:
    selected = case_ids or list_v6_eval_case_ids(lot="lot10")
    normalized = provider_name.strip().lower()
    if normalized == "openai":
        assert_openai_eval_opt_in()
        raise NotImplementedError(
            "OpenAI S15 expected_v6 structural eval is not a CI gate; "
            "use the Lot 10 business smoke harness for live provider quality."
        )
    if normalized != "fake":
        raise ValueError(f"Unknown provider: {provider_name!r}. Use 'fake'.")

    errors: list[str] = []
    results: list[V6CaseEvalResult] = []
    for case_id in selected:
        try:
            results.append(evaluate_v6_case_fake(case_id))
        except Exception as exc:  # noqa: BLE001 — collect per-case errors for report
            errors.append(f"{case_id}: {exc}")

    case_results = tuple(results)
    metrics_summary = _build_metrics_summary(case_results)
    report = V6CorpusEvalReport(
        provider=normalized,
        case_results=case_results,
        errors=tuple(errors),
        metrics_summary=metrics_summary,
    )
    if archive:
        path = write_eval_archive(report=v6_corpus_eval_report_to_dict(report))
        report.archive_path = str(path)
    return report


def v6_corpus_eval_report_to_dict(report: V6CorpusEvalReport) -> dict[str, Any]:
    return {
        "provider": report.provider,
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "prompt_version": AI_OBSERVATION_PIPELINE_PROMPT_VERSION,
        "errors": list(report.errors),
        "metrics_summary": report.metrics_summary,
        "all_passed": all(r.passed for r in report.case_results) and not report.errors,
        "case_results": [
            {
                "case_id": r.case_id,
                "title": r.title,
                "passed": r.passed,
                "diffs": list(r.diffs),
                "metrics": list(r.metrics),
                "mode": r.mode,
                "actual": r.actual,
            }
            for r in report.case_results
        ],
    }


def format_v6_corpus_eval_report(report: V6CorpusEvalReport) -> str:
    lines = [
        f"Pipeline V6 corpus eval (provider={report.provider})",
        f"schema={AI_OBSERVATION_PIPELINE_SCHEMA_VERSION} "
        f"prompt={AI_OBSERVATION_PIPELINE_PROMPT_VERSION}",
        "",
    ]
    for result in report.case_results:
        mark = "PASS" if result.passed else "FAIL"
        lines.append(f"[{mark}] {result.case_id} — {result.title}")
        for diff in result.diffs:
            lines.append(f"  - {diff}")
    if report.errors:
        lines.append("")
        lines.append("Errors:")
        for err in report.errors:
            lines.append(f"  - {err}")
    lines.append("")
    lines.append("Metrics A–J:")
    for metric_id in METRIC_IDS:
        summary = report.metrics_summary.get(metric_id, {})
        lines.append(
            f"  {metric_id} {summary.get('name')}: {summary.get('status')} "
            f"(pass={summary.get('passed', 0)} fail={summary.get('failed', 0)}) "
            f"{summary.get('note', '')}"
        )
    if report.archive_path:
        lines.append("")
        lines.append(f"Archive: {report.archive_path}")
    return "\n".join(lines) + "\n"
