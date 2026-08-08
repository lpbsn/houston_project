from __future__ import annotations

import json
import os
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import Q
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
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.analytics.services import (
    DUPLICATE_GUARD_SHORTLIST_STRATEGY,
    PatternClassificationRetryableError,
    classify_signal_pattern,
    finalize_retryable_pattern_classification_error,
)
from houston.signals.models import Signal

BACKFILL_SIMULATION_SCHEMA_VERSION = "analytics_pattern_backfill_simulation_v1"
BACKFILL_SIMULATION_DEFAULT_LIMIT = 100
BACKFILL_SIMULATION_OPT_IN_ENV = "HOUSTON_RUN_ANALYTICS_PATTERN_BACKFILL_SIMULATION"
BACKFILL_SIMULATION_ARCHIVE_DIR = Path(".artifacts/analytics-pattern-backfill-simulation")
BACKFILL_SIMULATION_TASK_MAX_RETRIES = 3
BACKFILL_SIMULATION_TASK_RETRY_DELAY_SECONDS = 30


@dataclass(frozen=True)
class BackfillSimulationProviderCall:
    phase: str
    status: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    error_code: str = ""


class CapturingBackfillPatternClassifierProvider:
    def __init__(self, provider: PatternClassifierProvider):
        self.provider = provider.provider
        self.model = getattr(provider, "model", "")
        self._provider = provider
        self.calls: list[dict[str, Any]] = []
        self.duplicate_guard_calls: list[dict[str, Any]] = []
        self.call_records: list[BackfillSimulationProviderCall] = []

    def classify(
        self,
        *,
        input_payload: dict[str, Any],
    ) -> PatternClassifierProviderResponse:
        self.calls.append(input_payload)
        started_at = time.monotonic()
        try:
            response = self._provider.classify(input_payload=input_payload)
        except Exception as exc:
            self.call_records.append(
                BackfillSimulationProviderCall(
                    phase="classification",
                    status="failed",
                    latency_ms=_elapsed_ms(started_at),
                    error_code=getattr(exc, "error_code", ""),
                )
            )
            raise
        self.call_records.append(
            BackfillSimulationProviderCall(
                phase="classification",
                status="succeeded",
                latency_ms=_elapsed_ms(started_at),
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.total_tokens,
            )
        )
        return response

    def assess_duplicate(
        self,
        *,
        input_payload: dict[str, Any],
    ) -> PatternClassifierProviderResponse:
        self.duplicate_guard_calls.append(input_payload)
        started_at = time.monotonic()
        try:
            response = self._provider.assess_duplicate(input_payload=input_payload)
        except Exception as exc:
            self.call_records.append(
                BackfillSimulationProviderCall(
                    phase="duplicate_guard",
                    status="failed",
                    latency_ms=_elapsed_ms(started_at),
                    error_code=getattr(exc, "error_code", ""),
                )
            )
            raise
        self.call_records.append(
            BackfillSimulationProviderCall(
                phase="duplicate_guard",
                status="succeeded",
                latency_ms=_elapsed_ms(started_at),
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.total_tokens,
            )
        )
        return response


@dataclass(frozen=True)
class BackfillSignalSimulationResult:
    signal_id: str
    signal_status: str
    initial_assignment_status: str
    initial_assignment_source: str
    claim_decisions: tuple[str, ...]
    claim_reasons: tuple[str, ...]
    outcome: str
    final_assignment_status: str
    final_assignment_source: str
    final_error_code: str
    provider_call_count: int
    duplicate_guard_call_count: int
    duplicate_guard_decision: str
    duplicate_guard_reason: str
    assigned_existing_pattern_id: str
    assigned_existing_pattern_label: str
    assigned_existing_pattern_normalized_label: str
    simulated_new_pattern_label: str
    simulated_new_pattern_normalized_label: str


@dataclass(frozen=True)
class BackfillSimulationReport:
    provider: str
    provider_model: str
    classifier_version: str
    prompt_version: str
    schema_version: str
    duplicate_guard_enabled: bool
    scope: dict[str, str | None]
    order: tuple[str, ...]
    default_limit: int
    effective_limit: int
    max_limit: int
    start_after_signal_id: str
    exclusions: dict[str, int]
    signal_results: tuple[BackfillSignalSimulationResult, ...]
    provider_calls: tuple[BackfillSimulationProviderCall, ...]
    payload_safety_status: str
    payload_safety_errors: tuple[str, ...] = field(default_factory=tuple)


def simulate_analytics_pattern_backfill(
    *,
    organization_id: uuid.UUID | str | None = None,
    establishment_id: uuid.UUID | str | None = None,
    start_after_signal_id: uuid.UUID | str | None = None,
    limit: int | None = None,
    provider_name: str = "fake",
    provider: PatternClassifierProvider | None = None,
    duplicate_guard_enabled: bool = True,
    archive: bool = False,
    archive_dir: Path | None = None,
) -> BackfillSimulationReport:
    normalized_provider = provider_name.strip().lower()
    if normalized_provider not in {"fake", "configured"}:
        raise ValueError("provider must be 'fake' or 'configured'")
    if normalized_provider == "configured":
        _assert_configured_provider_simulation_enabled()

    max_limit = int(
        getattr(settings, "HOUSTON_ANALYTICS_PATTERN_BACKFILL_SIMULATION_MAX_LIMIT", 500)
    )
    effective_limit = _effective_limit(limit=limit, max_limit=max_limit)
    scope = _scope(
        organization_id=organization_id,
        establishment_id=establishment_id,
    )
    selected_signal_ids, exclusions, cursor = _selected_signal_ids(
        scope=scope,
        start_after_signal_id=start_after_signal_id,
        limit=effective_limit,
    )
    selected_provider = provider or _provider_for_name(normalized_provider)
    capturing_provider = CapturingBackfillPatternClassifierProvider(selected_provider)

    with transaction.atomic():
        report = _simulate_selected_signals(
            provider_name=normalized_provider,
            provider=capturing_provider,
            scope=scope,
            selected_signal_ids=selected_signal_ids,
            exclusions=exclusions,
            cursor=cursor,
            effective_limit=effective_limit,
            max_limit=max_limit,
            duplicate_guard_enabled=duplicate_guard_enabled,
        )
        transaction.set_rollback(True)

    if archive:
        write_backfill_simulation_archive(
            report=backfill_simulation_report_to_dict(report),
            archive_dir=archive_dir,
        )
    return report


def backfill_simulation_report_to_dict(report: BackfillSimulationReport) -> dict[str, Any]:
    signal_results = [_signal_result_to_dict(result) for result in report.signal_results]
    metrics = _metrics(report.signal_results, report.provider_calls)
    return {
        "schema_version": BACKFILL_SIMULATION_SCHEMA_VERSION,
        "provider": report.provider,
        "provider_model": report.provider_model,
        "classifier_version": report.classifier_version,
        "prompt_version": report.prompt_version,
        "classification_schema_version": report.schema_version,
        "duplicate_guard": {
            "enabled": report.duplicate_guard_enabled,
            "prompt_version": ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
            "schema_version": ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
            "shortlist_strategy": DUPLICATE_GUARD_SHORTLIST_STRATEGY,
            "min_score": settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE,
            "max_candidates": settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MAX_CANDIDATES,
        },
        "scope": report.scope,
        "order": list(report.order),
        "default_limit": report.default_limit,
        "effective_limit": report.effective_limit,
        "max_limit": report.max_limit,
        "start_after_signal_id": report.start_after_signal_id,
        "metrics": metrics,
        "exclusions": report.exclusions,
        "payload_safety_status": report.payload_safety_status,
        "payload_safety_errors": list(report.payload_safety_errors),
        "signals": signal_results,
    }


def format_backfill_simulation_report(report: BackfillSimulationReport) -> str:
    metrics = _metrics(report.signal_results, report.provider_calls)
    return "\n".join(
        [
            f"Analytics pattern backfill simulation (provider={report.provider})",
            f"Signals inspected: {metrics['signals_inspected_count']}",
            f"Signals claimed: {metrics['signals_claimed_for_simulation_count']}",
            f"Already current: {metrics['assignments_already_current_count']}",
            f"Owner protected: {metrics['owner_correction_protected_count']}",
            "Would create new patterns: "
            f"{metrics['pattern_metrics']['would_create_new_pattern_count']}",
            f"Payload safety: {report.payload_safety_status}",
        ]
    )


def write_backfill_simulation_archive(
    *,
    report: dict[str, Any],
    archive_dir: Path | None = None,
) -> Path:
    target_dir = archive_dir or BACKFILL_SIMULATION_ARCHIVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"analytics-pattern-backfill-simulation-{timezone.now():%Y%m%d%H%M%S}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _simulate_selected_signals(
    *,
    provider_name: str,
    provider: CapturingBackfillPatternClassifierProvider,
    scope: dict[str, str | None],
    selected_signal_ids: list[uuid.UUID],
    exclusions: dict[str, int],
    cursor: str,
    effective_limit: int,
    max_limit: int,
    duplicate_guard_enabled: bool,
) -> BackfillSimulationReport:
    initial_pattern_ids = set(OperationalPattern.objects.values_list("id", flat=True))
    initial_processing_signal_ids = set(
        SignalPatternAssignment.objects.filter(
            signal_id__in=selected_signal_ids,
            classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
        ).values_list("signal_id", flat=True)
    )
    signal_results = []
    for signal_id in selected_signal_ids:
        signal_results.append(
            _simulate_signal(
                signal_id=signal_id,
                provider=provider,
                initial_pattern_ids=initial_pattern_ids,
                duplicate_guard_enabled=duplicate_guard_enabled,
            )
        )

    payload_errors = _payload_safety_errors(provider.calls + provider.duplicate_guard_calls)
    _assert_no_new_processing_assignments(
        selected_signal_ids=selected_signal_ids,
        initial_processing_signal_ids=initial_processing_signal_ids,
    )
    return BackfillSimulationReport(
        provider=provider_name,
        provider_model=provider.model,
        classifier_version=classifier_version_for_provider(provider),
        prompt_version=ANALYTICS_PATTERN_PROMPT_VERSION,
        schema_version=ANALYTICS_PATTERN_SCHEMA_VERSION,
        duplicate_guard_enabled=duplicate_guard_enabled,
        scope=scope,
        order=("created_at", "id"),
        default_limit=BACKFILL_SIMULATION_DEFAULT_LIMIT,
        effective_limit=effective_limit,
        max_limit=max_limit,
        start_after_signal_id=cursor,
        exclusions=exclusions,
        signal_results=tuple(signal_results),
        provider_calls=tuple(provider.call_records),
        payload_safety_status="pass" if not payload_errors else "fail",
        payload_safety_errors=tuple(payload_errors),
    )


def _simulate_signal(
    *,
    signal_id: uuid.UUID,
    provider: CapturingBackfillPatternClassifierProvider,
    initial_pattern_ids: set[uuid.UUID],
    duplicate_guard_enabled: bool,
) -> BackfillSignalSimulationResult:
    signal = _load_simulation_signal(signal_id)
    initial_assignment = _assignment_for_signal(signal)
    initial_assignment_status = (
        initial_assignment.classification_status if initial_assignment is not None else "missing"
    )
    initial_assignment_source = (
        initial_assignment.assignment_source if initial_assignment is not None else ""
    )
    classify_calls_before = len(provider.calls)
    duplicate_calls_before = len(provider.duplicate_guard_calls)
    claim_decisions, claim_reasons, assignment, outcome = _run_classification_to_terminal_state(
        signal=signal,
        provider=provider,
        duplicate_guard_enabled=duplicate_guard_enabled,
    )
    classify_calls_after = len(provider.calls)
    duplicate_calls_after = len(provider.duplicate_guard_calls)
    duplicate_guard_decision = getattr(assignment, "_analytics_duplicate_guard_decision", "")
    duplicate_guard_reason = getattr(assignment, "_analytics_duplicate_guard_reason", "")
    pattern = assignment.pattern if assignment is not None else None
    is_simulated_pattern = pattern is not None and pattern.id not in initial_pattern_ids
    return BackfillSignalSimulationResult(
        signal_id=str(signal.id),
        signal_status=signal.status,
        initial_assignment_status=initial_assignment_status,
        initial_assignment_source=initial_assignment_source,
        claim_decisions=tuple(claim_decisions),
        claim_reasons=tuple(claim_reasons),
        outcome=outcome,
        final_assignment_status=assignment.classification_status if assignment else "missing",
        final_assignment_source=assignment.assignment_source if assignment else "",
        final_error_code=assignment.last_error_code if assignment else "",
        provider_call_count=classify_calls_after - classify_calls_before,
        duplicate_guard_call_count=duplicate_calls_after - duplicate_calls_before,
        duplicate_guard_decision=duplicate_guard_decision,
        duplicate_guard_reason=duplicate_guard_reason,
        assigned_existing_pattern_id=str(pattern.id)
        if pattern is not None and not is_simulated_pattern
        else "",
        assigned_existing_pattern_label=pattern.label
        if pattern is not None and not is_simulated_pattern
        else "",
        assigned_existing_pattern_normalized_label=pattern.normalized_label
        if pattern is not None and not is_simulated_pattern
        else "",
        simulated_new_pattern_label=(
            pattern.label if pattern is not None and is_simulated_pattern else ""
        ),
        simulated_new_pattern_normalized_label=(
            pattern.normalized_label if pattern is not None and is_simulated_pattern else ""
        ),
    )


def _run_classification_to_terminal_state(
    *,
    signal: Signal,
    provider: CapturingBackfillPatternClassifierProvider,
    duplicate_guard_enabled: bool,
) -> tuple[list[str], list[str], SignalPatternAssignment | None, str]:
    retries = 0
    claim_decisions: list[str] = []
    claim_reasons: list[str] = []
    while True:
        try:
            assignment = classify_signal_pattern(
                signal.id,
                provider=provider,
                duplicate_guard_enabled=duplicate_guard_enabled,
            )
            claim_status = getattr(assignment, "_analytics_claim_status", "no_assignment")
            claim_reason = getattr(assignment, "_analytics_claim_reason", "")
            claim_decisions.append(claim_status)
            claim_reasons.append(claim_reason)
            return (
                claim_decisions,
                claim_reasons,
                assignment,
                _outcome_from_assignment(
                    assignment=assignment,
                    claim_status=claim_status,
                    claim_reason=claim_reason,
                ),
            )
        except PatternClassificationRetryableError as exc:
            claim_decisions.append("claimed")
            claim_reasons.append("retryable_error")
            signal.refresh_from_db()
            finalization = finalize_retryable_pattern_classification_error(
                signal=signal,
                exc=exc,
                retries=retries,
                max_retries=BACKFILL_SIMULATION_TASK_MAX_RETRIES,
                retry_delay_seconds=BACKFILL_SIMULATION_TASK_RETRY_DELAY_SECONDS,
            )
            if finalization.outcome == "retry":
                retries += 1
                continue
            return (
                claim_decisions,
                claim_reasons,
                finalization.assignment,
                finalization.outcome,
            )


def _outcome_from_assignment(
    *,
    assignment: SignalPatternAssignment | None,
    claim_status: str,
    claim_reason: str,
) -> str:
    if assignment is None:
        return "missing"
    if claim_status == "already_processing":
        return "already_processing"
    if claim_status == "obsolete":
        return "obsolete"
    if claim_status == "already_succeeded":
        if claim_reason == "owner_correction_protected":
            return "owner_protected"
        return "already_current"
    if assignment.classification_status == SignalPatternAssignment.ClassificationStatus.SUCCEEDED:
        return "simulated_succeeded"
    return assignment.classification_status


def _metrics(
    signal_results: tuple[BackfillSignalSimulationResult, ...],
    provider_calls: tuple[BackfillSimulationProviderCall, ...],
) -> dict[str, Any]:
    claim_decisions = Counter(
        decision
        for result in signal_results
        for decision in result.claim_decisions
    )
    initial_states = Counter(result.initial_assignment_status for result in signal_results)
    outcomes = Counter(result.outcome for result in signal_results)
    technical_state_policy_observed: dict[str, Counter[str]] = defaultdict(Counter)
    for result in signal_results:
        technical_state_policy_observed[result.initial_assignment_status][result.outcome] += 1
    simulated_labels = sorted(
        {
            result.simulated_new_pattern_normalized_label
            for result in signal_results
            if result.simulated_new_pattern_normalized_label
        }
    )
    return {
        "signals_inspected_count": len(signal_results),
        "signals_claimed_for_simulation_count": sum(
            1 for result in signal_results if "claimed" in result.claim_decisions
        ),
        "assignments_already_current_count": outcomes["already_current"],
        "owner_correction_protected_count": outcomes["owner_protected"],
        "owner_correction_reopened_count": sum(
            1
            for result in signal_results
            if result.initial_assignment_source
            == SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
            and "claimed" in result.claim_decisions
        ),
        "claim_decisions": dict(sorted(claim_decisions.items())),
        "technical_state_policy_observed": {
            state: dict(sorted(counter.items()))
            for state, counter in sorted(technical_state_policy_observed.items())
        },
        "assignment_initial_state": dict(sorted(initial_states.items())),
        "outcomes": dict(sorted(outcomes.items())),
        "pattern_metrics": {
            "reused_existing_pattern_count": sum(
                1 for result in signal_results if result.assigned_existing_pattern_id
            ),
            "strict_duplicate_reused_count": sum(
                1
                for result in signal_results
                if result.duplicate_guard_reason == "strict_duplicate"
            ),
            "duplicate_guard_reused_count": sum(
                1 for result in signal_results if result.duplicate_guard_decision == "reused"
            ),
            "would_create_new_pattern_count": len(simulated_labels),
            "simulated_new_patterns": simulated_labels,
        },
        "technical_error_count": sum(
            count
            for outcome, count in outcomes.items()
            if outcome
            in {
                SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED,
                SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED,
                "retry_exhausted",
            }
        ),
        "business_decision_count": sum(
            outcomes[outcome]
            for outcome in ("already_current", "owner_protected", "already_processing")
        ),
        "provider_calls": {
            "classification_count": sum(
                1 for call in provider_calls if call.phase == "classification"
            ),
            "duplicate_guard_count": sum(
                1 for call in provider_calls if call.phase == "duplicate_guard"
            ),
            "failed_count": sum(1 for call in provider_calls if call.status == "failed"),
            "total_tokens": sum(
                call.total_tokens or 0
                for call in provider_calls
                if call.total_tokens is not None
            ),
            "latency_ms_total": sum(call.latency_ms for call in provider_calls),
        },
    }


def _signal_result_to_dict(result: BackfillSignalSimulationResult) -> dict[str, Any]:
    return {
        "signal_id": result.signal_id,
        "signal_status": result.signal_status,
        "initial_assignment_status": result.initial_assignment_status,
        "initial_assignment_source": result.initial_assignment_source,
        "claim_decisions": list(result.claim_decisions),
        "claim_reasons": list(result.claim_reasons),
        "outcome": result.outcome,
        "final_assignment_status": result.final_assignment_status,
        "final_assignment_source": result.final_assignment_source,
        "final_error_code": result.final_error_code,
        "provider_call_count": result.provider_call_count,
        "duplicate_guard_call_count": result.duplicate_guard_call_count,
        "duplicate_guard_decision": result.duplicate_guard_decision,
        "duplicate_guard_reason": result.duplicate_guard_reason,
        "assigned_existing_pattern_id": result.assigned_existing_pattern_id,
        "assigned_existing_pattern_label": result.assigned_existing_pattern_label,
        "assigned_existing_pattern_normalized_label": (
            result.assigned_existing_pattern_normalized_label
        ),
        "simulated_new_pattern_label": result.simulated_new_pattern_label,
        "simulated_new_pattern_normalized_label": (
            result.simulated_new_pattern_normalized_label
        ),
    }


def _selected_signal_ids(
    *,
    scope: dict[str, str | None],
    start_after_signal_id: uuid.UUID | str | None,
    limit: int,
) -> tuple[list[uuid.UUID], dict[str, int], str]:
    scoped = _scoped_signals(scope=scope)
    cursor = ""
    if start_after_signal_id:
        cursor_uuid = uuid.UUID(str(start_after_signal_id))
        cursor_signal = scoped.filter(id=cursor_uuid).first()
        if cursor_signal is None:
            raise ValueError("start-after signal was not found in the selected scope")
        scoped = scoped.filter(
            Q(created_at__gt=cursor_signal.created_at)
            | Q(created_at=cursor_signal.created_at, id__gt=cursor_signal.id)
        )
        cursor = str(cursor_signal.id)
    exclusions = {
        "merged": scoped.filter(merged_into_id__isnull=False).count(),
    }
    ids = list(
        scoped.filter(merged_into_id__isnull=True)
        .order_by("created_at", "id")
        .values_list("id", flat=True)[:limit]
    )
    return ids, exclusions, cursor


def _scoped_signals(*, scope: dict[str, str | None]):
    queryset = Signal.objects.select_related("establishment", "establishment__organization")
    if scope["organization_id"]:
        queryset = queryset.filter(establishment__organization_id=scope["organization_id"])
    if scope["establishment_id"]:
        queryset = queryset.filter(establishment_id=scope["establishment_id"])
    return queryset


def _scope(
    *,
    organization_id: uuid.UUID | str | None,
    establishment_id: uuid.UUID | str | None,
) -> dict[str, str | None]:
    return {
        "organization_id": str(uuid.UUID(str(organization_id))) if organization_id else None,
        "establishment_id": str(uuid.UUID(str(establishment_id))) if establishment_id else None,
    }


def _effective_limit(*, limit: int | None, max_limit: int) -> int:
    selected = BACKFILL_SIMULATION_DEFAULT_LIMIT if limit is None else int(limit)
    if selected < 1:
        raise ValueError("limit must be at least 1")
    if selected > max_limit:
        raise ValueError(f"limit must be less than or equal to {max_limit}")
    return selected


def _load_simulation_signal(signal_id: uuid.UUID) -> Signal:
    return Signal.objects.select_related(
        "establishment",
        "establishment__organization",
        "affected_business_unit",
        "responsible_business_unit",
        "activity_subject",
        "operational_unit",
        "merged_into",
    ).get(pk=signal_id)


def _assignment_for_signal(signal: Signal) -> SignalPatternAssignment | None:
    return (
        SignalPatternAssignment.objects.select_related("pattern")
        .filter(signal=signal)
        .first()
    )


def _provider_for_name(provider_name: str) -> PatternClassifierProvider:
    if provider_name == "fake":
        return FakePatternClassifierProvider()
    return get_pattern_classifier_provider()


def _assert_no_new_processing_assignments(
    *,
    selected_signal_ids: list[uuid.UUID],
    initial_processing_signal_ids: set[uuid.UUID],
) -> None:
    processing_count = SignalPatternAssignment.objects.filter(
        signal_id__in=selected_signal_ids,
        classification_status=SignalPatternAssignment.ClassificationStatus.PROCESSING,
    ).exclude(signal_id__in=initial_processing_signal_ids).count()
    if processing_count:
        raise RuntimeError("Analytics backfill simulation left processing assignments.")


def _payload_safety_errors(payloads: list[dict[str, Any]]) -> list[str]:
    serialized = json.dumps(payloads, ensure_ascii=False)
    forbidden_tokens = (
        "raw_text",
        "media",
        "comment",
        "action_plan",
        "author",
        "submitted_at",
        "location_text",
        "routing_status",
        "expected_action",
    )
    return [token for token in forbidden_tokens if token in serialized]


def _assert_configured_provider_simulation_enabled() -> None:
    if os.environ.get(BACKFILL_SIMULATION_OPT_IN_ENV) != "1":
        raise RuntimeError(
            f"Configured Analytics pattern backfill simulation is opt-in only. Set "
            f"{BACKFILL_SIMULATION_OPT_IN_ENV}=1."
        )
    provider_name = settings.HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER.strip().lower()
    if provider_name == "fake":
        raise RuntimeError(
            "Configured Analytics pattern backfill simulation requires a non-fake provider."
        )


def _elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))
