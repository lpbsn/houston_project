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
from houston.analytics.permissions import (
    can_correct_operational_patterns,
    can_correct_signal_pattern_assignment,
)
from houston.analytics.signature import (
    build_signal_pattern_payload,
    build_signal_pattern_signature,
)
from houston.establishments.models import EstablishmentMembership
from houston.organizations.models import Organization
from houston.signals.models import Signal

DUPLICATE_GUARD_SHORTLIST_STRATEGY = "token_overlap_v1"
OWNER_CORRECTION_CLASSIFIER_VERSION = "owner_correction_v1"
OWNER_CORRECTION_LOCK_ORDER = (
    "Analytics classification locks Signal, then SignalPatternAssignment, then "
    "OperationalPattern. Owner merge/move services use the same order."
)


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
    reason: str = ""


@dataclass(frozen=True)
class PatternClassificationRetryFinalization:
    outcome: str
    assignment: SignalPatternAssignment


@dataclass(frozen=True)
class OwnerPatternMoveResult:
    moved_assignments: tuple[SignalPatternAssignment, ...]
    moved_signal_ids: tuple[str, ...]


@dataclass(frozen=True)
class PatternSplitResult:
    source_pattern: OperationalPattern
    target_pattern: OperationalPattern | None
    target_created: bool
    moved_assignments: tuple[SignalPatternAssignment, ...]
    correction_id: str


class PatternClassificationObsoleteAttempt(Exception):
    def __init__(self, assignment: SignalPatternAssignment):
        super().__init__("Analytics pattern classification attempt is obsolete.")
        self.assignment = assignment


def _is_obsolete_assignment_error(exc: AnalyticsValidationError) -> bool:
    return getattr(exc, "code", None) in {
        "analytics_assignment_obsolete_attempt",
        "analytics_assignment_not_processing",
    }


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


@transaction.atomic
def rename_operational_pattern(
    *,
    actor_membership: EstablishmentMembership,
    pattern: OperationalPattern,
    label: str,
    occurred_at=None,
) -> OperationalPattern:
    occurred_at = occurred_at or timezone.now()
    locked_pattern = OperationalPattern.objects.select_for_update().get(pk=pattern.pk)
    _require_owner_correction_permission(
        actor_membership=actor_membership,
        organization=locked_pattern.organization,
    )
    if locked_pattern.status != OperationalPattern.Status.ACTIVE:
        raise AnalyticsValidationError(
            "Only active patterns can be renamed.",
            code="analytics_pattern_not_active",
        )
    if locked_pattern.label == label:
        return locked_pattern

    old_label = locked_pattern.label
    old_normalized_label = locked_pattern.normalized_label
    new_normalized_label = normalize_pattern_label(label)
    if not new_normalized_label:
        raise AnalyticsValidationError(
            "Pattern label cannot be blank.",
            code="analytics_pattern_label_blank",
        )
    if (
        OperationalPattern.objects.filter(
            organization=locked_pattern.organization,
            normalized_label=new_normalized_label,
            status=OperationalPattern.Status.ACTIVE,
        )
        .exclude(pk=locked_pattern.pk)
        .exists()
    ):
        raise AnalyticsValidationError(
            "An active pattern with this normalized label already exists.",
            code="analytics_pattern_label_conflict",
        )

    locked_pattern.label = label
    try:
        locked_pattern.full_clean(validate_unique=False, validate_constraints=False)
        with transaction.atomic():
            locked_pattern.save(update_fields=["label", "updated_at"])
    except IntegrityError as exc:
        raise AnalyticsValidationError(
            "An active pattern with this normalized label already exists.",
            code="analytics_pattern_label_conflict",
        ) from exc
    except ValidationError as exc:
        raise AnalyticsValidationError(str(exc)) from exc

    _create_pattern_event(
        pattern=locked_pattern,
        event_type=PatternLifecycleEvent.EventType.RENAMED,
        actor_membership=actor_membership,
        occurred_at=occurred_at,
        metadata_safe={
            "old_label": old_label,
            "old_normalized_label": old_normalized_label,
            "new_label": locked_pattern.label,
            "new_normalized_label": locked_pattern.normalized_label,
        },
    )
    return locked_pattern


def merge_operational_patterns(
    *,
    actor_membership: EstablishmentMembership,
    source_pattern: OperationalPattern,
    target_pattern: OperationalPattern,
    occurred_at=None,
) -> OperationalPattern:
    occurred_at = occurred_at or timezone.now()
    prechecked = _terminal_merge_precheck(
        actor_membership=actor_membership,
        source_pattern=source_pattern,
        target_pattern=target_pattern,
    )
    if prechecked is not None:
        return prechecked

    source_id = source_pattern.id
    target_id = target_pattern.id
    candidate_signal_ids = list(
        SignalPatternAssignment.objects.filter(pattern_id=source_id)
        .order_by("signal_id")
        .values_list("signal_id", flat=True)
    )

    with transaction.atomic():
        locked_signals = _lock_signals_for_owner_correction(candidate_signal_ids)
        assignments = _lock_assignments_for_signals(candidate_signal_ids)
        patterns = _lock_patterns_for_owner_correction([source_id, target_id])
        source = patterns[source_id]
        target = patterns[target_id]
        _require_owner_correction_permission(
            actor_membership=actor_membership,
            organization=source.organization,
        )
        _require_new_merge_patterns(source=source, target=target)

        assignment_by_signal_id = {assignment.signal_id: assignment for assignment in assignments}
        if set(assignment_by_signal_id) != set(candidate_signal_ids):
            raise AnalyticsValidationError(
                "Source assignments changed during merge.",
                code="analytics_pattern_merge_concurrent_change",
            )
        if any(assignment.pattern_id != source.id for assignment in assignments):
            raise AnalyticsValidationError(
                "Source assignments changed during merge.",
                code="analytics_pattern_merge_concurrent_change",
            )

        current_source_signal_ids = set(
            SignalPatternAssignment.objects.filter(pattern_id=source.id).values_list(
                "signal_id",
                flat=True,
            )
        )
        if current_source_signal_ids != set(candidate_signal_ids):
            raise AnalyticsValidationError(
                "Source assignments changed during merge.",
                code="analytics_pattern_merge_concurrent_change",
            )

        moved_signal_ids: list[str] = []
        signatures = {
            signal.id: build_signal_pattern_signature(signal)
            for signal in locked_signals
        }
        for assignment in assignments:
            signal = next(signal for signal in locked_signals if signal.id == assignment.signal_id)
            if signal.establishment.organization_id != source.organization_id:
                raise AnalyticsValidationError(
                    "Signal belongs to another organization.",
                    code="analytics_signal_wrong_organization",
                )
            _mark_locked_assignment_owner_corrected(
                assignment=assignment,
                signal=signal,
                pattern=target,
                signature=signatures[signal.id],
                occurred_at=occurred_at,
            )
            moved_signal_ids.append(str(signal.id))

        source.status = OperationalPattern.Status.MERGED
        source.merged_into = target
        try:
            source.full_clean(validate_unique=False, validate_constraints=False)
        except ValidationError as exc:
            raise AnalyticsValidationError(str(exc)) from exc
        source.save(update_fields=["status", "merged_into", "updated_at"])

        correction_id = str(uuid.uuid4())
        _create_pattern_event(
            pattern=source,
            event_type=PatternLifecycleEvent.EventType.MERGED,
            actor_membership=actor_membership,
            occurred_at=occurred_at,
            metadata_safe={
                "correction_id": correction_id,
                "source_pattern_id": str(source.id),
                "target_pattern_id": str(target.id),
                "signal_count": len(moved_signal_ids),
            },
        )
        _create_signal_move_events(
            source=source,
            target=target,
            actor_membership=actor_membership,
            occurred_at=occurred_at,
            correction_id=correction_id,
            moved_signal_ids=moved_signal_ids,
        )
        return source


def move_signals_between_patterns(
    *,
    actor_membership: EstablishmentMembership,
    source_pattern: OperationalPattern,
    target_pattern: OperationalPattern,
    signal_ids,
    occurred_at=None,
) -> tuple[SignalPatternAssignment, ...]:
    occurred_at = occurred_at or timezone.now()
    normalized_signal_ids = _normalize_uuid_list(signal_ids)
    if not normalized_signal_ids:
        return ()

    with transaction.atomic():
        locked_signals = _lock_signals_for_owner_correction(normalized_signal_ids)
        if len(locked_signals) != len(normalized_signal_ids):
            raise AnalyticsValidationError(
                "One or more signals were not found.",
                code="analytics_signal_not_found",
            )
        assignments = _lock_assignments_for_signals(normalized_signal_ids)
        patterns = _lock_patterns_for_owner_correction([source_pattern.id, target_pattern.id])
        source = patterns[source_pattern.id]
        target = patterns[target_pattern.id]
        _require_owner_correction_permission(
            actor_membership=actor_membership,
            organization=source.organization,
        )
        _require_active_pattern_pair(source=source, target=target)

        move_result = _move_locked_signal_assignments_for_owner_correction(
            normalized_signal_ids=normalized_signal_ids,
            locked_signals=locked_signals,
            assignments=assignments,
            source=source,
            target=target,
            actor_membership=actor_membership,
            occurred_at=occurred_at,
        )

        if move_result.moved_signal_ids:
            _create_signal_move_events(
                source=source,
                target=target,
                actor_membership=actor_membership,
                occurred_at=occurred_at,
                correction_id=str(uuid.uuid4()),
                moved_signal_ids=list(move_result.moved_signal_ids),
            )
        return move_result.moved_assignments


def split_operational_pattern_to_existing(
    *,
    actor_membership: EstablishmentMembership,
    source_pattern: OperationalPattern,
    target_pattern: OperationalPattern,
    signal_ids,
    occurred_at=None,
) -> PatternSplitResult:
    occurred_at = occurred_at or timezone.now()
    normalized_signal_ids = _normalize_uuid_list(signal_ids)
    if not normalized_signal_ids:
        return PatternSplitResult(
            source_pattern=source_pattern,
            target_pattern=target_pattern,
            target_created=False,
            moved_assignments=(),
            correction_id="",
        )

    with transaction.atomic():
        locked_signals = _lock_signals_for_owner_correction(normalized_signal_ids)
        if len(locked_signals) != len(normalized_signal_ids):
            raise AnalyticsValidationError(
                "One or more signals were not found.",
                code="analytics_signal_not_found",
            )
        assignments = _lock_assignments_for_signals(normalized_signal_ids)
        patterns = _lock_patterns_for_owner_correction([source_pattern.id, target_pattern.id])
        source = patterns[source_pattern.id]
        target = patterns[target_pattern.id]
        _require_owner_correction_permission(
            actor_membership=actor_membership,
            organization=source.organization,
        )
        _require_active_pattern_pair(source=source, target=target)
        move_result = _move_locked_signal_assignments_for_owner_correction(
            normalized_signal_ids=normalized_signal_ids,
            locked_signals=locked_signals,
            assignments=assignments,
            source=source,
            target=target,
            actor_membership=actor_membership,
            occurred_at=occurred_at,
        )
        correction_id = str(uuid.uuid4()) if move_result.moved_signal_ids else ""
        if move_result.moved_signal_ids:
            _create_split_event(
                source=source,
                target=target,
                actor_membership=actor_membership,
                occurred_at=occurred_at,
                correction_id=correction_id,
                target_created=False,
                selected_signal_count=len(normalized_signal_ids),
                moved_signal_count=len(move_result.moved_signal_ids),
            )
            _create_signal_move_events(
                source=source,
                target=target,
                actor_membership=actor_membership,
                occurred_at=occurred_at,
                correction_id=correction_id,
                moved_signal_ids=list(move_result.moved_signal_ids),
            )
        return PatternSplitResult(
            source_pattern=source,
            target_pattern=target,
            target_created=False,
            moved_assignments=move_result.moved_assignments,
            correction_id=correction_id,
        )


def split_operational_pattern_to_new(
    *,
    actor_membership: EstablishmentMembership,
    source_pattern: OperationalPattern,
    label: str,
    signal_ids,
    occurred_at=None,
) -> PatternSplitResult:
    occurred_at = occurred_at or timezone.now()
    normalized_signal_ids = _normalize_uuid_list(signal_ids)
    if not normalized_signal_ids:
        return PatternSplitResult(
            source_pattern=source_pattern,
            target_pattern=None,
            target_created=False,
            moved_assignments=(),
            correction_id="",
        )

    with transaction.atomic():
        locked_signals = _lock_signals_for_owner_correction(normalized_signal_ids)
        if len(locked_signals) != len(normalized_signal_ids):
            raise AnalyticsValidationError(
                "One or more signals were not found.",
                code="analytics_signal_not_found",
            )
        assignments = _lock_assignments_for_signals(normalized_signal_ids)
        patterns = _lock_patterns_for_owner_correction([source_pattern.id])
        source = patterns[source_pattern.id]
        _require_owner_correction_permission(
            actor_membership=actor_membership,
            organization=source.organization,
        )
        if source.status != OperationalPattern.Status.ACTIVE:
            raise AnalyticsValidationError(
                "Source pattern must be active.",
                code="analytics_pattern_source_not_active",
            )
        _require_split_label_available(organization=source.organization, label=label)
        _require_locked_signals_assigned_to_source(
            normalized_signal_ids=normalized_signal_ids,
            locked_signals=locked_signals,
            assignments=assignments,
            source=source,
            actor_membership=actor_membership,
        )

        correction_id = str(uuid.uuid4())
        try:
            with transaction.atomic():
                target = create_operational_pattern(
                    organization=source.organization,
                    label=label,
                    created_by_membership=actor_membership,
                    occurred_at=occurred_at,
                    metadata_safe={
                        "correction_id": correction_id,
                        "created_for_split": True,
                        "split_source_pattern_id": str(source.id),
                    },
                )
        except IntegrityError as exc:
            raise AnalyticsValidationError(
                "An active pattern with this normalized label already exists.",
                code="analytics_pattern_label_conflict",
            ) from exc

        move_result = _move_locked_signal_assignments_for_owner_correction(
            normalized_signal_ids=normalized_signal_ids,
            locked_signals=locked_signals,
            assignments=assignments,
            source=source,
            target=target,
            actor_membership=actor_membership,
            occurred_at=occurred_at,
        )
        _create_split_event(
            source=source,
            target=target,
            actor_membership=actor_membership,
            occurred_at=occurred_at,
            correction_id=correction_id,
            target_created=True,
            selected_signal_count=len(normalized_signal_ids),
            moved_signal_count=len(move_result.moved_signal_ids),
        )
        _create_signal_move_events(
            source=source,
            target=target,
            actor_membership=actor_membership,
            occurred_at=occurred_at,
            correction_id=correction_id,
            moved_signal_ids=list(move_result.moved_signal_ids),
        )
        return PatternSplitResult(
            source_pattern=source,
            target_pattern=target,
            target_created=True,
            moved_assignments=move_result.moved_assignments,
            correction_id=correction_id,
        )


def _terminal_merge_precheck(
    *,
    actor_membership: EstablishmentMembership,
    source_pattern: OperationalPattern,
    target_pattern: OperationalPattern,
) -> OperationalPattern | None:
    with transaction.atomic():
        patterns = _lock_patterns_for_owner_correction(
            [source_pattern.id, target_pattern.id]
        )
        source = patterns[source_pattern.id]
        target = patterns[target_pattern.id]
        _require_owner_correction_permission(
            actor_membership=actor_membership,
            organization=source.organization,
        )
        if source.organization_id != target.organization_id:
            raise AnalyticsValidationError(
                "Patterns must belong to the same organization.",
                code="analytics_pattern_wrong_organization",
            )
        if source.status == OperationalPattern.Status.MERGED:
            if source.merged_into_id == target.id:
                return source
            raise AnalyticsValidationError(
                "Pattern is already merged into another target.",
                code="analytics_pattern_already_merged",
            )
        if source.status == OperationalPattern.Status.RETIRED:
            raise AnalyticsValidationError(
                "Retired patterns cannot be merged.",
                code="analytics_pattern_retired",
            )
        return None


def _require_owner_correction_permission(
    *,
    actor_membership: EstablishmentMembership,
    organization: Organization,
) -> None:
    if not can_correct_operational_patterns(actor_membership, organization=organization):
        raise AnalyticsValidationError(
            "Owner permission is required to correct operational patterns.",
            code="analytics_owner_permission_required",
        )


def _require_active_pattern_pair(
    *,
    source: OperationalPattern,
    target: OperationalPattern,
) -> None:
    if source.id == target.id:
        raise AnalyticsValidationError(
            "Source and target patterns must be distinct.",
            code="analytics_pattern_same_source_target",
        )
    if source.organization_id != target.organization_id:
        raise AnalyticsValidationError(
            "Patterns must belong to the same organization.",
            code="analytics_pattern_wrong_organization",
        )
    if source.status != OperationalPattern.Status.ACTIVE:
        raise AnalyticsValidationError(
            "Source pattern must be active.",
            code="analytics_pattern_source_not_active",
        )
    if target.status != OperationalPattern.Status.ACTIVE:
        raise AnalyticsValidationError(
            "Target pattern must be active.",
            code="analytics_pattern_target_not_active",
        )


def _require_new_merge_patterns(
    *,
    source: OperationalPattern,
    target: OperationalPattern,
) -> None:
    _require_active_pattern_pair(source=source, target=target)


def _normalize_uuid_list(values) -> list[uuid.UUID]:
    normalized = {uuid.UUID(str(value)) for value in values}
    return sorted(normalized, key=str)


def _lock_signals_for_owner_correction(signal_ids: list[uuid.UUID]) -> list[Signal]:
    if not signal_ids:
        return []
    return list(
        Signal.objects.select_for_update(of=("self",))
        .select_related(
            "establishment",
            "establishment__organization",
            "activity_subject",
            "operational_unit",
        )
        .filter(id__in=signal_ids)
        .order_by("id")
    )


def _lock_assignments_for_signals(
    signal_ids: list[uuid.UUID],
) -> list[SignalPatternAssignment]:
    if not signal_ids:
        return []
    return list(
        SignalPatternAssignment.objects.select_for_update(of=("self",))
        .select_related("signal", "pattern")
        .filter(signal_id__in=signal_ids)
        .order_by("signal_id")
    )


def _lock_patterns_for_owner_correction(
    pattern_ids: list[uuid.UUID],
) -> dict[uuid.UUID, OperationalPattern]:
    unique_ids = sorted({uuid.UUID(str(pattern_id)) for pattern_id in pattern_ids}, key=str)
    patterns = [
        OperationalPattern.objects.select_for_update(of=("self",))
        .select_related("organization")
        .get(id=pattern_id)
        for pattern_id in unique_ids
    ]
    if len(patterns) != len(unique_ids):
        raise AnalyticsValidationError(
            "One or more patterns were not found.",
            code="analytics_pattern_not_found",
        )
    return {pattern.id: pattern for pattern in patterns}


def _require_split_label_available(
    *,
    organization: Organization,
    label: str,
) -> None:
    normalized_label = normalize_pattern_label(label)
    if not normalized_label:
        raise AnalyticsValidationError(
            "Pattern label cannot be blank.",
            code="analytics_pattern_label_blank",
        )
    if OperationalPattern.objects.filter(
        organization=organization,
        normalized_label=normalized_label,
        status=OperationalPattern.Status.ACTIVE,
    ).exists():
        raise AnalyticsValidationError(
            "An active pattern with this normalized label already exists.",
            code="analytics_pattern_label_conflict",
        )


def _require_locked_signals_assigned_to_source(
    *,
    normalized_signal_ids: list[uuid.UUID],
    locked_signals: list[Signal],
    assignments: list[SignalPatternAssignment],
    source: OperationalPattern,
    actor_membership: EstablishmentMembership,
) -> None:
    assignment_by_signal_id = {assignment.signal_id: assignment for assignment in assignments}
    if set(assignment_by_signal_id) != set(normalized_signal_ids):
        raise AnalyticsValidationError(
            "Every moved signal requires an assignment.",
            code="analytics_assignment_missing",
        )
    for signal in locked_signals:
        if signal.establishment.organization_id != source.organization_id:
            raise AnalyticsValidationError(
                "Signal belongs to another organization.",
                code="analytics_signal_wrong_organization",
            )
        if not can_correct_signal_pattern_assignment(
            actor_membership,
            signal=signal,
        ):
            raise AnalyticsValidationError(
                "Owner cannot correct this signal assignment.",
                code="analytics_signal_scope_forbidden",
            )
        if assignment_by_signal_id[signal.id].pattern_id != source.id:
            raise AnalyticsValidationError(
                "Signal is not assigned to the source pattern.",
                code="analytics_assignment_wrong_pattern",
            )


def _move_locked_signal_assignments_for_owner_correction(
    *,
    normalized_signal_ids: list[uuid.UUID],
    locked_signals: list[Signal],
    assignments: list[SignalPatternAssignment],
    source: OperationalPattern,
    target: OperationalPattern,
    actor_membership: EstablishmentMembership,
    occurred_at,
) -> OwnerPatternMoveResult:
    assignment_by_signal_id = {assignment.signal_id: assignment for assignment in assignments}
    if set(assignment_by_signal_id) != set(normalized_signal_ids):
        raise AnalyticsValidationError(
            "Every moved signal requires an assignment.",
            code="analytics_assignment_missing",
        )

    moved_assignments: list[SignalPatternAssignment] = []
    moved_signal_ids: list[str] = []
    for signal in locked_signals:
        if signal.establishment.organization_id != source.organization_id:
            raise AnalyticsValidationError(
                "Signal belongs to another organization.",
                code="analytics_signal_wrong_organization",
            )
        if not can_correct_signal_pattern_assignment(
            actor_membership,
            signal=signal,
        ):
            raise AnalyticsValidationError(
                "Owner cannot correct this signal assignment.",
                code="analytics_signal_scope_forbidden",
            )
        assignment = assignment_by_signal_id[signal.id]
        if assignment.pattern_id == target.id:
            continue
        if assignment.pattern_id != source.id:
            raise AnalyticsValidationError(
                "Signal is not assigned to the source pattern.",
                code="analytics_assignment_wrong_pattern",
            )
        moved_assignments.append(
            _mark_locked_assignment_owner_corrected(
                assignment=assignment,
                signal=signal,
                pattern=target,
                signature=build_signal_pattern_signature(signal),
                occurred_at=occurred_at,
            )
        )
        moved_signal_ids.append(str(signal.id))

    return OwnerPatternMoveResult(
        moved_assignments=tuple(moved_assignments),
        moved_signal_ids=tuple(moved_signal_ids),
    )


def _mark_locked_assignment_owner_corrected(
    *,
    assignment: SignalPatternAssignment,
    signal: Signal,
    pattern: OperationalPattern,
    signature: str,
    occurred_at,
) -> SignalPatternAssignment:
    if (
        assignment.classification_status
        == SignalPatternAssignment.ClassificationStatus.PROCESSING
    ):
        assignment.attempt_count += 1
    assignment.signal = signal
    assignment.pattern = pattern
    assignment.classification_status = SignalPatternAssignment.ClassificationStatus.SUCCEEDED
    assignment.assignment_source = SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
    assignment.owner_correction_signature = _require_nonblank(
        signature,
        field_name="owner_correction_signature",
    )
    assignment.assigned_signature = assignment.owner_correction_signature
    assignment.assigned_classifier_version = OWNER_CORRECTION_CLASSIFIER_VERSION
    assignment.assigned_at = occurred_at
    assignment.pending_signature = ""
    assignment.pending_classifier_version = ""
    assignment.last_error_code = ""
    assignment.next_retry_at = None
    return _validate_and_save_assignment(
        assignment,
        update_fields=[
            "pattern",
            "classification_status",
            "assignment_source",
            "owner_correction_signature",
            "assigned_signature",
            "assigned_classifier_version",
            "assigned_at",
            "pending_signature",
            "pending_classifier_version",
            "last_error_code",
            "next_retry_at",
            "attempt_count",
        ],
    )


def _create_pattern_event(
    *,
    pattern: OperationalPattern,
    event_type: str,
    actor_membership: EstablishmentMembership | None,
    occurred_at,
    metadata_safe: dict[str, Any],
) -> PatternLifecycleEvent:
    event = PatternLifecycleEvent(
        pattern=pattern,
        organization=pattern.organization,
        event_type=event_type,
        actor_membership=actor_membership,
        occurred_at=occurred_at,
        metadata_safe=metadata_safe,
    )
    try:
        event.full_clean(validate_unique=False, validate_constraints=False)
    except ValidationError as exc:
        raise AnalyticsValidationError(str(exc)) from exc
    event.save()
    return event


def _create_signal_move_events(
    *,
    source: OperationalPattern,
    target: OperationalPattern,
    actor_membership: EstablishmentMembership,
    occurred_at,
    correction_id: str,
    moved_signal_ids: list[str],
) -> None:
    signal_ids = sorted(set(moved_signal_ids))
    if not signal_ids:
        return
    chunk_size = max(
        1,
        int(getattr(settings, "HOUSTON_ANALYTICS_PATTERN_EVENT_SIGNAL_ID_CHUNK_SIZE", 200)),
    )
    chunks = [
        signal_ids[index : index + chunk_size]
        for index in range(0, len(signal_ids), chunk_size)
    ]
    for direction, pattern in (("out", source), ("in", target)):
        for index, chunk in enumerate(chunks, start=1):
            _create_pattern_event(
                pattern=pattern,
                event_type=PatternLifecycleEvent.EventType.SIGNALS_MOVED,
                actor_membership=actor_membership,
                occurred_at=occurred_at,
                metadata_safe={
                    "correction_id": correction_id,
                    "source_pattern_id": str(source.id),
                    "target_pattern_id": str(target.id),
                    "signal_ids": chunk,
                    "signal_count": len(chunk),
                    "direction": direction,
                    "chunk_index": index,
                    "chunk_count": len(chunks),
                },
            )


def _create_split_event(
    *,
    source: OperationalPattern,
    target: OperationalPattern,
    actor_membership: EstablishmentMembership,
    occurred_at,
    correction_id: str,
    target_created: bool,
    selected_signal_count: int,
    moved_signal_count: int,
) -> PatternLifecycleEvent:
    return _create_pattern_event(
        pattern=source,
        event_type=PatternLifecycleEvent.EventType.SPLIT,
        actor_membership=actor_membership,
        occurred_at=occurred_at,
        metadata_safe={
            "correction_id": correction_id,
            "source_pattern_id": str(source.id),
            "target_pattern_id": str(target.id),
            "target_created": target_created,
            "selected_signal_count": selected_signal_count,
            "moved_signal_count": moved_signal_count,
        },
    )


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
    assignment.assignment_source = SignalPatternAssignment.AssignmentSource.CLASSIFIER
    assignment.owner_correction_signature = ""
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
            "assignment_source",
            "owner_correction_signature",
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
    assignment.assignment_source = SignalPatternAssignment.AssignmentSource.CLASSIFIER
    assignment.owner_correction_signature = ""
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
            "assignment_source",
            "owner_correction_signature",
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
        try:
            assignment = mark_assignment_temporary_failed(
                signal=signal,
                error_code=exc.error_code,
                expected_attempt_count=exc.attempt_count,
                pending_signature=exc.pending_signature,
                pending_classifier_version=exc.pending_classifier_version,
                next_retry_at=timezone.now() + timedelta(seconds=retry_delay_seconds),
            )
        except AnalyticsValidationError as validation_error:
            if _is_obsolete_assignment_error(validation_error):
                return PatternClassificationRetryFinalization(
                    outcome="obsolete",
                    assignment=SignalPatternAssignment.objects.get(signal=signal),
                )
            raise
        return PatternClassificationRetryFinalization(
            outcome="retry",
            assignment=assignment,
        )

    try:
        assignment = mark_assignment_permanently_failed(
            signal=signal,
            error_code="retry_exhausted",
            expected_attempt_count=exc.attempt_count,
            pending_signature=exc.pending_signature,
            pending_classifier_version=exc.pending_classifier_version,
        )
    except AnalyticsValidationError as validation_error:
        if _is_obsolete_assignment_error(validation_error):
            return PatternClassificationRetryFinalization(
                outcome="obsolete",
                assignment=SignalPatternAssignment.objects.get(signal=signal),
            )
        raise
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
        assignment.assignment_source
        == SignalPatternAssignment.AssignmentSource.OWNER_CORRECTION
        and assignment.pattern_id is not None
        and assignment.owner_correction_signature == signature
    ):
        return PatternClassificationClaimResult(
            status="already_succeeded",
            attempt_count=None,
            assignment=assignment,
            reason="owner_correction_protected",
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
            reason="already_current",
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
            reason="recent_processing",
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
        reason="claimed",
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
        setattr(claim.assignment, "_analytics_claim_status", claim.status)
        setattr(claim.assignment, "_analytics_claim_reason", claim.reason)
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
        setattr(
            assignment,
            "_analytics_duplicate_guard_reason",
            resolution.duplicate_guard_decision.reason,
        )
        setattr(assignment, "_analytics_claim_status", claim.status)
        setattr(assignment, "_analytics_claim_reason", claim.reason)
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
        setattr(exc.assignment, "_analytics_claim_status", "obsolete")
        setattr(exc.assignment, "_analytics_claim_reason", "obsolete_attempt")
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
        try:
            mark_assignment_permanently_failed(
                signal=signal,
                error_code=error_code,
                expected_attempt_count=claim.attempt_count,
                pending_signature=signature,
                pending_classifier_version=classifier_version,
            )
        except AnalyticsValidationError as validation_error:
            if _is_obsolete_assignment_error(validation_error):
                assignment = SignalPatternAssignment.objects.get(signal=signal)
                setattr(assignment, "_analytics_claim_status", "obsolete")
                setattr(assignment, "_analytics_claim_reason", "obsolete_attempt")
                return assignment
            raise
        _write_analytics_usage_log(
            signal=signal,
            provider=provider.provider,
            model=getattr(provider, "model", ""),
            status=AIUsageLog.Status.FAILED,
            latency_ms=_elapsed_ms(provider_started_at),
            correlation_id=uuid.uuid4(),
            error_code=error_code,
        )
        assignment = SignalPatternAssignment.objects.get(signal=signal)
        setattr(assignment, "_analytics_claim_status", claim.status)
        setattr(assignment, "_analytics_claim_reason", claim.reason)
        return assignment


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
        if _is_obsolete_assignment_error(exc):
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
