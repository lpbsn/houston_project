from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.ai.models import AIUsageLog
from houston.analytics.classifier import (
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
        with transaction.atomic():
            pattern = _resolve_classifier_pattern(
                signal=signal,
                response=parsed,
                candidates=candidates,
            )
            assignment = mark_assignment_succeeded(
                signal=signal,
                pattern=pattern,
                assigned_signature=signature,
                assigned_classifier_version=classifier_version,
                expected_attempt_count=claim.attempt_count,
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


def _resolve_classifier_pattern(
    *,
    signal: Signal,
    response,
    candidates: list[dict[str, str]],
) -> OperationalPattern:
    if response.result_type == "existing_pattern":
        candidate_ids = {uuid.UUID(candidate["id"]) for candidate in candidates}
        if response.pattern_id not in candidate_ids:
            raise PatternClassifierInvalidOutputError(
                "Classifier selected a pattern outside active candidates.",
            )
        pattern = OperationalPattern.objects.select_for_update().get(pk=response.pattern_id)
        return _resolve_active_pattern_target(signal=signal, pattern=pattern)

    label = _validate_new_pattern_label(signal=signal, label=response.canonical_label)
    return _get_or_create_active_pattern_for_label(signal=signal, label=label)


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

    if pattern.status == OperationalPattern.Status.MERGED and pattern.merged_into_id is not None:
        target = OperationalPattern.objects.select_for_update().get(pk=pattern.merged_into_id)
        if (
            target.organization_id == signal.establishment.organization_id
            and target.status == OperationalPattern.Status.ACTIVE
        ):
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


def _elapsed_ms(started_at: float) -> int:
    return int((time.monotonic() - started_at) * 1000)
