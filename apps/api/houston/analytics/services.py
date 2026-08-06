from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import (
    OperationalPattern,
    PatternLifecycleEvent,
    SignalPatternAssignment,
)
from houston.establishments.models import EstablishmentMembership
from houston.organizations.models import Organization
from houston.signals.models import Signal


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
        .select_related("establishment")
        .get(pk=signal.pk)
    )


def _get_or_create_locked_assignment(signal: Signal) -> SignalPatternAssignment:
    locked_signal = _locked_signal(signal)
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
    assigned_at=None,
) -> SignalPatternAssignment:
    assignment = _get_or_create_locked_assignment(signal)
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
    pending_signature: str = "",
    pending_classifier_version: str = "",
    next_retry_at=None,
) -> SignalPatternAssignment:
    assignment = _get_or_create_locked_assignment(signal)
    if assignment.classification_status != SignalPatternAssignment.ClassificationStatus.PROCESSING:
        raise AnalyticsValidationError(
            "Assignment is not processing.",
            code="analytics_assignment_not_processing",
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
    pending_signature: str = "",
    pending_classifier_version: str = "",
    next_retry_at=None,
) -> SignalPatternAssignment:
    return _mark_assignment_failed(
        signal=signal,
        status=SignalPatternAssignment.ClassificationStatus.TEMPORARY_FAILED,
        error_code=error_code,
        pending_signature=pending_signature,
        pending_classifier_version=pending_classifier_version,
        next_retry_at=next_retry_at,
    )


@transaction.atomic
def mark_assignment_permanently_failed(
    *,
    signal: Signal,
    error_code: str,
    pending_signature: str = "",
    pending_classifier_version: str = "",
) -> SignalPatternAssignment:
    return _mark_assignment_failed(
        signal=signal,
        status=SignalPatternAssignment.ClassificationStatus.PERMANENTLY_FAILED,
        error_code=error_code,
        pending_signature=pending_signature,
        pending_classifier_version=pending_classifier_version,
    )
