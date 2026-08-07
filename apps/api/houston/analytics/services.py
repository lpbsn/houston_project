from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.ai.models import AIUsageLog
from houston.analytics.classifier import (
    ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
    ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
    ANALYTICS_PATTERN_PROMPT_VERSION,
    ANALYTICS_PATTERN_SCHEMA_VERSION,
    PatternClassifierError,
    PatternClassifierInvalidOutputError,
    PatternClassifierProvider,
    PatternClassifierTimeoutError,
    PatternClassifierUnavailableError,
    classifier_version_for_provider,
    get_pattern_classifier_provider,
    parse_pattern_classifier_response,
    parse_pattern_duplicate_guard_response,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.labels import normalize_pattern_label
from houston.analytics.models import (
    PATTERN_LABEL_MAX_LENGTH,
    OperationalPattern,
    PatternLifecycleEvent,
    SignalPatternAssignment,
)
from houston.analytics.signature import (
    build_signal_pattern_payload,
    build_signal_pattern_signature,
)
from houston.establishments.models import EstablishmentMembership
from houston.organizations.models import Organization
from houston.signals.models import Signal

DUPLICATE_GUARD_SHORTLIST_STRATEGY = "token_overlap_v1"


class PatternClassificationRetryableError(Exception):
    def __init__(
        self,
        message: str,
        *,
        signal_id: uuid.UUID,
        attempt_count: int,
        pending_signature: str,
        pending_classifier_version: str,
        error_code: str,
    ):
        super().__init__(message)
        self.signal_id = signal_id
        self.attempt_count = attempt_count
        self.pending_signature = pending_signature
        self.pending_classifier_version = pending_classifier_version
        self.error_code = error_code


@dataclass(frozen=True)
class PatternClassificationClaimResult:
    status: str
    attempt_count: int | None
    assignment: SignalPatternAssignment


@dataclass(frozen=True)
class PatternClassificationRetryFinalization:
    outcome: str
    assignment: SignalPatternAssignment


class PatternClassificationObsoleteAttempt(Exception):
    def __init__(self, assignment: SignalPatternAssignment):
        super().__init__("Analytics pattern classification attempt is obsolete.")
        self.assignment = assignment


@dataclass(frozen=True)
class PatternDuplicateGuardCandidate:
    id: uuid.UUID
    label: str
    normalized_label: str
    score: float


@dataclass(frozen=True)
class PatternDuplicateGuardDecision:
    action: str
    pattern_id: uuid.UUID | None = None
    reason: str = ""


@dataclass(frozen=True)
class PatternClassifierPatternResolution:
    mode: str
    label: str = ""
    pattern_id: uuid.UUID | None = None
    duplicate_guard_decision: PatternDuplicateGuardDecision = field(
        default_factory=lambda: PatternDuplicateGuardDecision(action="skipped")
    )


@transaction.atomic
def create_operational_pattern(
    *,
    organization: Organization,
    label: str,
    created_by_membership: EstablishmentMembership | None = None,
    occurred_at=None,
    metadata_safe: dict[str, Any] | None = None,
) -> OperationalPattern:
    pattern = OperationalPattern(
        organization=organization,
        label=label,
        created_by_membership=created_by_membership,
    )
    try:
        pattern.full_clean(validate_unique=False, validate_constraints=False)
    except ValidationError as exc:
        raise AnalyticsValidationError(str(exc)) from exc
    pattern.save()

    event = PatternLifecycleEvent(
        pattern=pattern,
        organization=organization,
        event_type=PatternLifecycleEvent.EventType.CREATED,
        actor_membership=created_by_membership,
        occurred_at=occurred_at or timezone.now(),
        metadata_safe=metadata_safe or {},
    )
    try:
        event.full_clean(validate_unique=False, validate_constraints=False)
    except ValidationError as exc:
        raise AnalyticsValidationError(str(exc)) from exc
    event.save()

    return pattern


def _validate_and_save_assignment(
    assignment: SignalPatternAssignment,
    *,
    update_fields: list[str] | None = None,
) -> SignalPatternAssignment:
    try:
        assignment.full_clean(validate_unique=False, validate_constraints=False)
    except ValidationError as exc:
        raise AnalyticsValidationError(str(exc)) from exc
    if update_fields is None:
        assignment.save()
    else:
        assignment.save(update_fields=[*update_fields, "updated_at"])
    return assignment


def _require_nonblank(value: str, *, field_name: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise AnalyticsValidationError(f"{field_name} is required.")
    return normalized


def _locked_signal(signal: Signal) -> Signal:
    return (
        Signal.objects.select_for_update()
        .select_related("establishment", "establishment__organization")
        .get(pk=signal.pk)
    )


def _get_or_create_assignment_for_locked_signal(
    locked_signal: Signal,
) -> SignalPatternAssignment:
    assignment = (
        SignalPatternAssignment.objects.select_for_update()
        .filter(signal=locked_signal)
        .first()
    )
    if assignment is not None:
        assignment.signal = locked_signal
        return assignment

    assignment = SignalPatternAssignment(signal=locked_signal)
    return _validate_and_save_assignment(assignment)


def _get_or_create_locked_assignment(signal: Signal) -> SignalPatternAssignment:
    return _get_or_create_assignment_for_locked_signal(_locked_signal(signal))


def _require_expected_processing_attempt(
    assignment: SignalPatternAssignment,
    *,
    expected_attempt_count: int,
) -> None:
    if (
        assignment.classification_status
        != SignalPatternAssignment.ClassificationStatus.PROCESSING
    ):
        raise AnalyticsValidationError(
            "Assignment is not processing.",
            code="analytics_assignment_not_processing",
        )
    if assignment.attempt_count != expected_attempt_count:
        raise AnalyticsValidationError(
            "Assignment attempt is obsolete.",
            code="analytics_assignment_obsolete_attempt",
        )


def _require_current_processing_attempt(
    assignment: SignalPatternAssignment,
    *,
    expected_attempt_count: int,
    pending_signature: str,
    pending_classifier_version: str,
) -> None:
    _require_expected_processing_attempt(
        assignment,
        expected_attempt_count=expected_attempt_count,
    )
    if (
        assignment.pending_signature != pending_signature
        or assignment.pending_classifier_version != pending_classifier_version
    ):
        raise AnalyticsValidationError(
            "Assignment attempt is obsolete.",
            code="analytics_assignment_obsolete_attempt",
        )


def _mark_locked_assignment_succeeded(
    *,
    assignment: SignalPatternAssignment,
    pattern: OperationalPattern,
    assigned_signature: str,
    assigned_classifier_version: str,
    assigned_at=None,
) -> SignalPatternAssignment:
    occurred_at = assigned_at or timezone.now()
    assignment.classification_status = SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    assignment.pattern = pattern
    assignment.assigned_signature = _require_nonblank(
        assigned_signature,
        field_name="assigned_signature",
    )
    assignment.assigned_classifier_version = _require_nonblank(
        assigned_classifier_version,
        field_name="assigned_classifier_version",
    )
    assignment.assigned_at = occurred_at
    assignment.pending_signature = ""
    assignment.pending_classifier_version = ""
    assignment.last_error_code = ""
    assignment.last_attempted_at = occurred_at
    assignment.next_retry_at = None
    return _validate_and_save_assignment(
        assignment,
        update_fields=[
            "classification_status",
            "pattern",
            "assigned_signature",
            "assigned_classifier_version",
            "assigned_at",
            "pending_signature",
            "pending_classifier_version",
            "last_error_code",
            "last_attempted_at",
            "next_retry_at",
        ],
    )


@transaction.atomic
def get_or_create_assignment_for_signal(signal: Signal) -> SignalPatternAssignment:
    return _get_or_create_locked_assignment(signal)


@transaction.atomic
def mark_assignment_processing(
    *,
    signal: Signal,
    pending_signature: str,
    pending_classifier_version: str,
) -> SignalPatternAssignment:
    assignment = _get_or_create_locked_assignment(signal)
    if assignment.classification_status == SignalPatternAssignment.ClassificationStatus.PROCESSING:
        raise AnalyticsValidationError(
            "Assignment is already processing.",
            code="analytics_assignment_already_processing",
        )

    now = timezone.now()
    assignment.classification_status = SignalPatternAssignment.ClassificationStatus.PROCESSING
    assignment.pending_signature = _require_nonblank(
        pending_signature,
        field_name="pending_signature",
    )
    assignment.pending_classifier_version = _require_nonblank(
        pending_classifier_version,
        field_name="pending_classifier_version",
    )
    assignment.attempt_count += 1
    assignment.last_error_code = ""
    assignment.last_attempted_at = now
    assignment.next_retry_at = None
    return _validate_and_save_assignment(
        assignment,
        update_fields=[
            "classification_status",
            "pending_signature",
            "pending_classifier_version",
            "attempt_count",
            "last_error_code",
            "last_attempted_at",
            "next_retry_at",
        ],
    )


@transaction.atomic
def mark_assignment_succeeded(
    *,
    signal: Signal,
    pattern: OperationalPattern,
    assigned_signature: str,
    assigned_classifier_version: str,
    expected_attempt_count: int,
    assigned_at=None,
) -> SignalPatternAssignment:
    assignment = _get_or_create_locked_assignment(signal)
    _require_expected_processing_attempt(
        assignment,
        expected_attempt_count=expected_attempt_count,
    )
    occurred_at = assigned_at or timezone.now()
    assignment.classification_status = SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    assignment.pattern = pattern
    assignment.assigned_signature = _require_nonblank(
        assigned_signature,
        field_name="assigned_signature",
    )
    assignment.assigned_classifier_version = _require_nonblank(
        assigned_classifier_version,
        field_name="assigned_classifier_version",
    )
    assignment.assigned_at = occurred_at
    assignment.pending_signature = ""
    assignment.pending_classifier_version = ""
    assignment.last_error_code = ""
    assignment.last_attempted_at = occurred_at
    assignment.next_retry_at = None
    return _validate_and_save_assignment(
        assignment,
        update_fields=[
            "classification_status",
            "pattern",
            "assigned_signature",
            "assigned_classifier_version",
            "assigned_at",
            "pending_signature",
            "pending_classifier_version",
            "last_error_code",
            "last_attempted_at",
            "next_retry_at",
        ],
    )


def _mark_assignment_failed(
    *,
    signal: Signal,
    status: str,
    error_code: str,
    expected_attempt_count: int,
    pending_signature: str = "",
    pending_classifier_version: str = "",
    next_retry_at=None,
) -> SignalPatternAssignment:
    assignment = _get_or_create_locked_assignment(signal)
    _require_expected_processing_attempt(
        assignment,
        expected_attempt_count=expected_attempt_count,
    )

    assignment.classification_status = status
    assignment.last_error_code = _require_nonblank(
        error_code,
        field_name="error_code",
    )
    if pending_signature:
        assignment.pending_signature = pending_signature.strip()
    if pending_classifier_version:
        assignment.pending_classifier_version = pending_classifier_version.strip()
    assignment.next_retry_at = next_retry_at
    return _validate_and_save_assignment(
        assignment,
        update_fields=[
            "classification_status",
            "pending_signature",
            "pending_classifier_version",
            "last_error_code",
            "next_retry_at",
        ],
    )


@transaction.atomic
def mark_assignment_temporary_failed(
    *,
    signal: Signal,
    error_code: str,
    expected_attempt_count: int,
    pending_signature: str = "",
    pending_classifier_version: str = "",
    next_retry_at=None,
) -> SignalPatternAssignment:
    return _mark_assignment_failed(
        signal=signal,
        status=SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED,
        error_code=error_code,
        expected_attempt_count=expected_attempt_count,
        pending_signature=pending_signature,
        pending_classifier_version=pending_classifier_version,
        next_retry_at=next_retry_at,
    )


@transaction.atomic
def mark_assignment_permanently_failed(
    *,
    signal: Signal,
    error_code: str,
    expected_attempt_count: int,
    pending_signature: str = "",
    pending_classifier_version: str = "",
) -> SignalPatternAssignment:
    return _mark_assignment_failed(
        signal=signal,
        status=SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED,
        error_code=error_code,
        expected_attempt_count=expected_attempt_count,
        pending_signature=pending_signature,
        pending_classifier_version=pending_classifier_version,
    )


def finalize_retryable_pattern_classification_error(
    *,
    signal: Signal,
    exc: PatternClassificationRetryableError,
    retries: int,
    max_retries: int,
    retry_delay_seconds: int,
) -> PatternClassificationRetryFinalization:
    if retries < max_retries:
        assignment = mark_assignment_temporary_failed(
            signal=signal,
            error_code=exc.error_code,
            expected_attempt_count=exc.attempt_count,
            pending_signature=exc.pending_signature,
            pending_classifier_version=exc.pending_classifier_version,
            next_retry_at=timezone.now() + timedelta(seconds=retry_delay_seconds),
        )
        return PatternClassificationRetryFinalization(
            outcome="retry",
            assignment=assignment,
        )

    assignment = mark_assignment_permanently_failed(
        signal=signal,
        error_code="retry_exhausted",
        expected_attempt_count=exc.attempt_count,
        pending_signature=exc.pending_signature,
        pending_classifier_version=exc.pending_classifier_version,
    )
    return PatternClassificationRetryFinalization(
        outcome="retry_exhausted",
        assignment=assignment,
    )


@transaction.atomic
def claim_signal_pattern_classification(
    *,
    signal: Signal,
    signature: str,
    classifier_version: str,
) -> PatternClassificationClaimResult:
    locked_signal = _locked_signal(signal)
    assignment = _get_or_create_assignment_for_locked_signal(locked_signal)
    signature = _require_nonblank(signature, field_name="signature")
    classifier_version = _require_nonblank(
        classifier_version,
        field_name="classifier_version",
    )

    if (
        assignment.pattern_id is not None
        and assignment.assigned_signature == signature
        and assignment.assigned_classifier_version == classifier_version
    ):
        return PatternClassificationClaimResult(
            status="already_succeeded",
            attempt_count=None,
            assignment=assignment,
        )

    now = timezone.now()
    if (
        assignment.classification_status
        == SignalPatternAssignment.ClassificationStatus.PROCESSING
        and assignment.pending_signature == signature
        and assignment.pending_classifier_version == classifier_version
        and assignment.last_attempted_at is not None
        and assignment.last_attempted_at
        > now - timedelta(seconds=settings.HOUSTON_ANALYTICS_PATTERN_PROCESSING_STALE_SECONDS)
    ):
        return PatternClassificationClaimResult(
            status="already_processing",
            attempt_count=assignment.attempt_count,
            assignment=assignment,
        )

    assignment.classification_status = SignalPatternAssignment.ClassificationStatus.PROCESSING
    assignment.pending_signature = signature
    assignment.pending_classifier_version = classifier_version
    assignment.attempt_count += 1
    assignment.last_error_code = ""
    assignment.last_attempted_at = now
    assignment.next_retry_at = None
    assignment = _validate_and_save_assignment(
        assignment,
        update_fields=[
            "classification_status",
            "pending_signature",
            "pending_classifier_version",
            "attempt_count",
            "last_error_code",
            "last_attempted_at",
            "next_retry_at",
        ],
    )
    return PatternClassificationClaimResult(
        status="claimed",
        attempt_count=assignment.attempt_count,
        assignment=assignment,
    )


def classify_signal_pattern(
    signal_id: uuid.UUID,
    *,
    provider: PatternClassifierProvider | None = None,
    duplicate_guard_enabled: bool = True,
) -> SignalPatternAssignment | None:
    signal = _load_signal_for_pattern_classification(signal_id)
    if signal is None:
        return None
    if signal.merged_into_id is not None:
        return None

    provider = provider or get_pattern_classifier_provider()
    signature = build_signal_pattern_signature(signal)
    classifier_version = classifier_version_for_provider(provider)
    claim = claim_signal_pattern_classification(
        signal=signal,
        signature=signature,
        classifier_version=classifier_version,
    )
    if claim.status != "claimed":
        return claim.assignment

    assert claim.attempt_count is not None
    candidates = _active_pattern_candidates(signal)
    input_payload = {
        "schema_version": ANALYTICS_PATTERN_SCHEMA_VERSION,
        "prompt_version": ANALYTICS_PATTERN_PROMPT_VERSION,
        **build_signal_pattern_payload(signal),
        "active_patterns": candidates,
    }

    provider_started_at = time.monotonic()
    try:
        provider_response = provider.classify(input_payload=input_payload)
        parsed = parse_pattern_classifier_response(provider_response.payload)
        resolution = _prepare_classifier_pattern_resolution(
            signal=signal,
            response=parsed,
            candidates=candidates,
            provider=provider,
            duplicate_guard_enabled=duplicate_guard_enabled,
        )
        assignment = _finalize_pattern_classification_success(
            signal=signal,
            resolution=resolution,
            assigned_signature=signature,
            assigned_classifier_version=classifier_version,
            expected_attempt_count=claim.attempt_count,
        )
        setattr(
            assignment,
            "_analytics_duplicate_guard_decision",
            resolution.duplicate_guard_decision.action,
        )
        _write_analytics_usage_log(
            signal=signal,
            provider=provider.provider,
            model=provider_response.model or getattr(provider, "model", ""),
            status=AIUsageLog.Status.SUCCEEDED,
            latency_ms=_elapsed_ms(provider_started_at),
            correlation_id=uuid.uuid4(),
            input_tokens=provider_response.input_tokens,
            output_tokens=provider_response.output_tokens,
            total_tokens=provider_response.total_tokens,
        )
        return assignment
    except PatternClassificationObsoleteAttempt as exc:
        return exc.assignment
    except (PatternClassifierTimeoutError, PatternClassifierUnavailableError) as exc:
        _write_analytics_usage_log(
            signal=signal,
            provider=provider.provider,
            model=getattr(provider, "model", ""),
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(provider_started_at),
            correlation_id=uuid.uuid4(),
            error_code=exc.error_code,
        )
        raise PatternClassificationRetryableError(
            str(exc),
            signal_id=signal.id,
            attempt_count=claim.attempt_count,
            pending_signature=signature,
            pending_classifier_version=classifier_version,
            error_code=exc.error_code,
        ) from exc
    except (PatternClassifierError, AnalyticsValidationError) as exc:
        error_code = getattr(exc, "error_code", None) or getattr(exc, "code", None)
        error_code = error_code or "pattern_classification_permanent_error"
        mark_assignment_permanently_failed(
            signal=signal,
            error_code=error_code,
            expected_attempt_count=claim.attempt_count,
            pending_signature=signature,
            pending_classifier_version=classifier_version,
        )
        _write_analytics_usage_log(
            signal=signal,
            provider=provider.provider,
            model=getattr(provider, "model", ""),
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(provider_started_at),
            correlation_id=uuid.uuid4(),
            error_code=error_code,
        )
        return SignalPatternAssignment.objects.get(signal=signal)


def _load_signal_for_pattern_classification(signal_id: uuid.UUID) -> Signal | None:
    return (
        Signal.objects.select_related(
            "establishment",
            "establishment__organization",
            "affected_business_unit",
            "responsible_business_unit",
            "activity_subject",
            "operational_unit",
            "merged_into",
        )
        .filter(pk=signal_id)
        .first()
    )


def _active_pattern_candidates(signal: Signal) -> list[dict[str, str]]:
    return [
        {
            "id": str(pattern.id),
            "label": pattern.label,
            "normalized_label": pattern.normalized_label,
        }
        for pattern in OperationalPattern.objects.filter(
            organization=signal.establishment.organization,
            status=OperationalPattern.Status.ACTIVE,
        ).order_by("label", "id")
    ]


def _prepare_classifier_pattern_resolution(
    *,
    signal: Signal,
    response,
    candidates: list[dict[str, str]],
    provider: PatternClassifierProvider,
    duplicate_guard_enabled: bool,
) -> PatternClassifierPatternResolution:
    if response.result_type == "existing_pattern":
        candidate_ids = {uuid.UUID(candidate["id"]) for candidate in candidates}
        if response.pattern_id not in candidate_ids:
            raise PatternClassifierInvalidOutputError(
                "Classifier selected a pattern outside active candidates.",
            )
        return PatternClassifierPatternResolution(
            mode="existing_pattern",
            pattern_id=response.pattern_id,
        )

    label = _validate_new_pattern_label(signal=signal, label=response.canonical_label)
    normalized = normalize_pattern_label(label)
    strict_duplicate = _find_active_pattern_by_normalized_label(
        signal=signal,
        normalized_label=normalized,
    )
    if strict_duplicate is not None:
        return PatternClassifierPatternResolution(
            mode="reuse_pattern",
            label=label,
            pattern_id=strict_duplicate.id,
            duplicate_guard_decision=PatternDuplicateGuardDecision(
                action="skipped",
                pattern_id=strict_duplicate.id,
                reason="strict_duplicate",
            ),
        )

    shortlist = (
        _duplicate_guard_shortlist(signal=signal, canonical_label=label)
        if duplicate_guard_enabled
        else []
    )
    if not shortlist:
        return PatternClassifierPatternResolution(
            mode="create_pattern",
            label=label,
            duplicate_guard_decision=PatternDuplicateGuardDecision(
                action="skipped",
                reason="no_candidates" if duplicate_guard_enabled else "disabled",
            ),
        )

    decision = _assess_duplicate_guard_best_effort(
        signal=signal,
        provider=provider,
        canonical_label=label,
        shortlist=shortlist,
    )
    if decision.action == "reused" and decision.pattern_id is not None:
        return PatternClassifierPatternResolution(
            mode="reuse_pattern",
            label=label,
            pattern_id=decision.pattern_id,
            duplicate_guard_decision=decision,
        )

    return PatternClassifierPatternResolution(
        mode="create_pattern",
        label=label,
        duplicate_guard_decision=decision,
    )


def _finalize_pattern_classification_success(
    *,
    signal: Signal,
    resolution: PatternClassifierPatternResolution,
    assigned_signature: str,
    assigned_classifier_version: str,
    expected_attempt_count: int,
) -> SignalPatternAssignment:
    try:
        with transaction.atomic():
            locked_signal = _locked_signal(signal)
            assignment = _get_or_create_assignment_for_locked_signal(locked_signal)
            _require_current_processing_attempt(
                assignment,
                expected_attempt_count=expected_attempt_count,
                pending_signature=assigned_signature,
                pending_classifier_version=assigned_classifier_version,
            )
            pattern = _resolve_pattern_resolution_for_write(
                signal=locked_signal,
                resolution=resolution,
            )
            assignment = _mark_locked_assignment_succeeded(
                assignment=assignment,
                pattern=pattern,
                assigned_signature=assigned_signature,
                assigned_classifier_version=assigned_classifier_version,
            )
            return assignment
    except AnalyticsValidationError as exc:
        if getattr(exc, "code", None) == "analytics_assignment_obsolete_attempt":
            assignment = SignalPatternAssignment.objects.get(signal=signal)
            raise PatternClassificationObsoleteAttempt(assignment) from exc
        raise


def _resolve_pattern_resolution_for_write(
    *,
    signal: Signal,
    resolution: PatternClassifierPatternResolution,
) -> OperationalPattern:
    if resolution.mode == "existing_pattern":
        if resolution.pattern_id is None:
            raise PatternClassifierInvalidOutputError("Pattern resolution missing target.")
        pattern = OperationalPattern.objects.select_for_update().get(
            pk=resolution.pattern_id
        )
        return _resolve_active_pattern_target(signal=signal, pattern=pattern)

    if resolution.mode == "reuse_pattern":
        if resolution.pattern_id is not None:
            try:
                pattern = OperationalPattern.objects.select_for_update().get(
                    pk=resolution.pattern_id
                )
            except OperationalPattern.DoesNotExist:
                pattern = None
            if pattern is None:
                return _get_or_create_active_pattern_for_label(
                    signal=signal,
                    label=resolution.label,
                )
            try:
                return _resolve_active_pattern_target(signal=signal, pattern=pattern)
            except PatternClassifierInvalidOutputError:
                pass

    return _get_or_create_active_pattern_for_label(signal=signal, label=resolution.label)


def _find_active_pattern_by_normalized_label(
    *,
    signal: Signal,
    normalized_label: str,
) -> OperationalPattern | None:
    return (
        OperationalPattern.objects.filter(
            organization=signal.establishment.organization,
            normalized_label=normalized_label,
            status=OperationalPattern.Status.ACTIVE,
        )
        .order_by("normalized_label", "label")
        .first()
    )


def _duplicate_guard_shortlist(
    *,
    signal: Signal,
    canonical_label: str,
) -> list[PatternDuplicateGuardCandidate]:
    min_score = settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE
    max_candidates = settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MAX_CANDIDATES
    if max_candidates <= 0:
        return []

    source_tokens = _duplicate_guard_source_tokens(
        signal=signal,
        canonical_label=canonical_label,
    )
    if not source_tokens:
        return []

    candidates: list[PatternDuplicateGuardCandidate] = []
    for pattern in OperationalPattern.objects.filter(
        organization=signal.establishment.organization,
        status=OperationalPattern.Status.ACTIVE,
    ):
        candidate_tokens = _normalized_tokens(pattern.label)
        if not candidate_tokens:
            continue
        score = len(source_tokens & candidate_tokens) / len(candidate_tokens)
        if score >= min_score:
            candidates.append(
                PatternDuplicateGuardCandidate(
                    id=pattern.id,
                    label=pattern.label,
                    normalized_label=pattern.normalized_label,
                    score=score,
                )
            )

    candidates.sort(
        key=lambda candidate: (
            -candidate.score,
            candidate.normalized_label,
            candidate.label,
        )
    )
    return candidates[:max_candidates]


def _duplicate_guard_source_tokens(
    *,
    signal: Signal,
    canonical_label: str,
) -> set[str]:
    activity_subject = signal.activity_subject.label if signal.activity_subject_id else ""
    operational_unit = signal.operational_unit.label if signal.operational_unit_id else ""
    return _normalized_tokens(
        " ".join(
            [
                canonical_label,
                signal.title,
                signal.structured_summary,
                signal.issue_focus,
                activity_subject,
                operational_unit,
            ]
        )
    )


def _normalized_tokens(value: str) -> set[str]:
    return {
        token
        for token in normalize_pattern_label(value).split()
        if len(token) >= 3
    }


def _assess_duplicate_guard_best_effort(
    *,
    signal: Signal,
    provider: PatternClassifierProvider,
    canonical_label: str,
    shortlist: list[PatternDuplicateGuardCandidate],
) -> PatternDuplicateGuardDecision:
    shortlist_ids = {candidate.id for candidate in shortlist}
    input_payload = {
        "schema_version": ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
        "prompt_version": ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
        "signal": _duplicate_guard_signal_payload(signal),
        "canonical_label": canonical_label,
        "candidate_patterns": [
            {
                "id": str(candidate.id),
                "label": candidate.label,
                "normalized_label": candidate.normalized_label,
            }
            for candidate in shortlist
        ],
    }

    started_at = time.monotonic()
    try:
        response = provider.assess_duplicate(input_payload=input_payload)
        parsed = parse_pattern_duplicate_guard_response(response.payload)
        if parsed.result_type == "reuse_existing_pattern":
            if parsed.pattern_id not in shortlist_ids:
                _write_duplicate_guard_usage_log(
                    signal=signal,
                    provider=provider.provider,
                    model=response.model or getattr(provider, "model", ""),
                    status=AIUsageLog.Status.FAILED,
                    latency_ms=_elapsed_ms(started_at),
                    correlation_id=uuid.uuid4(),
                    error_code="duplicate_guard_pattern_outside_shortlist",
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    total_tokens=response.total_tokens,
                )
                return PatternDuplicateGuardDecision(
                    action="fallback",
                    reason="outside_shortlist",
                )
            _write_duplicate_guard_usage_log(
                signal=signal,
                provider=provider.provider,
                model=response.model or getattr(provider, "model", ""),
                status=AIUsageLog.Status.SUCCEEDED,
                latency_ms=_elapsed_ms(started_at),
                correlation_id=uuid.uuid4(),
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_tokens=response.total_tokens,
            )
            return PatternDuplicateGuardDecision(
                action="reused",
                pattern_id=parsed.pattern_id,
            )

        _write_duplicate_guard_usage_log(
            signal=signal,
            provider=provider.provider,
            model=response.model or getattr(provider, "model", ""),
            status=AIUsageLog.Status.SUCCEEDED,
            latency_ms=_elapsed_ms(started_at),
            correlation_id=uuid.uuid4(),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            total_tokens=response.total_tokens,
        )
        return PatternDuplicateGuardDecision(action="created")
    except PatternClassifierError as exc:
        _write_duplicate_guard_usage_log(
            signal=signal,
            provider=provider.provider,
            model=getattr(provider, "model", ""),
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(started_at),
            correlation_id=uuid.uuid4(),
            error_code=getattr(exc, "error_code", "duplicate_guard_error"),
        )
        return PatternDuplicateGuardDecision(
            action="fallback",
            reason=getattr(exc, "error_code", "duplicate_guard_error"),
        )


def _duplicate_guard_signal_payload(signal: Signal) -> dict[str, Any]:
    activity_subject = signal.activity_subject.label if signal.activity_subject_id else ""
    operational_unit = signal.operational_unit.label if signal.operational_unit_id else ""
    return {
        "title": signal.title,
        "structured_summary": signal.structured_summary,
        "issue_focus": signal.issue_focus,
        "activity_subject": activity_subject,
        "operational_unit": operational_unit,
    }


def _resolve_active_pattern_target(
    *,
    signal: Signal,
    pattern: OperationalPattern,
) -> OperationalPattern:
    if (
        pattern.organization_id == signal.establishment.organization_id
        and pattern.status == OperationalPattern.Status.ACTIVE
    ):
        return pattern

    if pattern.status == OperationalPattern.Status.MERGED:
        target = _resolve_merged_pattern_chain(signal=signal, pattern=pattern)
        if target is not None:
            return target

    active = (
        OperationalPattern.objects.select_for_update()
        .filter(
            organization=signal.establishment.organization,
            normalized_label=pattern.normalized_label,
            status=OperationalPattern.Status.ACTIVE,
        )
        .first()
    )
    if active is not None:
        return active

    raise PatternClassifierInvalidOutputError("No active target pattern could be resolved.")


def _resolve_merged_pattern_chain(
    *,
    signal: Signal,
    pattern: OperationalPattern,
) -> OperationalPattern | None:
    seen = {pattern.id}
    current = pattern
    for _ in range(5):
        if current.merged_into_id is None:
            return None
        target = OperationalPattern.objects.select_for_update().get(pk=current.merged_into_id)
        if target.id in seen:
            return None
        seen.add(target.id)
        if target.organization_id != signal.establishment.organization_id:
            return None
        if target.status == OperationalPattern.Status.ACTIVE:
            return target
        if target.status != OperationalPattern.Status.MERGED:
            return None
        current = target
    return None


def _validate_new_pattern_label(*, signal: Signal, label: str) -> str:
    normalized = normalize_pattern_label(label)
    if not normalized:
        raise PatternClassifierInvalidOutputError("New pattern label is empty.")
    cleaned = label.strip()
    if len(cleaned) > PATTERN_LABEL_MAX_LENGTH:
        raise PatternClassifierInvalidOutputError("New pattern label is too long.")
    if normalized == normalize_pattern_label(signal.title):
        raise PatternClassifierInvalidOutputError("New pattern label copies the signal title.")

    forbidden_labels = [signal.establishment.name]
    for business_unit in (
        signal.affected_business_unit,
        signal.responsible_business_unit,
    ):
        if business_unit is not None and business_unit.specific_name:
            forbidden_labels.append(business_unit.specific_name)
    for forbidden_label in forbidden_labels:
        forbidden = normalize_pattern_label(forbidden_label)
        if forbidden and forbidden in normalized:
            raise PatternClassifierInvalidOutputError(
                "New pattern label includes establishment or business unit context."
            )

    return cleaned


def _get_or_create_active_pattern_for_label(
    *,
    signal: Signal,
    label: str,
) -> OperationalPattern:
    normalized = normalize_pattern_label(label)
    try:
        with transaction.atomic():
            return create_operational_pattern(
                organization=signal.establishment.organization,
                label=label,
            )
    except IntegrityError:
        pattern = (
            OperationalPattern.objects.filter(
                organization=signal.establishment.organization,
                normalized_label=normalized,
                status=OperationalPattern.Status.ACTIVE,
            )
            .order_by("id")
            .first()
        )
        if pattern is not None:
            return pattern
        raise PatternClassifierInvalidOutputError("Concurrent pattern creation lost target.")


def _write_analytics_usage_log(
    *,
    signal: Signal,
    provider: str,
    model: str,
    status: str,
    latency_ms: int,
    correlation_id: uuid.UUID,
    error_code: str = "",
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
) -> None:
    AIUsageLog.objects.create(
        ai_domain=AIUsageLog.Domain.ANALYTICS_PATTERN,
        provider=provider,
        model=model or "",
        prompt_version=ANALYTICS_PATTERN_PROMPT_VERSION,
        schema_version=ANALYTICS_PATTERN_SCHEMA_VERSION,
        status=status,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        error_code=error_code,
        error_context={},
        correlation_id=correlation_id,
        establishment=signal.establishment,
    )


def _write_duplicate_guard_usage_log(
    *,
    signal: Signal,
    provider: str,
    model: str,
    status: str,
    latency_ms: int,
    correlation_id: uuid.UUID,
    error_code: str = "",
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_tokens: int | None = None,
) -> None:
    AIUsageLog.objects.create(
        ai_domain=AIUsageLog.Domain.ANALYTICS_PATTERN,
        provider=provider,
        model=model or "",
        prompt_version=ANALYTICS_PATTERN_DUPLICATE_GUARD_PROMPT_VERSION,
        schema_version=ANALYTICS_PATTERN_DUPLICATE_GUARD_SCHEMA_VERSION,
        status=status,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        error_code=error_code,
        error_context={"phase": "analytics_pattern_duplicate_guard"},
        correlation_id=correlation_id,
        establishment=signal.establishment,
    )


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)
