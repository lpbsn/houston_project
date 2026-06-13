from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from houston.ai.observation_pipeline import (
    FakeObservationPipelineProvider,
    ObservationPipelineProvider,
    OpenAIObservationPipelineProvider,
    call_observation_pipeline,
)
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.services import normalize_issue_focus
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership
from houston.testing.pipeline_golden_v4 import (
    get_pipeline_golden_v4_case,
    list_pipeline_golden_v4_case_ids,
    setup_active_signals_from_fixture,
    setup_taxonomy_from_fixture,
)

OPENAI_OPT_IN_ENV = "HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST"


@dataclass(frozen=True)
class CaseEvalResult:
    case_id: str
    description: str
    passed: bool
    diffs: tuple[str, ...] = ()
    expected_signatures: tuple[tuple[Any, ...], ...] = ()
    actual_signatures: tuple[tuple[Any, ...], ...] = ()
    actual_candidates: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class CorpusEvalReport:
    provider: str
    case_results: tuple[CaseEvalResult, ...] = ()
    errors: tuple[str, ...] = ()


def openai_eval_opt_in_enabled() -> bool:
    return os.environ.get(OPENAI_OPT_IN_ENV) == "1"


def assert_openai_eval_opt_in() -> None:
    if not openai_eval_opt_in_enabled():
        raise RuntimeError(
            f"Live OpenAI eval is opt-in only. Set {OPENAI_OPT_IN_ENV}=1 "
            "before running evaluate_observation_pipeline with --provider openai."
        )
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured.")


def resolve_eval_provider(provider_name: str) -> ObservationPipelineProvider:
    normalized = provider_name.strip().lower()
    if normalized == "fake":
        return FakeObservationPipelineProvider()
    if normalized == "openai":
        assert_openai_eval_opt_in()
        return OpenAIObservationPipelineProvider()
    raise ValueError(f"Unknown provider: {provider_name!r}. Use 'openai' or 'fake'.")


def candidate_signature(raw: dict[str, Any]) -> tuple[str, str, str, str, str | None]:
    return (
        raw["affected_business_unit_key"],
        raw["responsible_business_unit_key"],
        raw["activity_subject_key"],
        normalize_issue_focus(raw.get("issue_focus", "")),
        raw.get("operational_unit_key"),
    )


def _candidate_to_snapshot(candidate: PipelineCandidateOutput) -> dict[str, Any]:
    payload = candidate.model_dump()
    payload["issue_focus_normalized"] = normalize_issue_focus(candidate.issue_focus)
    return payload


def compare_pipeline_output_to_expected(
    *,
    case_id: str,
    description: str,
    expected_candidates: list[dict[str, Any]],
    output: ObservationPipelineOutput,
) -> CaseEvalResult:
    expected_signatures = tuple(
        candidate_signature(raw) for raw in expected_candidates
    )
    actual_snapshots = tuple(_candidate_to_snapshot(c) for c in output.candidates)
    actual_signatures = tuple(
        candidate_signature(snapshot) for snapshot in actual_snapshots
    )

    diffs: list[str] = []
    if output.schema_version != AI_OBSERVATION_PIPELINE_SCHEMA_VERSION:
        diffs.append(
            "schema_version: "
            f"expected {AI_OBSERVATION_PIPELINE_SCHEMA_VERSION!r}, "
            f"got {output.schema_version!r}"
        )

    expected_counter = Counter(expected_signatures)
    actual_counter = Counter(actual_signatures)
    if expected_counter != actual_counter:
        missing = expected_counter - actual_counter
        extra = actual_counter - expected_counter
        if missing:
            for signature, count in sorted(missing.items()):
                diffs.append(f"missing candidate signature (x{count}): {signature}")
        if extra:
            for signature, count in sorted(extra.items()):
                diffs.append(f"extra candidate signature (x{count}): {signature}")

    for candidate in output.candidates:
        if not candidate.issue_focus.strip():
            diffs.append("actual candidate has empty issue_focus")
            break

    return CaseEvalResult(
        case_id=case_id,
        description=description,
        passed=not diffs,
        diffs=tuple(diffs),
        expected_signatures=expected_signatures,
        actual_signatures=actual_signatures,
        actual_candidates=actual_snapshots,
    )


def _fake_provider_for_case(case: dict[str, Any]) -> FakeObservationPipelineProvider:
    candidates = [
        PipelineCandidateOutput(**raw) for raw in case["expected_candidates"]
    ]
    payload = ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=candidates,
    ).model_dump(mode="json")
    return FakeObservationPipelineProvider(payload=payload)


def run_corpus_case_eval(
    *,
    case_id: str,
    provider: ObservationPipelineProvider,
) -> CaseEvalResult:
    case = get_pipeline_golden_v4_case(case_id)
    membership = build_membership()
    establishment = membership.establishment
    business_units, activity_subjects = setup_taxonomy_from_fixture(
        establishment=establishment,
        fixture=case["taxonomy_fixture"],
    )
    setup_active_signals_from_fixture(
        establishment=establishment,
        setup=case.get("active_signals_setup", []),
        business_units=business_units,
        activity_subjects=activity_subjects,
    )
    observation = create_observation(
        membership=membership,
        text=case["observation_text"],
    )
    output = call_observation_pipeline(
        observation=observation,
        provider=provider,
    )
    return compare_pipeline_output_to_expected(
        case_id=case_id,
        description=case["description"],
        expected_candidates=case["expected_candidates"],
        output=output,
    )


def evaluate_corpus_cases(
    *,
    case_ids: list[str] | None = None,
    provider_name: str = "openai",
) -> CorpusEvalReport:
    selected_case_ids = case_ids or list_pipeline_golden_v4_case_ids()
    normalized_provider = provider_name.strip().lower()
    if normalized_provider == "openai":
        assert_openai_eval_opt_in()
        provider: ObservationPipelineProvider = OpenAIObservationPipelineProvider()
    elif normalized_provider == "fake":
        provider = FakeObservationPipelineProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name!r}. Use 'openai' or 'fake'.")

    errors: list[str] = []
    results: list[CaseEvalResult] = []

    for case_id in selected_case_ids:
        try:
            case_provider = provider
            if normalized_provider == "fake":
                case = get_pipeline_golden_v4_case(case_id)
                case_provider = _fake_provider_for_case(case)
            results.append(
                run_corpus_case_eval(case_id=case_id, provider=case_provider)
            )
        except Exception as exc:
            errors.append(f"{case_id}: {exc}")

    return CorpusEvalReport(
        provider=normalized_provider,
        case_results=tuple(results),
        errors=tuple(errors),
    )


def corpus_eval_report_to_dict(report: CorpusEvalReport) -> dict[str, Any]:
    passed_count = sum(1 for result in report.case_results if result.passed)
    return {
        "provider": report.provider,
        "case_count": len(report.case_results),
        "passed_count": passed_count,
        "failed_count": len(report.case_results) - passed_count,
        "error_count": len(report.errors),
        "cases": [
            {
                "case_id": result.case_id,
                "description": result.description,
                "passed": result.passed,
                "diffs": list(result.diffs),
                "expected_signatures": [
                    list(signature) for signature in result.expected_signatures
                ],
                "actual_signatures": [list(signature) for signature in result.actual_signatures],
                "actual_candidates": list(result.actual_candidates),
            }
            for result in report.case_results
        ],
        "errors": list(report.errors),
    }


def format_corpus_eval_report(report: CorpusEvalReport) -> str:
    lines: list[str] = []
    passed_count = sum(1 for result in report.case_results if result.passed)
    total = len(report.case_results)
    lines.append(
        f"Observation pipeline corpus eval (provider={report.provider}, "
        f"{passed_count}/{total} passed)"
    )
    lines.append("")

    for result in report.case_results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"{result.case_id} {status} — {result.description}")
        for diff in result.diffs:
            lines.append(f"  - {diff}")
        if not result.passed and not result.diffs:
            lines.append("  - structural mismatch with no detailed diff")
        lines.append("")

    for error in report.errors:
        lines.append(f"ERROR: {error}")

    if report.errors:
        lines.append("")
    lines.append(
        f"Summary: {passed_count}/{total} passed, {len(report.errors)} errors"
    )
    return "\n".join(lines).rstrip() + "\n"
