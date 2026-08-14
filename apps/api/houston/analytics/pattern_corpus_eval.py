from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from houston.analytics.classifier import (
    ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
    ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
    ANALYTICS_PATTERN_PROMPT_VERSION,
    ANALYTICS_PATTERN_SCHEMA_VERSION,
    FakePatternClassifierProvider,
    PatternClassifierProvider,
    PatternClassifierProviderResponse,
    classifier_version_for_provider,
    get_pattern_classifier_provider,
)
from houston.analytics.labels import normalize_pattern_label
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.analytics.payload_safety import assert_provider_payloads_are_safe
from houston.analytics.services import (
    DUPLICATE_GUARD_SHORTLIST_STRATEGY,
    PatternClassificationRetryableError,
    classify_signal_pattern,
    create_operational_pattern,
    finalize_retryable_pattern_classification_error,
)
from houston.establishments.models import OperationalUnit
from houston.signals.models import Signal
from houston.testing.analytics_pattern_corpus import (
    AnalyticsPatternCorpusValidationError,
    get_analytics_pattern_scenario,
    list_analytics_pattern_scenario_ids,
    normalized_pair,
    validate_analytics_pattern_corpus,
)
from houston.testing.factories import build_membership
from houston.testing.taxonomy import create_activity_subject, create_business_unit

ANALYTICS_PATTERN_EVAL_OPT_IN_ENV = "HOUSTON_RUN_ANALYTICS_PATTERN_EVAL"
ANALYTICS_PATTERN_EVAL_ARCHIVE_DIR = (
    Path(__file__).resolve().parents[3] / ".artifacts" / "analytics-pattern-eval"
)

MAIN_THRESHOLDS = {
    "false_merge_rate": ("lt", 0.05),
    "acceptable_grouping_rate": ("gte", 0.85),
    "technical_success_rate": ("gte", 0.98),
}


@dataclass(frozen=True)
class CorpusSignalResult:
    ref: str
    classification_status: str
    technical_success: bool
    assigned_pattern_key: str | None = None
    assigned_label: str = ""
    expected_pattern_key: str | None = None
    expected_new_pattern_label: str = ""
    error_code: str = ""
    provider_call_count: int = 0
    duplicate_guard_decision: str = ""
    duplicate_guard_reason: str = ""
    duplicate_guard_reason_code: str | None = None


@dataclass(frozen=True)
class CorpusScenarioResult:
    scenario_id: str
    signal_order: tuple[str, ...]
    signal_results: tuple[CorpusSignalResult, ...]
    metrics: dict[str, Any] = field(default_factory=dict)
    idempotence: dict[str, Any] = field(default_factory=dict)
    duplicate_guard_comparison: dict[str, Any] = field(default_factory=dict)
    errors: tuple[str, ...] = ()


@dataclass
class AnalyticsPatternCorpusEvalReport:
    provider: str
    provider_model: str
    classifier_version: str
    prompt_version: str
    schema_version: str
    timeout_seconds: int | None
    max_retries: int
    retry_delay_seconds: int
    scenario_results: tuple[CorpusScenarioResult, ...]
    metrics: dict[str, Any]
    errors: tuple[str, ...] = ()


class CapturingPatternClassifierProvider:
    def __init__(self, provider: PatternClassifierProvider):
        self.provider = provider.provider
        self.model = getattr(provider, "model", "")
        self._provider = provider
        self.calls: list[dict[str, Any]] = []
        self.duplicate_guard_calls: list[dict[str, Any]] = []

    def classify(self, *, input_payload: dict[str, Any]) -> PatternClassifierProviderResponse:
        self.calls.append(input_payload)
        return self._provider.classify(input_payload=input_payload)

    def assess_duplicate(
        self,
        *,
        input_payload: dict[str, Any],
    ) -> PatternClassifierProviderResponse:
        self.duplicate_guard_calls.append(input_payload)
        return self._provider.assess_duplicate(input_payload=input_payload)


class CorpusFakePatternClassifierProvider(FakePatternClassifierProvider):
    def __init__(
        self,
        *,
        response: dict[str, Any],
        pattern_ids_by_key: dict[str, Any],
    ):
        self._response = response
        self._pattern_ids_by_key = pattern_ids_by_key
        super().__init__(payload={})

    def classify(self, *, input_payload: dict[str, Any]) -> PatternClassifierProviderResponse:
        self.calls.append(input_payload)
        return PatternClassifierProviderResponse(
            payload={"canonical_label": self._response["canonical_label"]},
            model=self.model,
        )

    def assess_duplicate(
        self,
        *,
        input_payload: dict[str, Any],
    ) -> PatternClassifierProviderResponse:
        self.duplicate_guard_calls.append(input_payload)
        response = self._response.get("duplicate_guard_response") or {
            "result_type": "create_new_pattern"
        }
        if response["result_type"] == "reuse_existing_pattern":
            pattern_key = response["pattern_key"]
            return PatternClassifierProviderResponse(
                payload={
                    "result_type": "reuse_existing_pattern",
                    "pattern_id": str(self._pattern_ids_by_key[pattern_key]),
                    "reason_code": response.get("reason_code", "same_phenomenon"),
                },
                model=self.model,
            )
        return PatternClassifierProviderResponse(
            payload={
                "result_type": "create_new_pattern",
                "pattern_id": None,
                "reason_code": response.get("reason_code", "ambiguous"),
            },
            model=self.model,
        )


def evaluate_analytics_pattern_corpus(
    *,
    scenario_ids: list[str] | None = None,
    provider_name: str = "fake",
    rollback: bool = True,
    archive: bool = False,
    archive_dir: Path | None = None,
) -> AnalyticsPatternCorpusEvalReport:
    validation_errors = validate_analytics_pattern_corpus()
    if validation_errors:
        raise AnalyticsPatternCorpusValidationError("; ".join(validation_errors))

    selected_scenario_ids = _selected_scenario_ids(scenario_ids)
    normalized_provider = provider_name.strip().lower()
    if normalized_provider not in {"fake", "configured"}:
        raise ValueError("provider must be 'fake' or 'configured'")
    if normalized_provider == "configured":
        _assert_configured_provider_eval_enabled()

    if rollback:
        with transaction.atomic():
            report = _evaluate_selected_scenarios(
                scenario_ids=selected_scenario_ids,
                provider_name=normalized_provider,
            )
            transaction.set_rollback(True)
    else:
        report = _evaluate_selected_scenarios(
            scenario_ids=selected_scenario_ids,
            provider_name=normalized_provider,
        )

    if archive:
        write_analytics_pattern_eval_archive(
            report=analytics_pattern_corpus_eval_report_to_dict(report),
            archive_dir=archive_dir,
        )
    return report


def analytics_pattern_corpus_eval_report_to_dict(
    report: AnalyticsPatternCorpusEvalReport,
) -> dict[str, Any]:
    thresholds_passed = all_thresholds_passed(report.metrics)
    return {
        "provider": report.provider,
        "provider_model": report.provider_model,
        "classifier_version": report.classifier_version,
        "prompt_version": report.prompt_version,
        "schema_version": report.schema_version,
        "duplicate_guard": {
            "prompt_version": ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
            "schema_version": ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
            "shortlist_strategy": DUPLICATE_GUARD_SHORTLIST_STRATEGY,
            "min_score": settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE,
            "max_candidates": settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MAX_CANDIDATES,
        },
        "timeout_seconds": report.timeout_seconds,
        "max_retries": report.max_retries,
        "retry_delay_seconds": report.retry_delay_seconds,
        "metrics": report.metrics,
        "errors": list(report.errors),
        "thresholds_passed": thresholds_passed,
        "evaluation_status": (
            "pass" if analytics_pattern_corpus_eval_passed(report) else "fail"
        ),
        "scenarios": [
            {
                "scenario_id": scenario.scenario_id,
                "signal_order": list(scenario.signal_order),
                "metrics": scenario.metrics,
                "idempotence": scenario.idempotence,
                "duplicate_guard_comparison": scenario.duplicate_guard_comparison,
                "errors": list(scenario.errors),
                "signals": [
                    {
                        "ref": signal.ref,
                        "classification_status": signal.classification_status,
                        "technical_success": signal.technical_success,
                        "assigned_pattern_key": signal.assigned_pattern_key,
                        "assigned_label": signal.assigned_label,
                        "expected_pattern_key": signal.expected_pattern_key,
                        "expected_new_pattern_label": signal.expected_new_pattern_label,
                        "error_code": signal.error_code,
                        "provider_call_count": signal.provider_call_count,
                        "duplicate_guard_decision": signal.duplicate_guard_decision,
                        "duplicate_guard_reason": signal.duplicate_guard_reason,
                        "duplicate_guard_reason_code": signal.duplicate_guard_reason_code,
                    }
                    for signal in scenario.signal_results
                ],
            }
            for scenario in report.scenario_results
        ],
    }


def format_analytics_pattern_corpus_eval_report(
    report: AnalyticsPatternCorpusEvalReport,
) -> str:
    lines = [
        f"Analytics pattern corpus eval (provider={report.provider})",
        f"schema={report.schema_version} prompt={report.prompt_version}",
        "",
    ]
    for metric_name, metric in report.metrics.items():
        rate = metric.get("rate")
        rendered_rate = "n/a" if rate is None else f"{rate:.3f}"
        lines.append(
            f"{metric_name}: {metric.get('status')} "
            f"({metric.get('passed')}/{metric.get('total')}, rate={rendered_rate})"
        )
    lines.append("")
    for scenario in report.scenario_results:
        lines.append(f"{scenario.scenario_id}: {len(scenario.signal_results)} signals")
        if scenario.errors:
            for error in scenario.errors:
                lines.append(f"  - {error}")
    if report.errors:
        lines.append("")
        lines.append("Errors:")
        for error in report.errors:
            lines.append(f"  - {error}")
    return "\n".join(lines).rstrip() + "\n"


def all_thresholds_passed(metrics: dict[str, Any]) -> bool:
    return all(
        metric.get("status") in {"pass", "not_applicable"}
        for key, metric in metrics.items()
        if key in MAIN_THRESHOLDS
    )


def analytics_pattern_corpus_eval_passed(
    report: AnalyticsPatternCorpusEvalReport,
) -> bool:
    return (
        not report.errors
        and bool(report.scenario_results)
        and all_thresholds_passed(report.metrics)
    )


def write_analytics_pattern_eval_archive(
    *,
    report: dict[str, Any],
    archive_dir: Path | None = None,
) -> Path:
    target_dir = archive_dir or ANALYTICS_PATTERN_EVAL_ARCHIVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = target_dir / f"analytics-pattern-eval-{stamp}.json"
    body = {
        "archived_at": stamp,
        **report,
    }
    path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _evaluate_selected_scenarios(
    *,
    scenario_ids: list[str],
    provider_name: str,
) -> AnalyticsPatternCorpusEvalReport:
    provider_template = _provider_template(provider_name)
    scenario_results: list[CorpusScenarioResult] = []
    errors: list[str] = []
    for scenario_id in scenario_ids:
        try:
            scenario_results.append(
                _evaluate_scenario(
                    scenario=get_analytics_pattern_scenario(scenario_id),
                    provider_name=provider_name,
                )
            )
        except Exception as exc:  # noqa: BLE001 - report per-scenario failure safely.
            errors.append(f"{scenario_id}: {exc.__class__.__name__}")

    combined_metrics = _combine_metrics(tuple(scenario_results))
    return AnalyticsPatternCorpusEvalReport(
        provider=provider_name,
        provider_model=getattr(provider_template, "model", ""),
        classifier_version=classifier_version_for_provider(provider_template),
        prompt_version=ANALYTICS_PATTERN_PROMPT_VERSION,
        schema_version=ANALYTICS_PATTERN_SCHEMA_VERSION,
        timeout_seconds=getattr(provider_template, "timeout_seconds", None),
        max_retries=3,
        retry_delay_seconds=30,
        scenario_results=tuple(scenario_results),
        metrics=combined_metrics,
        errors=tuple(errors),
    )


def _evaluate_scenario(
    *,
    scenario: dict[str, Any],
    provider_name: str,
) -> CorpusScenarioResult:
    with transaction.atomic():
        baseline = _evaluate_scenario_once(
            scenario=scenario,
            provider_name=provider_name,
            duplicate_guard_enabled=False,
        )
        transaction.set_rollback(True)

    with transaction.atomic():
        guarded = _evaluate_scenario_once(
            scenario=scenario,
            provider_name=provider_name,
            duplicate_guard_enabled=True,
        )
        transaction.set_rollback(True)

    return CorpusScenarioResult(
        scenario_id=guarded.scenario_id,
        signal_order=guarded.signal_order,
        signal_results=guarded.signal_results,
        metrics=guarded.metrics,
        idempotence=guarded.idempotence,
        duplicate_guard_comparison=_duplicate_guard_comparison(
            baseline=baseline,
            guarded=guarded,
        ),
        errors=guarded.errors,
    )


def _evaluate_scenario_once(
    *,
    scenario: dict[str, Any],
    provider_name: str,
    duplicate_guard_enabled: bool,
) -> CorpusScenarioResult:
    membership = build_membership()
    establishment = membership.establishment
    business_units = {
        raw["key"]: create_business_unit(
            establishment=establishment,
            key=raw["key"],
            label=raw["label"],
        )
        for raw in scenario["business_units"]
    }
    activity_subjects = {
        raw["key"]: create_activity_subject(
            establishment=establishment,
            business_unit=business_units[raw["business_unit_key"]],
            label=raw["label"],
        )
        for raw in scenario["activity_subjects"]
    }
    operational_units = {
        raw["key"]: OperationalUnit.objects.create(
            establishment=establishment,
            key=raw["key"],
            label=raw["label"],
        )
        for raw in scenario.get("operational_units", [])
    }
    patterns_by_key = {
        raw["pattern_key"]: create_operational_pattern(
            organization=establishment.organization,
            label=raw["label"],
        )
        for raw in scenario.get("initial_patterns", [])
    }
    pattern_ids_by_key = {key: pattern.id for key, pattern in patterns_by_key.items()}
    pattern_keys_by_id = {pattern.id: key for key, pattern in patterns_by_key.items()}

    signals_by_ref: dict[str, Signal] = {}
    signal_specs_by_ref = {raw["ref"]: raw for raw in scenario["signals"]}
    signal_results: list[CorpusSignalResult] = []
    all_provider_calls: list[dict[str, Any]] = []
    for raw in scenario["signals"]:
        signal = Signal.objects.create(
            establishment=establishment,
            affected_business_unit=business_units[raw["affected_business_unit_key"]],
            responsible_business_unit=business_units[raw["responsible_business_unit_key"]],
            activity_subject=activity_subjects[raw["activity_subject_key"]],
            operational_unit=(
                operational_units[raw["operational_unit_key"]]
                if raw.get("operational_unit_key") is not None
                else None
            ),
            routing_status=Signal.RoutingStatus.RESOLVED,
            title=raw["title"],
            structured_summary=raw["structured_summary"],
            issue_focus=raw["issue_focus"],
            last_activity_at=timezone.now(),
        )
        signals_by_ref[raw["ref"]] = signal

    for raw in scenario["signals"]:
        signal = signals_by_ref[raw["ref"]]
        provider = _provider_for_signal(
            provider_name=provider_name,
            fake_response=scenario["fake_responses"][raw["ref"]],
            pattern_ids_by_key=pattern_ids_by_key,
        )
        assignment = _run_classification_to_terminal_state(
            signal=signal,
            provider=provider,
            max_retries=3,
            retry_delay_seconds=30,
            duplicate_guard_enabled=duplicate_guard_enabled,
        )
        all_provider_calls.extend(provider.calls)
        all_provider_calls.extend(provider.duplicate_guard_calls)
        signal_results.append(
            _build_signal_result(
                signal_ref=raw["ref"],
                signal_spec=raw,
                assignment=assignment,
                pattern_keys_by_id=pattern_keys_by_id,
                provider_call_count=len(provider.calls),
            )
        )

    _assert_no_processing_assignments(signals_by_ref.values())
    _assert_payloads_are_safe(all_provider_calls)
    idempotence = _evaluate_idempotence(
        scenario=scenario,
        signals_by_ref=signals_by_ref,
        first_results=tuple(signal_results),
        provider_name=provider_name,
        pattern_ids_by_key=pattern_ids_by_key,
        duplicate_guard_enabled=duplicate_guard_enabled,
    )
    metrics = _scenario_metrics(
        scenario=scenario,
        signal_results=tuple(signal_results),
        signal_specs_by_ref=signal_specs_by_ref,
    )
    return CorpusScenarioResult(
        scenario_id=scenario["id"],
        signal_order=tuple(raw["ref"] for raw in scenario["signals"]),
        signal_results=tuple(signal_results),
        metrics=metrics,
        idempotence=idempotence,
    )


def _duplicate_guard_comparison(
    *,
    baseline: CorpusScenarioResult,
    guarded: CorpusScenarioResult,
) -> dict[str, Any]:
    baseline_new_patterns = _new_pattern_count(baseline.signal_results)
    guarded_new_patterns = _new_pattern_count(guarded.signal_results)
    return {
        "baseline": {
            "new_pattern_count": baseline_new_patterns,
            "fragmentation_false_separation_count": baseline.metrics[
                "fragmentation_false_separation_count"
            ],
            "false_merge_failing_count": baseline.metrics["false_merge_rate"].get(
                "failing_count",
                0,
            ),
            "technical_success_rate": baseline.metrics["technical_success_rate"],
        },
        "guard": {
            "new_pattern_count": guarded_new_patterns,
            "fragmentation_false_separation_count": guarded.metrics[
                "fragmentation_false_separation_count"
            ],
            "false_merge_failing_count": guarded.metrics["false_merge_rate"].get(
                "failing_count",
                0,
            ),
            "technical_success_rate": guarded.metrics["technical_success_rate"],
            "duplicate_guard_reuse_count": guarded.metrics[
                "duplicate_guard_reuse_count"
            ],
            "duplicate_guard_created_count": guarded.metrics[
                "duplicate_guard_created_count"
            ],
            "duplicate_guard_skipped_count": guarded.metrics[
                "duplicate_guard_skipped_count"
            ],
            "duplicate_guard_fallback_count": guarded.metrics[
                "duplicate_guard_fallback_count"
            ],
        },
        "delta": {
            "new_pattern_count": guarded_new_patterns - baseline_new_patterns,
            "fragmentation_false_separation_count": guarded.metrics[
                "fragmentation_false_separation_count"
            ]
            - baseline.metrics["fragmentation_false_separation_count"],
            "false_merge_failing_count": guarded.metrics["false_merge_rate"].get(
                "failing_count",
                0,
            )
            - baseline.metrics["false_merge_rate"].get("failing_count", 0),
        },
    }


def _new_pattern_count(signal_results: tuple[CorpusSignalResult, ...]) -> int:
    return sum(
        1
        for result in signal_results
        if result.technical_success and result.assigned_pattern_key is None
    )


def _run_classification_to_terminal_state(
    *,
    signal: Signal,
    provider: CapturingPatternClassifierProvider | CorpusFakePatternClassifierProvider,
    max_retries: int,
    retry_delay_seconds: int,
    duplicate_guard_enabled: bool = True,
) -> SignalPatternAssignment | None:
    retries = 0
    while True:
        try:
            return classify_signal_pattern(
                signal.id,
                provider=provider,
                duplicate_guard_enabled=duplicate_guard_enabled,
            )
        except PatternClassificationRetryableError as exc:
            signal.refresh_from_db()
            finalization = finalize_retryable_pattern_classification_error(
                signal=signal,
                exc=exc,
                retries=retries,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
            )
            if finalization.outcome == "retry":
                retries += 1
                continue
            return finalization.assignment


def _evaluate_idempotence(
    *,
    scenario: dict[str, Any],
    signals_by_ref: dict[str, Signal],
    first_results: tuple[CorpusSignalResult, ...],
    provider_name: str,
    pattern_ids_by_key: dict[str, Any],
    duplicate_guard_enabled: bool,
) -> dict[str, Any]:
    eligible = [
        result
        for result in first_results
        if result.classification_status
        == SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    ]
    passed = 0
    for result in eligible:
        provider = _provider_for_signal(
            provider_name=provider_name,
            fake_response=scenario["fake_responses"][result.ref],
            pattern_ids_by_key=pattern_ids_by_key,
        )
        before_patterns = OperationalPattern.objects.count()
        assignment = classify_signal_pattern(
            signals_by_ref[result.ref].id,
            provider=provider,
            duplicate_guard_enabled=duplicate_guard_enabled,
        )
        after_patterns = OperationalPattern.objects.count()
        if (
            assignment is not None
            and assignment.classification_status
            == SignalPatternAssignment.ClassificationStatus.SUCCEEDED
            and not provider.calls
            and not provider.duplicate_guard_calls
            and before_patterns == after_patterns
        ):
            passed += 1
    return {
        "eligible_signal_count": len(eligible),
        "passed_signal_count": passed,
        "status": "pass" if passed == len(eligible) else "fail",
    }


def _build_signal_result(
    *,
    signal_ref: str,
    signal_spec: dict[str, Any],
    assignment: SignalPatternAssignment | None,
    pattern_keys_by_id: dict[Any, str],
    provider_call_count: int,
) -> CorpusSignalResult:
    if assignment is None:
        return CorpusSignalResult(
            ref=signal_ref,
            classification_status="missing",
            technical_success=False,
            expected_pattern_key=signal_spec.get("expected_pattern_key"),
            expected_new_pattern_label=signal_spec.get("expected_new_pattern_label", ""),
            provider_call_count=provider_call_count,
        )
    pattern = assignment.pattern
    return CorpusSignalResult(
        ref=signal_ref,
        classification_status=assignment.classification_status,
        technical_success=(
            assignment.classification_status
            == SignalPatternAssignment.ClassificationStatus.SUCCEEDED
        ),
        assigned_pattern_key=(
            pattern_keys_by_id.get(pattern.id)
            if pattern is not None and pattern.id in pattern_keys_by_id
            else None
        ),
        assigned_label=pattern.label if pattern is not None else "",
        expected_pattern_key=signal_spec.get("expected_pattern_key"),
        expected_new_pattern_label=signal_spec.get("expected_new_pattern_label", ""),
        error_code=assignment.last_error_code,
        provider_call_count=provider_call_count,
        duplicate_guard_decision=getattr(
            assignment,
            "_analytics_duplicate_guard_decision",
            "",
        ),
        duplicate_guard_reason=getattr(
            assignment,
            "_analytics_duplicate_guard_reason",
            "",
        ),
        duplicate_guard_reason_code=getattr(
            assignment,
            "_analytics_duplicate_guard_reason_code",
            None,
        ),
    )


def _scenario_metrics(
    *,
    scenario: dict[str, Any],
    signal_results: tuple[CorpusSignalResult, ...],
    signal_specs_by_ref: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    by_ref = {result.ref: result for result in signal_results}
    must_not_failed = 0
    must_not_total = len(scenario.get("must_not_link", []))
    for first, second in scenario.get("must_not_link", []):
        if _same_assigned_pattern(by_ref[first], by_ref[second]):
            must_not_failed += 1

    must_link_passed = 0
    must_link_total = len(scenario.get("must_link", []))
    fragmentation_count = 0
    for first, second in scenario.get("must_link", []):
        if _same_assigned_pattern(by_ref[first], by_ref[second]):
            must_link_passed += 1
        else:
            fragmentation_count += 1

    succeeded = sum(1 for result in signal_results if result.technical_success)
    expected_pattern_results = [
        result for result in signal_results if result.expected_pattern_key is not None
    ]
    correct_existing = sum(
        1
        for result in expected_pattern_results
        if result.assigned_pattern_key == result.expected_pattern_key
    )
    unnecessary_creation = sum(
        1
        for result in expected_pattern_results
        if result.technical_success and result.assigned_pattern_key is None
    )
    expected_new_results = [
        result for result in signal_results if result.expected_new_pattern_label
    ]
    expected_new_created = sum(
        1
        for result in expected_new_results
        if result.technical_success
        and result.assigned_pattern_key is None
        and normalize_pattern_label(result.assigned_label)
        == normalize_pattern_label(result.expected_new_pattern_label)
    )
    label_quality_passed = sum(
        1
        for result in expected_new_results
        if result.technical_success
        and normalize_pattern_label(result.assigned_label)
        == normalize_pattern_label(result.expected_new_pattern_label)
        and not _label_includes_forbidden_context(
            label=result.assigned_label,
            signal_spec=signal_specs_by_ref[result.ref],
            scenario=scenario,
        )
    )
    guard_reused = sum(
        1 for result in signal_results if result.duplicate_guard_decision == "reused"
    )
    guard_created = sum(
        1 for result in signal_results if result.duplicate_guard_decision == "created"
    )
    guard_skipped = sum(
        1 for result in signal_results if result.duplicate_guard_decision == "skipped"
    )
    guard_fallback = sum(
        1 for result in signal_results if result.duplicate_guard_decision == "fallback"
    )

    return {
        "false_merge_rate": _rate_metric(
            passed=must_not_total - must_not_failed,
            total=must_not_total,
            metric_name="false_merge_rate",
            failing_count=must_not_failed,
        ),
        "acceptable_grouping_rate": _rate_metric(
            passed=must_link_passed,
            total=must_link_total,
            metric_name="acceptable_grouping_rate",
        ),
        "technical_success_rate": _rate_metric(
            passed=succeeded,
            total=len(signal_results),
            metric_name="technical_success_rate",
        ),
        "initial_pattern_attachment_rate": _rate_metric(
            passed=correct_existing,
            total=len(expected_pattern_results),
            metric_name="initial_pattern_attachment_rate",
        ),
        "unnecessary_new_pattern_count": unnecessary_creation,
        "expected_new_pattern_creation_rate": _rate_metric(
            passed=expected_new_created,
            total=len(expected_new_results),
            metric_name="expected_new_pattern_creation_rate",
        ),
        "fragmentation_false_separation_count": fragmentation_count,
        "canonical_label_quality_rate": _rate_metric(
            passed=label_quality_passed,
            total=len(expected_new_results),
            metric_name="canonical_label_quality_rate",
        ),
        "duplicate_guard_reuse_count": guard_reused,
        "duplicate_guard_created_count": guard_created,
        "duplicate_guard_skipped_count": guard_skipped,
        "duplicate_guard_fallback_count": guard_fallback,
        "duplicate_guard_reason_code_distribution": (
            _duplicate_guard_reason_code_distribution(signal_results)
        ),
    }


def _combine_metrics(
    scenario_results: tuple[CorpusScenarioResult, ...],
) -> dict[str, Any]:
    signal_results = tuple(
        signal
        for scenario in scenario_results
        for signal in scenario.signal_results
    )
    must_not_total = sum(
        scenario.metrics["false_merge_rate"]["total"] for scenario in scenario_results
    )
    must_not_failed = sum(
        scenario.metrics["false_merge_rate"].get("failing_count", 0)
        for scenario in scenario_results
    )
    must_link_total = sum(
        scenario.metrics["acceptable_grouping_rate"]["total"]
        for scenario in scenario_results
    )
    must_link_passed = sum(
        scenario.metrics["acceptable_grouping_rate"]["passed"]
        for scenario in scenario_results
    )
    succeeded = sum(1 for signal in signal_results if signal.technical_success)
    expected_pattern_total = sum(
        scenario.metrics["initial_pattern_attachment_rate"]["total"]
        for scenario in scenario_results
    )
    expected_pattern_passed = sum(
        scenario.metrics["initial_pattern_attachment_rate"]["passed"]
        for scenario in scenario_results
    )
    expected_new_total = sum(
        scenario.metrics["expected_new_pattern_creation_rate"]["total"]
        for scenario in scenario_results
    )
    expected_new_passed = sum(
        scenario.metrics["expected_new_pattern_creation_rate"]["passed"]
        for scenario in scenario_results
    )
    label_passed = sum(
        scenario.metrics["canonical_label_quality_rate"]["passed"]
        for scenario in scenario_results
    )
    return {
        "false_merge_rate": _rate_metric(
            passed=must_not_total - must_not_failed,
            total=must_not_total,
            metric_name="false_merge_rate",
            failing_count=must_not_failed,
        ),
        "acceptable_grouping_rate": _rate_metric(
            passed=must_link_passed,
            total=must_link_total,
            metric_name="acceptable_grouping_rate",
        ),
        "technical_success_rate": _rate_metric(
            passed=succeeded,
            total=len(signal_results),
            metric_name="technical_success_rate",
        ),
        "initial_pattern_attachment_rate": _rate_metric(
            passed=expected_pattern_passed,
            total=expected_pattern_total,
            metric_name="initial_pattern_attachment_rate",
        ),
        "unnecessary_new_pattern_count": sum(
            scenario.metrics["unnecessary_new_pattern_count"]
            for scenario in scenario_results
        ),
        "expected_new_pattern_creation_rate": _rate_metric(
            passed=expected_new_passed,
            total=expected_new_total,
            metric_name="expected_new_pattern_creation_rate",
        ),
        "fragmentation_false_separation_count": sum(
            scenario.metrics["fragmentation_false_separation_count"]
            for scenario in scenario_results
        ),
        "canonical_label_quality_rate": _rate_metric(
            passed=label_passed,
            total=expected_new_total,
            metric_name="canonical_label_quality_rate",
        ),
        "duplicate_guard_reuse_count": sum(
            scenario.metrics["duplicate_guard_reuse_count"]
            for scenario in scenario_results
        ),
        "duplicate_guard_created_count": sum(
            scenario.metrics["duplicate_guard_created_count"]
            for scenario in scenario_results
        ),
        "duplicate_guard_skipped_count": sum(
            scenario.metrics["duplicate_guard_skipped_count"]
            for scenario in scenario_results
        ),
        "duplicate_guard_fallback_count": sum(
            scenario.metrics["duplicate_guard_fallback_count"]
            for scenario in scenario_results
        ),
        "duplicate_guard_reason_code_distribution": _combine_reason_code_distributions(
            scenario.metrics["duplicate_guard_reason_code_distribution"]
            for scenario in scenario_results
        ),
    }


def _duplicate_guard_reason_code_distribution(
    signal_results: tuple[CorpusSignalResult, ...],
) -> dict[str, int]:
    distribution: dict[str, int] = {}
    for result in signal_results:
        if result.duplicate_guard_reason_code is None:
            continue
        distribution[result.duplicate_guard_reason_code] = (
            distribution.get(result.duplicate_guard_reason_code, 0) + 1
        )
    return distribution


def _combine_reason_code_distributions(
    distributions,
) -> dict[str, int]:
    combined: dict[str, int] = {}
    for distribution in distributions:
        for reason_code, count in distribution.items():
            combined[reason_code] = combined.get(reason_code, 0) + count
    return combined


def _rate_metric(
    *,
    passed: int,
    total: int,
    metric_name: str,
    failing_count: int | None = None,
) -> dict[str, Any]:
    if total == 0:
        return {
            "passed": passed,
            "total": total,
            "rate": None,
            "status": "not_applicable",
        }
    rate = (
        failing_count / total
        if metric_name == "false_merge_rate" and failing_count is not None
        else passed / total
    )
    status = "unscored"
    threshold = MAIN_THRESHOLDS.get(metric_name)
    if threshold is not None:
        operator, value = threshold
        status = "pass" if (
            rate < value if operator == "lt" else rate >= value
        ) else "fail"
    payload = {
        "passed": passed,
        "total": total,
        "rate": rate,
        "status": status,
    }
    if failing_count is not None:
        payload["failing_count"] = failing_count
    return payload


def _same_assigned_pattern(
    first: CorpusSignalResult,
    second: CorpusSignalResult,
) -> bool:
    if not first.technical_success or not second.technical_success:
        return False
    return normalize_pattern_label(first.assigned_label) == normalize_pattern_label(
        second.assigned_label
    )


def _label_includes_forbidden_context(
    *,
    label: str,
    signal_spec: dict[str, Any],
    scenario: dict[str, Any],
) -> bool:
    normalized = normalize_pattern_label(label)
    business_units_by_key = {
        raw["key"]: raw["label"] for raw in scenario["business_units"]
    }
    forbidden_labels = [
        business_units_by_key[signal_spec["affected_business_unit_key"]],
        business_units_by_key[signal_spec["responsible_business_unit_key"]],
    ]
    for forbidden_label in forbidden_labels:
        forbidden = normalize_pattern_label(forbidden_label)
        if forbidden and forbidden in normalized:
            return True
    return False


def _provider_for_signal(
    *,
    provider_name: str,
    fake_response: dict[str, Any],
    pattern_ids_by_key: dict[str, Any],
) -> CapturingPatternClassifierProvider | CorpusFakePatternClassifierProvider:
    if provider_name == "fake":
        return CorpusFakePatternClassifierProvider(
            response=fake_response,
            pattern_ids_by_key=pattern_ids_by_key,
        )
    return CapturingPatternClassifierProvider(get_pattern_classifier_provider())


def _provider_template(provider_name: str) -> PatternClassifierProvider:
    if provider_name == "fake":
        return FakePatternClassifierProvider()
    return get_pattern_classifier_provider()


def _assert_no_processing_assignments(signals: Any) -> None:
    processing_count = SignalPatternAssignment.objects.filter(
        signal__in=list(signals),
        classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
    ).count()
    if processing_count:
        raise RuntimeError("Analytics pattern eval left processing assignments.")


def _assert_payloads_are_safe(payloads: list[dict[str, Any]]) -> None:
    try:
        assert_provider_payloads_are_safe(payloads)
    except RuntimeError as exc:
        raise RuntimeError(
            "Analytics pattern eval sent forbidden provider payload data."
        ) from exc


def _selected_scenario_ids(raw_scenario_ids: list[str] | None) -> list[str]:
    known = list_analytics_pattern_scenario_ids()
    if not raw_scenario_ids:
        return known
    unknown = [scenario_id for scenario_id in raw_scenario_ids if scenario_id not in known]
    if unknown:
        raise ValueError(
            f"Unknown Analytics pattern scenario id(s): {', '.join(unknown)}. "
            f"Known: {', '.join(known)}"
        )
    return list(raw_scenario_ids)


def _assert_configured_provider_eval_enabled() -> None:
    if os.environ.get(ANALYTICS_PATTERN_EVAL_OPT_IN_ENV) != "1":
        raise RuntimeError(
            f"Configured Analytics pattern eval is opt-in only. Set "
            f"{ANALYTICS_PATTERN_EVAL_OPT_IN_ENV}=1."
        )
    provider_name = settings.HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER.strip().lower()
    if provider_name == "fake":
        raise RuntimeError("Configured Analytics pattern eval requires a non-fake provider.")


def selected_scenarios_have_no_orphan_pairs(scenario_ids: list[str]) -> bool:
    for scenario_id in scenario_ids:
        scenario = get_analytics_pattern_scenario(scenario_id)
        refs = {signal["ref"] for signal in scenario["signals"]}
        for pair in scenario.get("must_link", []) + scenario.get("must_not_link", []):
            first, second = normalized_pair(pair)
            if first not in refs or second not in refs:
                return False
    return True
