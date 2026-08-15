from __future__ import annotations

import json
import os
import uuid
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from houston.analytics.backfill_selection import (
    normalize_backfill_signal_ids,
    select_explicit_backfill_signal_ids,
)
from houston.analytics.backfill_simulation import CapturingBackfillPatternClassifierProvider
from houston.analytics.classifier import (
    ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
    ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
    ANALYTICS_PATTERN_PROMPT_VERSION,
    ANALYTICS_PATTERN_SCHEMA_VERSION,
    FakePatternClassifierProvider,
    PatternClassifierProvider,
    classifier_version_for_provider,
    get_pattern_classifier_provider,
)
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.analytics.payload_safety import provider_payload_safety_errors
from houston.analytics.retry_policy import analytics_pattern_task_retry_policy
from houston.analytics.services import (
    DUPLICATE_GUARD_SHORTLIST_STRATEGY,
    PatternClassificationRetryableError,
    classify_signal_pattern,
    finalize_retryable_pattern_classification_error,
)
from houston.signals.models import Signal

BACKFILL_SCHEMA_VERSION = "analytics_pattern_backfill_v1"
BACKFILL_DEFAULT_LIMIT = 100
BACKFILL_CONFIGURED_OPT_IN_ENV = "HOUSTON_RUN_ANALYTICS_PATTERN_BACKFILL"
BACKFILL_ALLOW_FAKE_ENV = "HOUSTON_ALLOW_FAKE_ANALYTICS_PATTERN_BACKFILL"
BACKFILL_ARCHIVE_DIR = Path(".artifacts/analytics-pattern-backfill")


@dataclass(frozen=True)
class BackfillSignalResult:
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
    final_validation_branch: str
    provider_call_count: int
    duplicate_guard_call_count: int
    duplicate_guard_decision: str
    duplicate_guard_reason: str
    duplicate_guard_reason_code: str | None
    remaining_reason: str
    assigned_existing_pattern_id: str
    assigned_existing_pattern_label: str
    assigned_existing_pattern_normalized_label: str
    created_pattern_id: str
    created_pattern_label: str
    created_pattern_normalized_label: str


@dataclass(frozen=True)
class BackfillReport:
    provider: str
    provider_model: str
    classifier_version: str
    prompt_version: str
    schema_version: str
    duplicate_guard_enabled: bool
    scope: dict[str, str | None]
    mode: str
    order: tuple[str, ...]
    default_limit: int
    effective_limit: int
    max_limit: int
    start_after_signal_id: str
    next_scan_cursor: str
    exclusions: dict[str, int]
    signal_results: tuple[BackfillSignalResult, ...]
    provider_calls: tuple[Any, ...]
    errors: tuple[dict[str, str], ...] = field(default_factory=tuple)
    payload_safety_status: str = "pass"
    payload_safety_errors: tuple[str, ...] = field(default_factory=tuple)


def backfill_analytics_patterns(
    *,
    organization_id: uuid.UUID | str | None = None,
    establishment_id: uuid.UUID | str | None = None,
    start_after_signal_id: uuid.UUID | str | None = None,
    signal_ids=None,
    limit: int | None = None,
    provider_name: str = "configured",
    provider: PatternClassifierProvider | None = None,
    duplicate_guard_enabled: bool = True,
    archive: bool = False,
    archive_dir: Path | None = None,
) -> BackfillReport:
    normalized_provider = provider_name.strip().lower()
    if normalized_provider not in {"fake", "configured"}:
        raise ValueError("provider must be 'fake' or 'configured'")
    _assert_provider_allowed(normalized_provider)

    max_limit = int(getattr(settings, "HOUSTON_ANALYTICS_PATTERN_BACKFILL_MAX_LIMIT", 500))
    effective_limit = _effective_limit(limit=limit, max_limit=max_limit)
    scope = _scope(organization_id=organization_id, establishment_id=establishment_id)
    normalized_signal_ids = normalize_backfill_signal_ids(signal_ids)
    if normalized_signal_ids:
        selected_signal_ids, exclusions, next_scan_cursor = select_explicit_backfill_signal_ids(
            signal_ids=normalized_signal_ids,
            scope=scope,
            limit=effective_limit,
        )
        mode = "explicit_signal_ids"
        cursor = ""
    else:
        selected_signal_ids, exclusions, cursor, _ = _scan_signal_ids(
            scope=scope,
            start_after_signal_id=start_after_signal_id,
            limit=effective_limit,
        )
        mode = "scan"

    selected_provider = provider or _provider_for_name(normalized_provider)
    _assert_effective_provider_allowed(
        provider_name=normalized_provider,
        provider=selected_provider,
    )
    capturing_provider = CapturingBackfillPatternClassifierProvider(selected_provider)
    initial_pattern_ids = set(OperationalPattern.objects.values_list("id", flat=True))
    signal_results: list[BackfillSignalResult] = []
    errors: list[dict[str, str]] = []
    for signal_id in selected_signal_ids:
        result = _backfill_signal(
            signal_id=signal_id,
            provider=capturing_provider,
            initial_pattern_ids=initial_pattern_ids,
            duplicate_guard_enabled=duplicate_guard_enabled,
        )
        signal_results.append(result)
        if result.outcome == "reported":
            errors.append(
                {
                    "signal_id": result.signal_id,
                    "signal_status": result.signal_status,
                    "error_code": result.final_error_code,
                }
            )

    if mode == "scan":
        next_scan_cursor = _safe_next_scan_cursor(
            input_cursor=cursor,
            signal_results=signal_results,
        )
    payload_errors = provider_payload_safety_errors(
        capturing_provider.calls + capturing_provider.duplicate_guard_calls
    )
    report = BackfillReport(
        provider=normalized_provider,
        provider_model=capturing_provider.model,
        classifier_version=classifier_version_for_provider(capturing_provider),
        prompt_version=ANALYTICS_PATTERN_PROMPT_VERSION,
        schema_version=ANALYTICS_PATTERN_SCHEMA_VERSION,
        duplicate_guard_enabled=duplicate_guard_enabled,
        scope=scope,
        mode=mode,
        order=("created_at", "id"),
        default_limit=BACKFILL_DEFAULT_LIMIT,
        effective_limit=effective_limit,
        max_limit=max_limit,
        start_after_signal_id=cursor,
        next_scan_cursor=next_scan_cursor,
        exclusions=exclusions,
        signal_results=tuple(signal_results),
        provider_calls=tuple(capturing_provider.call_records),
        errors=tuple(errors),
        payload_safety_status="pass" if not payload_errors else "fail",
        payload_safety_errors=tuple(payload_errors),
    )
    if archive:
        write_backfill_archive(report=backfill_report_to_dict(report), archive_dir=archive_dir)
    return report


def backfill_report_to_dict(report: BackfillReport) -> dict[str, Any]:
    return {
        "schema_version": BACKFILL_SCHEMA_VERSION,
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
        "mode": report.mode,
        "order": list(report.order),
        "default_limit": report.default_limit,
        "effective_limit": report.effective_limit,
        "max_limit": report.max_limit,
        "start_after_signal_id": report.start_after_signal_id,
        "next_scan_cursor": report.next_scan_cursor,
        "metrics": _metrics(report.signal_results, report.provider_calls),
        "exclusions": report.exclusions,
        "errors": list(report.errors),
        "payload_safety_status": report.payload_safety_status,
        "payload_safety_errors": list(report.payload_safety_errors),
        "signals": [_signal_result_to_dict(result) for result in report.signal_results],
    }


def backfill_report_failed(report: BackfillReport) -> bool:
    return bool(report.errors) or report.payload_safety_status != "pass"


def format_backfill_report(report: BackfillReport) -> str:
    metrics = _metrics(report.signal_results, report.provider_calls)
    return "\n".join(
        [
            f"Analytics pattern backfill (provider={report.provider}, mode={report.mode})",
            f"Signals inspected: {metrics['signals_inspected_count']}",
            f"Claimed: {metrics['signals_claimed_count']}",
            f"Already current: {metrics['assignments_already_current_count']}",
            f"Owner protected: {metrics['owner_correction_protected_count']}",
            f"Remaining: {len(metrics['remaining_signal_ids'])}",
            f"Payload safety: {report.payload_safety_status}",
        ]
    )


def write_backfill_archive(*, report: dict[str, Any], archive_dir: Path | None = None) -> Path:
    target_dir = archive_dir or BACKFILL_ARCHIVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"analytics-pattern-backfill-{timezone.now():%Y%m%d%H%M%S}.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _backfill_signal(
    *,
    signal_id: uuid.UUID,
    provider: CapturingBackfillPatternClassifierProvider,
    initial_pattern_ids: set[uuid.UUID],
    duplicate_guard_enabled: bool,
) -> BackfillSignalResult:
    signal = _load_signal(signal_id)
    initial_assignment = _assignment_for_signal(signal)
    initial_assignment_status = (
        initial_assignment.classification_status if initial_assignment is not None else "missing"
    )
    initial_assignment_source = (
        initial_assignment.assignment_source if initial_assignment is not None else ""
    )
    classify_calls_before = len(provider.calls)
    duplicate_calls_before = len(provider.duplicate_guard_calls)
    try:
        claim_decisions, claim_reasons, assignment, outcome, validation_branch = _run_once(
            signal=signal,
            provider=provider,
            duplicate_guard_enabled=duplicate_guard_enabled,
        )
    except Exception as exc:
        claim_decisions = []
        claim_reasons = []
        assignment = _assignment_for_signal(signal)
        outcome = "reported"
        error_code = getattr(exc, "error_code", exc.__class__.__name__)
        validation_branch = getattr(exc, "validation_branch", "")
    else:
        error_code = assignment.last_error_code if assignment else ""
    classify_calls_after = len(provider.calls)
    duplicate_calls_after = len(provider.duplicate_guard_calls)
    duplicate_guard_decision = getattr(assignment, "_analytics_duplicate_guard_decision", "")
    duplicate_guard_reason = getattr(assignment, "_analytics_duplicate_guard_reason", "")
    duplicate_guard_reason_code = getattr(
        assignment,
        "_analytics_duplicate_guard_reason_code",
        None,
    )
    pattern = assignment.pattern if assignment is not None else None
    is_created_pattern = pattern is not None and pattern.id not in initial_pattern_ids
    return BackfillSignalResult(
        signal_id=str(signal.id),
        signal_status=signal.status,
        initial_assignment_status=initial_assignment_status,
        initial_assignment_source=initial_assignment_source,
        claim_decisions=tuple(claim_decisions),
        claim_reasons=tuple(claim_reasons),
        outcome=outcome,
        final_assignment_status=assignment.classification_status if assignment else "missing",
        final_assignment_source=assignment.assignment_source if assignment else "",
        final_error_code=error_code,
        final_validation_branch=validation_branch,
        provider_call_count=classify_calls_after - classify_calls_before,
        duplicate_guard_call_count=duplicate_calls_after - duplicate_calls_before,
        duplicate_guard_decision=duplicate_guard_decision,
        duplicate_guard_reason=duplicate_guard_reason,
        duplicate_guard_reason_code=duplicate_guard_reason_code,
        remaining_reason=_remaining_reason(outcome),
        assigned_existing_pattern_id=str(pattern.id)
        if pattern is not None and not is_created_pattern
        else "",
        assigned_existing_pattern_label=pattern.label
        if pattern is not None and not is_created_pattern
        else "",
        assigned_existing_pattern_normalized_label=pattern.normalized_label
        if pattern is not None and not is_created_pattern
        else "",
        created_pattern_id=str(pattern.id) if pattern is not None and is_created_pattern else "",
        created_pattern_label=pattern.label if pattern is not None and is_created_pattern else "",
        created_pattern_normalized_label=(
            pattern.normalized_label if pattern is not None and is_created_pattern else ""
        ),
    )


def _run_once(
    *,
    signal: Signal,
    provider: CapturingBackfillPatternClassifierProvider,
    duplicate_guard_enabled: bool,
) -> tuple[list[str], list[str], SignalPatternAssignment | None, str, str]:
    try:
        assignment = classify_signal_pattern(
            signal.id,
            provider=provider,
            duplicate_guard_enabled=duplicate_guard_enabled,
        )
        claim_status = getattr(assignment, "_analytics_claim_status", "no_assignment")
        claim_reason = getattr(assignment, "_analytics_claim_reason", "")
        return (
            [claim_status],
            [claim_reason],
            assignment,
            _outcome_from_assignment(
                assignment=assignment,
                claim_status=claim_status,
                claim_reason=claim_reason,
            ),
            "",
        )
    except PatternClassificationRetryableError as exc:
        signal.refresh_from_db()
        retry_policy = analytics_pattern_task_retry_policy()
        finalization = finalize_retryable_pattern_classification_error(
            signal=signal,
            exc=exc,
            retries=_retry_count_for_attempt(exc.attempt_count),
            max_retries=retry_policy.max_retries,
            retry_delay_seconds=retry_policy.retry_delay_seconds,
        )
        outcome = (
            SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED
            if finalization.outcome == "retry"
            else finalization.outcome
        )
        return (
            ["claimed"],
            ["retryable_error"],
            finalization.assignment,
            outcome,
            exc.validation_branch,
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
        return "succeeded"
    return assignment.classification_status


def _metrics(
    signal_results: tuple[BackfillSignalResult, ...],
    provider_calls: tuple[Any, ...],
) -> dict[str, Any]:
    claim_decisions = Counter(
        decision for result in signal_results for decision in result.claim_decisions
    )
    outcomes = Counter(result.outcome for result in signal_results)
    initial_states = Counter(result.initial_assignment_status for result in signal_results)
    remaining_by_reason = Counter(
        result.remaining_reason for result in signal_results if result.remaining_reason
    )
    terminal_by_outcome = Counter(
        result.outcome
        for result in signal_results
        if result.outcome
        in {
            SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED,
            "retry_exhausted",
        }
    )
    created_labels = sorted(
        {
            result.created_pattern_normalized_label
            for result in signal_results
            if result.created_pattern_normalized_label
        }
    )
    return {
        "signals_inspected_count": len(signal_results),
        "signals_claimed_count": sum(
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
        "owner_correction_reopened_outcomes": dict(
            sorted(
                Counter(
                    result.outcome
                    for result in signal_results
                    if result.initial_assignment_source
                    == SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
                    and "claimed" in result.claim_decisions
                ).items()
            )
        ),
        "remaining_signal_ids": [
            result.signal_id for result in signal_results if result.remaining_reason
        ],
        "remaining_by_reason": dict(sorted(remaining_by_reason.items())),
        "terminal_outcomes": dict(sorted(terminal_by_outcome.items())),
        "claim_decisions": dict(sorted(claim_decisions.items())),
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
            "created_new_pattern_count": len(created_labels),
            "created_new_patterns": created_labels,
        },
        "technical_error_count": sum(
            count
            for outcome, count in outcomes.items()
            if outcome
            in {
                SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED,
                SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED,
                "retry_exhausted",
                "reported",
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


def _safe_next_scan_cursor(
    *,
    input_cursor: str,
    signal_results: list[BackfillSignalResult],
) -> str:
    if not signal_results:
        return ""
    next_cursor = input_cursor
    for result in signal_results:
        if result.remaining_reason:
            return next_cursor
        next_cursor = result.signal_id
    return next_cursor


def _signal_result_to_dict(result: BackfillSignalResult) -> dict[str, Any]:
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
        "final_validation_branch": result.final_validation_branch,
        "provider_call_count": result.provider_call_count,
        "duplicate_guard_call_count": result.duplicate_guard_call_count,
        "duplicate_guard_decision": result.duplicate_guard_decision,
        "duplicate_guard_reason": result.duplicate_guard_reason,
        "duplicate_guard_reason_code": result.duplicate_guard_reason_code,
        "remaining_reason": result.remaining_reason,
        "assigned_existing_pattern_id": result.assigned_existing_pattern_id,
        "assigned_existing_pattern_label": result.assigned_existing_pattern_label,
        "assigned_existing_pattern_normalized_label": (
            result.assigned_existing_pattern_normalized_label
        ),
        "created_pattern_id": result.created_pattern_id,
        "created_pattern_label": result.created_pattern_label,
        "created_pattern_normalized_label": result.created_pattern_normalized_label,
    }


def _scan_signal_ids(
    *,
    scope: dict[str, str | None],
    start_after_signal_id: uuid.UUID | str | None,
    limit: int,
) -> tuple[list[uuid.UUID], dict[str, int], str, str]:
    scoped = _scoped_signals(scope=scope)
    input_cursor = ""
    if start_after_signal_id:
        cursor_uuid = uuid.UUID(str(start_after_signal_id))
        cursor_signal = scoped.filter(id=cursor_uuid).first()
        if cursor_signal is None:
            raise ValueError("start-after signal was not found in the selected scope")
        scoped = scoped.filter(
            Q(created_at__gt=cursor_signal.created_at)
            | Q(created_at=cursor_signal.created_at, id__gt=cursor_signal.id)
        )
        input_cursor = str(cursor_signal.id)
    exclusions = {
        "merged": scoped.filter(merged_into_id__isnull=False).count(),
    }
    ids = list(
        scoped.filter(merged_into_id__isnull=True)
        .order_by("created_at", "id")
        .values_list("id", flat=True)[:limit]
    )
    next_cursor = str(ids[-1]) if ids else ""
    return ids, exclusions, input_cursor, next_cursor


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
    selected = BACKFILL_DEFAULT_LIMIT if limit is None else int(limit)
    if selected < 1:
        raise ValueError("limit must be at least 1")
    if selected > max_limit:
        raise ValueError(f"limit must be less than or equal to {max_limit}")
    return selected


def _load_signal(signal_id: uuid.UUID) -> Signal:
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


def _assert_provider_allowed(provider_name: str) -> None:
    if provider_name == "configured":
        if os.environ.get(BACKFILL_CONFIGURED_OPT_IN_ENV) != "1":
            raise RuntimeError(
                f"Configured Analytics pattern backfill is opt-in only. Set "
                f"{BACKFILL_CONFIGURED_OPT_IN_ENV}=1."
        )
        configured = settings.HOUSTON_AI_ANALYTICS_PATTERN_PROVIDER.strip().lower()
        if configured == "fake":
            raise RuntimeError(
                "Configured Analytics pattern backfill requires a non-fake provider."
            )
    elif not settings.DEBUG and os.environ.get(BACKFILL_ALLOW_FAKE_ENV) != "1":
        raise RuntimeError(
            f"Fake Analytics pattern backfill is opt-in only. Set {BACKFILL_ALLOW_FAKE_ENV}=1."
        )


def _assert_effective_provider_allowed(
    *,
    provider_name: str,
    provider: PatternClassifierProvider,
) -> None:
    if provider_name == "configured" and provider.provider.strip().lower() == "fake":
        raise RuntimeError(
            "Configured Analytics pattern backfill requires a non-fake effective provider."
        )


def _retry_count_for_attempt(attempt_count: int) -> int:
    return max(0, attempt_count - 1)


def _remaining_reason(outcome: str) -> str:
    if outcome in {
        SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED,
        "already_processing",
        "obsolete",
        "reported",
    }:
        return outcome
    return ""
