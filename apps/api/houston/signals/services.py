from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.ai.observation_pipeline import (
    ObservationPipelineError,
    ObservationPipelineInvalidOutputError,
    ObservationPipelineSkippedError,
    ObservationPipelineTimeoutError,
    ObservationPipelineUnavailableError,
    call_observation_pipeline,
)
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.core.observability import (
    build_observation_pipeline_candidate_apply_log_context,
    build_observation_pipeline_timing_log_context,
    build_observation_processing_log_context,
    observation_processing_duration_seconds,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    EstablishmentMembership,
    OperationalUnit,
)
from houston.establishments.taxonomy_snapshot import build_routing_taxonomy
from houston.observations.models import Observation, ObservationProcessing
from houston.signals.aggregation_eval import (
    count_active_taxonomy_peers_with_different_focus,
    format_taxonomy_bucket_key,
)
from houston.signals.author_affected_fallback import apply_author_affected_fallback
from houston.signals.constants import (
    ACTIVE_SIGNAL_STATUSES,
    AI_ISSUE_FOCUS_MAX_LENGTH,
    AI_LOCATION_TEXT_MAX_LENGTH,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    CANCEL_RESOLVE_SIGNAL_STATUSES,
    MAX_CANDIDATES_PER_OBSERVATION,
    SIGNAL_IN_PROGRESS_MANUAL_CANCEL_DETAIL,
    SIGNAL_IN_PROGRESS_MANUAL_RESOLVE_DETAIL,
    SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
    SIGNAL_LIFECYCLE_EVENT_CANCELED,
    SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING,
    SIGNAL_LIFECYCLE_EVENT_RESOLVED,
    SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN,
    SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    STRUCTURED_SUMMARY_SHORT_MAX_LENGTH,
)
from houston.signals.exceptions import (
    SignalAlreadyMergedError,
    SignalPermissionError,
    SignalPipelineCandidateError,
    SignalStateError,
    SignalValidationError,
)
from houston.signals.lifecycle_events import record_signal_lifecycle_event
from houston.signals.models import CandidateSignal, ExpectedAction, Signal, SignalSourceObservation
from houston.signals.responsible_text_anchoring import (
    sanitize_unanchored_responsible_without_subject,
)
from houston.signals.routing_resolver import (
    RoutingResolution,
    resolve_candidate_routing,
    resolve_materialized_routing,
    routing_proposal_from_pipeline_candidate,
)
from houston.signals.signal_classification import (
    InvalidSignalClassificationError,
    routing_status_for_classification,
    validate_partial_signal_routing,
    validate_signal_classification,
)

if TYPE_CHECKING:
    from houston.ai.observation_pipeline import ObservationPipelineProvider

logger = logging.getLogger(__name__)

_STUCK_PROCESSING_RECOVERY_ERROR_CODE = "stuck_processing_recovered"
_MAX_OBSERVATION_PIPELINE_ATTEMPTS = 3
_ACTIVE_AGGREGATION_UNIQUE_CONSTRAINT = "signal_unique_active_aggregation_key"


@dataclass(frozen=True)
class ResolvedTaxonomy:
    operational_unit: OperationalUnit | None
    affected_business_unit: BusinessUnit | None = None
    responsible_business_unit: BusinessUnit | None = None
    activity_subject: ActivitySubject | None = None


@dataclass(frozen=True)
class PipelineApplyResult:
    outcome: ObservationProcessing.Outcome
    created_count: int
    aggregated_count: int


def normalize_location_text(value: str | None) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return ""
    if len(normalized) > AI_LOCATION_TEXT_MAX_LENGTH:
        return normalized[:AI_LOCATION_TEXT_MAX_LENGTH]
    return normalized


def normalize_issue_focus(value: str | None) -> str:
    normalized = " ".join((value or "").strip().lower().split())
    if len(normalized) > AI_ISSUE_FOCUS_MAX_LENGTH:
        return normalized[:AI_ISSUE_FOCUS_MAX_LENGTH]
    return normalized


def require_normalized_issue_focus(value: str | None) -> str:
    normalized = normalize_issue_focus(value)
    if not normalized:
        raise SignalPipelineCandidateError("issue_focus is required after normalization.")
    return normalized


def _is_active_aggregation_unique_violation(exc: IntegrityError) -> bool:
    cause = exc.__cause__
    if cause is None:
        return False
    diag = getattr(cause, "diag", None)
    if diag is None:
        return False
    return getattr(diag, "constraint_name", None) == _ACTIVE_AGGREGATION_UNIQUE_CONSTRAINT


def validate_pipeline_output_issue_focus(
    *,
    output: ObservationPipelineOutput,
    observation: Observation | None = None,
) -> None:
    for index, candidate in enumerate(output.candidates):
        try:
            require_normalized_issue_focus(candidate.issue_focus)
        except SignalPipelineCandidateError:
            extra: dict[str, str | int | bool] = {
                "candidate_index": index,
                "issue_focus_present": candidate.issue_focus is not None,
                "issue_focus_normalized_empty": True,
                "event": "observation_pipeline_invalid_issue_focus",
            }
            if observation is not None:
                extra["observation_id"] = str(observation.id)
                extra["establishment_id"] = str(observation.establishment_id)
            logger.warning(
                "observation_pipeline_invalid_issue_focus",
                extra=extra,
            )
            raise


def format_aggregation_key(
    key: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID | None, str],
) -> str:
    affected_id, responsible_id, subject_id, unit_id, issue_focus = key
    unit_token = str(unit_id) if unit_id is not None else "null"
    return f"{affected_id}|{responsible_id}|{subject_id}|{unit_token}|{issue_focus}"


def resolve_signal_location_text(
    *,
    candidate: PipelineCandidateOutput,
    resolved: ResolvedTaxonomy,
    observation: Observation,
) -> str:
    if resolved.operational_unit is not None:
        return normalize_location_text(resolved.operational_unit.label)

    text = normalize_location_text(candidate.location_text)
    if not text:
        return ""

    raw_normalized = observation.raw_text.strip().casefold()
    if text.casefold() == raw_normalized:
        return ""
    return text


def structured_summary_short(text: str) -> str:
    normalized = (text or "").strip()
    if len(normalized) <= STRUCTURED_SUMMARY_SHORT_MAX_LENGTH:
        return normalized
    return normalized[: STRUCTURED_SUMMARY_SHORT_MAX_LENGTH - 1].rstrip() + "…"


def touch_signal_activity(*, signal: Signal, at=None) -> None:
    signal.last_activity_at = at or timezone.now()
    signal.save(update_fields=["last_activity_at", "updated_at"])


def record_source_observation_link(
    *,
    signal: Signal,
    observation: Observation,
    link_type: str,
) -> SignalSourceObservation:
    link, _created = SignalSourceObservation.objects.get_or_create(
        signal=signal,
        observation=observation,
        link_type=link_type,
    )
    return link


@transaction.atomic
def create_signal_from_candidate(
    *,
    observation: Observation,
    candidate: PipelineCandidateOutput,
    resolved: ResolvedTaxonomy,
    title: str,
    structured_summary: str,
    routing_status: str,
) -> Signal:
    establishment = observation.establishment
    try:
        if routing_status == Signal.RoutingStatus.RESOLVED:
            if (
                resolved.affected_business_unit is None
                or resolved.responsible_business_unit is None
                or resolved.activity_subject is None
            ):
                raise SignalValidationError(
                    "resolved routing_status requires a complete taxonomy triplet.",
                    code="inconsistent_routing_status",
                )
            validate_signal_classification(
                establishment=establishment,
                affected_business_unit=resolved.affected_business_unit,
                responsible_business_unit=resolved.responsible_business_unit,
                activity_subject=resolved.activity_subject,
            )
        elif routing_status == Signal.RoutingStatus.UNASSIGNED:
            validate_partial_signal_routing(
                establishment=establishment,
                affected_business_unit=resolved.affected_business_unit,
                responsible_business_unit=resolved.responsible_business_unit,
                activity_subject=resolved.activity_subject,
            )
        else:
            raise SignalValidationError(
                "routing_status must be resolved or unassigned.",
                code="invalid_routing_status",
            )
    except InvalidSignalClassificationError as exc:
        raise SignalValidationError(
            str(exc),
            code="invalid_signal_classification",
        ) from exc

    expected_status = routing_status_for_classification(
        establishment=establishment,
        affected_business_unit=resolved.affected_business_unit,
        responsible_business_unit=resolved.responsible_business_unit,
        activity_subject=resolved.activity_subject,
    )
    if routing_status != expected_status:
        raise SignalValidationError(
            "routing_status is inconsistent with resolved taxonomy FKs.",
            code="inconsistent_routing_status",
        )

    now = timezone.now()
    location_text = resolve_signal_location_text(
        candidate=candidate,
        resolved=resolved,
        observation=observation,
    )

    signal = Signal.objects.create(
        establishment=establishment,
        operational_unit=resolved.operational_unit,
        affected_business_unit=resolved.affected_business_unit,
        responsible_business_unit=resolved.responsible_business_unit,
        activity_subject=resolved.activity_subject,
        status=Signal.Status.OPEN,
        routing_status=routing_status,
        title=title.strip(),
        structured_summary=structured_summary.strip(),
        location_text=location_text,
        issue_focus=require_normalized_issue_focus(candidate.issue_focus),
        expected_action=candidate.expected_action,
        last_activity_at=now,
    )
    record_source_observation_link(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    _schedule_signal_invalidation(signal=signal, reason="signal.created")
    from houston.notifications.scheduling import schedule_signal_created_notification

    schedule_signal_created_notification(signal_id=signal.id)
    return signal


@transaction.atomic
def aggregate_candidate_into_signal(
    *,
    signal: Signal,
    observation: Observation,
) -> Signal:
    now = timezone.now()
    signal.last_activity_at = now
    signal.save(update_fields=["last_activity_at", "updated_at"])
    record_source_observation_link(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )
    from houston.observations.media_services import delete_all_observation_media

    has_active_created_from = Signal.objects.filter(
        source_observation_links__observation_id=observation.id,
        source_observation_links__link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        status__in=ACTIVE_SIGNAL_STATUSES,
    ).exists()
    if not has_active_created_from:
        delete_all_observation_media(observation_id=observation.id)
    _schedule_signal_invalidation(signal=signal, reason="signal.updated")
    return signal


def _d3_expected_action_decision(
    *,
    signal_expected_action: str | None,
    candidate_expected_action: str | None,
) -> tuple[str | None, dict[str, str | None] | None]:
    """Single D3 decision: (effective_signal_expected_action, optional audit_block)."""
    signal_action = signal_expected_action or None
    candidate_action = candidate_expected_action or None
    if signal_action is None and candidate_action is not None:
        return candidate_action, {
            "source": "aggregation_initial_expected_action",
            "signal_expected_action": None,
            "candidate_expected_action": candidate_action,
            "adopted": candidate_action,
        }
    if (
        signal_action is not None
        and candidate_action is not None
        and signal_action != candidate_action
    ):
        return signal_action, {
            "source": "aggregation_expected_action_divergence",
            "signal_expected_action": signal_action,
            "candidate_expected_action": candidate_action,
        }
    return signal_action, None


def apply_expected_action_on_aggregation(
    *,
    signal: Signal,
    candidate_expected_action: str | None,
    candidate_row: CandidateSignal | None = None,
) -> bool:
    """Apply D3 expected_action policy. Returns True if resolution_audit was enriched."""
    effective, audit_block = _d3_expected_action_decision(
        signal_expected_action=signal.expected_action or None,
        candidate_expected_action=candidate_expected_action,
    )
    if effective != (signal.expected_action or None):
        signal.expected_action = effective
        signal.save(update_fields=["expected_action", "updated_at"])

    if audit_block is None:
        return False

    if candidate_row is not None:
        resolution_audit = {**(candidate_row.resolution_audit or {})}
        resolution_audit["expected_action"] = audit_block
        candidate_row.resolution_audit = resolution_audit
    return True


def _apply_expected_action_on_aggregation(
    *,
    signal: Signal,
    candidate_row: CandidateSignal,
) -> bool:
    return apply_expected_action_on_aggregation(
        signal=signal,
        candidate_expected_action=candidate_row.expected_action or None,
        candidate_row=candidate_row,
    )


def _finalize_aggregated_candidate(
    *,
    signal: Signal,
    observation: Observation,
    row: CandidateSignal,
    aggregation_key: str,
    issue_focus: str,
    taxonomy_bucket_key: str,
) -> None:
    signal = aggregate_candidate_into_signal(signal=signal, observation=observation)
    audit_updated = _apply_expected_action_on_aggregation(
        signal=signal,
        candidate_row=row,
    )
    row.outcome = CandidateSignal.Outcome.AGGREGATED_SIGNAL
    row.result_signal = signal
    update_fields = ["outcome", "result_signal", "updated_at"]
    if audit_updated:
        update_fields.insert(0, "resolution_audit")
    row.save(update_fields=update_fields)
    _log_pipeline_candidate_applied(
        observation=observation,
        aggregation_key=aggregation_key,
        hint_used=False,
        hint_rejected_reason="",
        candidate_outcome=CandidateSignal.Outcome.AGGREGATED_SIGNAL,
        issue_focus=issue_focus,
        taxonomy_bucket_key=taxonomy_bucket_key,
        aggregation_match_mode="exact",
    )


def _aggregation_key(
    *,
    affected_business_unit_id: uuid.UUID,
    responsible_business_unit_id: uuid.UUID,
    activity_subject_id: uuid.UUID,
    unit_id: uuid.UUID | None,
    issue_focus: str,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID | None, str]:
    return (
        affected_business_unit_id,
        responsible_business_unit_id,
        activity_subject_id,
        unit_id,
        issue_focus,
    )


def _issue_focus_eval_log_fields(
    *,
    establishment_id: uuid.UUID,
    resolved: ResolvedTaxonomy,
    normalized_issue_focus: str,
    include_peer_count: bool = False,
) -> dict[str, str | int]:
    assert resolved.affected_business_unit is not None
    assert resolved.responsible_business_unit is not None
    assert resolved.activity_subject is not None
    unit_id = resolved.operational_unit.id if resolved.operational_unit else None
    fields: dict[str, str | int] = {
        "issue_focus": normalized_issue_focus,
        "taxonomy_bucket_key": format_taxonomy_bucket_key(
            affected_business_unit_id=resolved.affected_business_unit.id,
            responsible_business_unit_id=resolved.responsible_business_unit.id,
            activity_subject_id=resolved.activity_subject.id,
            operational_unit_id=unit_id,
        ),
    }
    if include_peer_count:
        fields["active_taxonomy_peer_count"] = count_active_taxonomy_peers_with_different_focus(
            establishment_id=establishment_id,
            affected_business_unit_id=resolved.affected_business_unit.id,
            responsible_business_unit_id=resolved.responsible_business_unit.id,
            activity_subject_id=resolved.activity_subject.id,
            operational_unit_id=unit_id,
            issue_focus=normalized_issue_focus,
        )
    return fields


def _resolved_taxonomy_from_resolution(resolution: RoutingResolution) -> ResolvedTaxonomy:
    return ResolvedTaxonomy(
        operational_unit=resolution.operational_unit,
        affected_business_unit=resolution.affected_business_unit,
        responsible_business_unit=resolution.responsible_business_unit,
        activity_subject=resolution.activity_subject,
    )


def find_active_signal_for_aggregation(
    *,
    establishment_id: uuid.UUID,
    resolved: ResolvedTaxonomy,
    issue_focus: str,
    for_update: bool = False,
) -> Signal | None:
    if (
        resolved.affected_business_unit is None
        or resolved.responsible_business_unit is None
        or resolved.activity_subject is None
    ):
        return None

    queryset = Signal.objects.filter(
        establishment_id=establishment_id,
        affected_business_unit=resolved.affected_business_unit,
        responsible_business_unit=resolved.responsible_business_unit,
        activity_subject=resolved.activity_subject,
        issue_focus=issue_focus,
        status__in=ACTIVE_SIGNAL_STATUSES,
        routing_status=Signal.RoutingStatus.RESOLVED,
    )
    if resolved.operational_unit is None:
        queryset = queryset.filter(operational_unit__isnull=True)
    else:
        queryset = queryset.filter(operational_unit=resolved.operational_unit)

    if for_update:
        queryset = queryset.select_for_update()

    return queryset.order_by("-last_activity_at").first()


def _persist_pending_candidate(
    *,
    observation: Observation,
    candidate: PipelineCandidateOutput,
    resolution: RoutingResolution,
) -> CandidateSignal:
    return CandidateSignal.objects.create(
        observation=observation,
        establishment=observation.establishment,
        operational_unit=resolution.operational_unit,
        affected_business_unit=resolution.affected_business_unit,
        responsible_business_unit=resolution.responsible_business_unit,
        activity_subject=resolution.activity_subject,
        location_text=normalize_location_text(candidate.location_text),
        title=candidate.title.strip(),
        structured_summary=candidate.structured_summary.strip(),
        issue_focus=require_normalized_issue_focus(candidate.issue_focus),
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        signal_kind=candidate.signal_kind,
        information_type=candidate.information_type or "",
        canonical_object=candidate.canonical_object,
        expected_action=candidate.expected_action,
        proposed_affected_business_unit_routing_key=(
            candidate.affected_business_unit_routing_key or ""
        ),
        proposed_responsible_business_unit_routing_key=(
            candidate.responsible_business_unit_routing_key or ""
        ),
        proposed_activity_subject_routing_key=(
            candidate.activity_subject_routing_key or ""
        ),
        routing_status=resolution.routing_status,
        resolution_audit=resolution.resolution_audit,
        outcome=CandidateSignal.Outcome.PENDING,
    )


def _apply_resolved_candidate(
    *,
    observation: Observation,
    candidate: PipelineCandidateOutput,
    resolved: ResolvedTaxonomy,
    row: CandidateSignal,
    normalized_issue_focus: str,
    seen_keys: set[tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID | None, str]],
) -> tuple[str, int, int]:
    """Apply aggregation/create for a resolved candidate. Returns (kind, created, aggregated)."""
    assert resolved.affected_business_unit is not None
    assert resolved.responsible_business_unit is not None
    assert resolved.activity_subject is not None
    # Empty normalized issue_focus is rejected before this path (require_normalized_issue_focus).

    eval_log_fields = _issue_focus_eval_log_fields(
        establishment_id=observation.establishment_id,
        resolved=resolved,
        normalized_issue_focus=normalized_issue_focus,
    )
    dedupe_key = _aggregation_key(
        affected_business_unit_id=resolved.affected_business_unit.id,
        responsible_business_unit_id=resolved.responsible_business_unit.id,
        activity_subject_id=resolved.activity_subject.id,
        unit_id=resolved.operational_unit.id if resolved.operational_unit else None,
        issue_focus=normalized_issue_focus,
    )
    formatted_key = format_aggregation_key(dedupe_key)
    if dedupe_key in seen_keys:
        row.outcome = CandidateSignal.Outcome.REJECTED
        row.save(update_fields=["outcome", "updated_at"])
        _log_pipeline_candidate_applied(
            observation=observation,
            aggregation_key=formatted_key,
            hint_used=False,
            hint_rejected_reason="",
            candidate_outcome=CandidateSignal.Outcome.REJECTED,
            issue_focus=str(eval_log_fields["issue_focus"]),
            taxonomy_bucket_key=str(eval_log_fields["taxonomy_bucket_key"]),
        )
        return "rejected", 0, 0
    seen_keys.add(dedupe_key)

    existing = find_active_signal_for_aggregation(
        establishment_id=observation.establishment_id,
        resolved=resolved,
        issue_focus=normalized_issue_focus,
        for_update=True,
    )
    if existing is not None:
        _finalize_aggregated_candidate(
            signal=existing,
            observation=observation,
            row=row,
            aggregation_key=formatted_key,
            issue_focus=str(eval_log_fields["issue_focus"]),
            taxonomy_bucket_key=str(eval_log_fields["taxonomy_bucket_key"]),
        )
        return "aggregated", 0, 1

    create_eval_log_fields = _issue_focus_eval_log_fields(
        establishment_id=observation.establishment_id,
        resolved=resolved,
        normalized_issue_focus=normalized_issue_focus,
        include_peer_count=True,
    )
    try:
        with transaction.atomic():
            signal = create_signal_from_candidate(
                observation=observation,
                candidate=candidate,
                resolved=resolved,
                title=candidate.title,
                structured_summary=candidate.structured_summary,
                routing_status=Signal.RoutingStatus.RESOLVED,
            )
    except IntegrityError as exc:
        if not _is_active_aggregation_unique_violation(exc):
            raise
        existing = find_active_signal_for_aggregation(
            establishment_id=observation.establishment_id,
            resolved=resolved,
            issue_focus=normalized_issue_focus,
            for_update=True,
        )
        if existing is None:
            raise
        _finalize_aggregated_candidate(
            signal=existing,
            observation=observation,
            row=row,
            aggregation_key=formatted_key,
            issue_focus=str(create_eval_log_fields["issue_focus"]),
            taxonomy_bucket_key=str(create_eval_log_fields["taxonomy_bucket_key"]),
        )
        return "aggregated", 0, 1

    row.outcome = CandidateSignal.Outcome.CREATED_SIGNAL
    row.result_signal = signal
    row.save(update_fields=["outcome", "result_signal", "updated_at"])
    _log_pipeline_candidate_applied(
        observation=observation,
        aggregation_key=formatted_key,
        hint_used=False,
        hint_rejected_reason="",
        candidate_outcome=CandidateSignal.Outcome.CREATED_SIGNAL,
        issue_focus=str(create_eval_log_fields["issue_focus"]),
        taxonomy_bucket_key=str(create_eval_log_fields["taxonomy_bucket_key"]),
        active_taxonomy_peer_count=int(create_eval_log_fields["active_taxonomy_peer_count"]),
    )
    return "created", 1, 0


@transaction.atomic
def apply_pipeline_output(
    *,
    observation: Observation,
    output: ObservationPipelineOutput,
) -> PipelineApplyResult:
    candidates = output.candidates[:MAX_CANDIDATES_PER_OBSERVATION]
    if not candidates:
        return PipelineApplyResult(
            outcome=ObservationProcessing.Outcome.NO_SIGNAL_CREATED,
            created_count=0,
            aggregated_count=0,
        )

    taxonomy = build_routing_taxonomy(establishment_id=observation.establishment_id)
    seen_keys: set[tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID | None, str]] = set()
    created_count = 0
    aggregated_count = 0

    for candidate in candidates:
        proposal = routing_proposal_from_pipeline_candidate(candidate)
        resolution = resolve_candidate_routing(
            establishment_id=observation.establishment_id,
            proposal=proposal,
            routing_taxonomy=taxonomy,
        )
        resolution = sanitize_unanchored_responsible_without_subject(
            observation=observation,
            resolution=resolution,
        )
        resolution = apply_author_affected_fallback(
            observation=observation,
            resolution=resolution,
            routing_taxonomy=taxonomy,
        )
        resolved = _resolved_taxonomy_from_resolution(resolution)
        normalized_issue_focus = require_normalized_issue_focus(candidate.issue_focus)
        row = _persist_pending_candidate(
            observation=observation,
            candidate=candidate,
            resolution=resolution,
        )

        if resolution.routing_status == Signal.RoutingStatus.UNASSIGNED:
            signal = create_signal_from_candidate(
                observation=observation,
                candidate=candidate,
                resolved=resolved,
                title=candidate.title,
                structured_summary=candidate.structured_summary,
                routing_status=Signal.RoutingStatus.UNASSIGNED,
            )
            row.outcome = CandidateSignal.Outcome.CREATED_SIGNAL
            row.result_signal = signal
            row.save(update_fields=["outcome", "result_signal", "updated_at"])
            created_count += 1
            _log_pipeline_candidate_applied(
                observation=observation,
                aggregation_key="",
                hint_used=False,
                hint_rejected_reason="",
                candidate_outcome=CandidateSignal.Outcome.CREATED_SIGNAL,
                issue_focus=normalized_issue_focus,
                taxonomy_bucket_key="",
            )
            continue

        kind, created_delta, aggregated_delta = _apply_resolved_candidate(
            observation=observation,
            candidate=candidate,
            resolved=resolved,
            row=row,
            normalized_issue_focus=normalized_issue_focus,
            seen_keys=seen_keys,
        )
        del kind
        created_count += created_delta
        aggregated_count += aggregated_delta

    if created_count == 0 and aggregated_count == 0:
        return PipelineApplyResult(
            outcome=ObservationProcessing.Outcome.NO_SIGNAL_CREATED,
            created_count=0,
            aggregated_count=0,
        )

    if created_count > 0 and aggregated_count > 0:
        outcome = ObservationProcessing.Outcome.SIGNALS_CREATED
    elif aggregated_count > 0:
        outcome = ObservationProcessing.Outcome.SIGNAL_AGGREGATED
    else:
        outcome = ObservationProcessing.Outcome.SIGNALS_CREATED
    return PipelineApplyResult(
        outcome=outcome,
        created_count=created_count,
        aggregated_count=aggregated_count,
    )


def _enqueue_observation_pipeline_task(
    observation_id: uuid.UUID,
    *,
    already_enqueued: set[uuid.UUID],
) -> bool:
    if observation_id in already_enqueued:
        return False
    already_enqueued.add(observation_id)
    try:
        from houston.signals.tasks import process_observation_task

        process_observation_task.delay(str(observation_id))
    except Exception:
        logger.error(
            "observation_pipeline_recovery_enqueue_failed",
            extra={
                "observation_id": str(observation_id),
                "event": "observation_pipeline_recovery_enqueue_failed",
            },
            exc_info=True,
        )
        already_enqueued.discard(observation_id)
        return False
    logger.info(
        "observation_pipeline_recovery_enqueued",
        extra={
            "observation_id": str(observation_id),
            "event": "observation_pipeline_recovery_enqueued",
        },
    )
    return True


def recover_stuck_observation_processing_batch(
    *,
    already_enqueued: set[uuid.UUID] | None = None,
) -> int:
    enqueued_ids = already_enqueued if already_enqueued is not None else set()
    stuck_threshold = settings.HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS
    cutoff = timezone.now() - timedelta(seconds=stuck_threshold)
    stuck_ids = list(
        ObservationProcessing.objects.filter(
            status=ObservationProcessing.Status.PROCESSING,
            processing_started_at__lt=cutoff,
        ).values_list("id", flat=True)
    )
    acted_on = 0
    for processing_id in stuck_ids:
        processing = ObservationProcessing.objects.filter(id=processing_id).first()
        if processing is None:
            continue
        observation_id = processing.observation_id
        if _try_recover_stuck_processing(processing=processing):
            acted_on += 1
            processing.refresh_from_db()
            if processing.status == ObservationProcessing.Status.RETRYING:
                _enqueue_observation_pipeline_task(
                    observation_id,
                    already_enqueued=enqueued_ids,
                )
            continue
        processing.refresh_from_db()
        if processing.status == ObservationProcessing.Status.FAILED:
            acted_on += 1
    return acted_on


def recover_orphaned_observation_processing_batch(
    *,
    already_enqueued: set[uuid.UUID] | None = None,
) -> int:
    enqueued_ids = already_enqueued if already_enqueued is not None else set()
    stuck_threshold = settings.HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS
    cutoff = timezone.now() - timedelta(seconds=stuck_threshold)
    enqueued_count = 0

    queued_observation_ids = list(
        ObservationProcessing.objects.filter(
            status=ObservationProcessing.Status.QUEUED,
            queued_at__lt=cutoff,
        ).values_list("observation_id", flat=True)
    )
    for observation_id in queued_observation_ids:
        if _enqueue_observation_pipeline_task(
            observation_id,
            already_enqueued=enqueued_ids,
        ):
            enqueued_count += 1

    retrying_observation_ids = list(
        ObservationProcessing.objects.filter(
            status=ObservationProcessing.Status.RETRYING,
            processing_started_at__isnull=True,
            updated_at__lt=cutoff,
        ).values_list("observation_id", flat=True)
    )
    for observation_id in retrying_observation_ids:
        if _enqueue_observation_pipeline_task(
            observation_id,
            already_enqueued=enqueued_ids,
        ):
            enqueued_count += 1

    return enqueued_count


def recover_observation_processing_batch() -> dict[str, int]:
    already_enqueued: set[uuid.UUID] = set()
    stuck_acted_on = recover_stuck_observation_processing_batch(
        already_enqueued=already_enqueued,
    )
    orphan_enqueued = recover_orphaned_observation_processing_batch(
        already_enqueued=already_enqueued,
    )
    return {
        "stuck_acted_on": stuck_acted_on,
        "orphan_enqueued": orphan_enqueued,
    }


def run_observation_pipeline(
    observation_id: uuid.UUID,
    *,
    provider: ObservationPipelineProvider | None = None,
) -> None:
    with transaction.atomic():
        processing = (
            ObservationProcessing.objects.select_for_update()
            .select_related("observation", "observation__establishment")
            .filter(observation_id=observation_id)
            .first()
        )
        if processing is None:
            return
        if processing.status == ObservationProcessing.Status.PROCESSING:
            if not _try_recover_stuck_processing(processing=processing):
                _log_observation_processing_skip(processing=processing)
                return
            processing = (
                ObservationProcessing.objects.select_for_update()
                .select_related("observation", "observation__establishment")
                .get(id=processing.id)
            )
        if processing.status not in {
            ObservationProcessing.Status.QUEUED,
            ObservationProcessing.Status.RETRYING,
        }:
            _log_observation_processing_skip(processing=processing)
            return

        observation = processing.observation
        now = timezone.now()
        processing.status = ObservationProcessing.Status.PROCESSING
        processing.processing_started_at = now
        processing.attempt_count += 1
        processing.save(
            update_fields=[
                "status",
                "processing_started_at",
                "attempt_count",
                "updated_at",
            ]
        )
        logger.info(
            "observation_pipeline_processing_started",
            extra=build_observation_processing_log_context(
                processing=processing,
                establishment_id=observation.establishment_id,
                event="observation_pipeline_processing_started",
            ),
        )

    pipeline_started_at = time.monotonic()
    try:
        output = call_observation_pipeline(
            observation=observation,
            provider=provider,
        )
    except ObservationPipelineSkippedError as exc:
        _mark_processing_failed(processing_id=processing.id, error_code=exc.error_code)
        return
    except (
        ObservationPipelineUnavailableError,
        ObservationPipelineTimeoutError,
    ) as exc:
        _mark_processing_retry_or_failed(processing_id=processing.id, error_code=exc.error_code)
        raise
    except ObservationPipelineInvalidOutputError as exc:
        _mark_processing_failed(processing_id=processing.id, error_code=exc.error_code)
        return
    except ObservationPipelineError as exc:
        _mark_processing_failed(processing_id=processing.id, error_code=exc.error_code)
        return
    except Exception:
        _mark_processing_failed(
            processing_id=processing.id,
            error_code="pipeline_internal_error",
        )
        raise

    apply_started_at = time.monotonic()
    try:
        validate_pipeline_output_issue_focus(output=output, observation=observation)
    except SignalPipelineCandidateError:
        _mark_processing_failed(processing_id=processing.id, error_code="invalid_issue_focus")
        return

    try:
        with transaction.atomic():
            processing = ObservationProcessing.objects.select_for_update().get(id=processing.id)
            apply_result = apply_pipeline_output(observation=observation, output=output)
            processing.status = ObservationProcessing.Status.PROCESSED
            processing.processed_at = timezone.now()
            processing.outcome = apply_result.outcome
            processing.last_error_code = ""
            processing.save(
                update_fields=[
                    "status",
                    "processed_at",
                    "outcome",
                    "last_error_code",
                    "updated_at",
                ]
            )
    except SignalPipelineCandidateError:
        _mark_processing_failed(processing_id=processing.id, error_code="invalid_issue_focus")
        return
    except IntegrityError:
        _mark_processing_failed(
            processing_id=processing.id,
            error_code="pipeline_persist_error",
        )
        logger.exception(
            "observation_pipeline_apply_persist_failed",
            extra={
                "observation_id": str(observation.id),
                "establishment_id": str(observation.establishment_id),
                "event": "observation_pipeline_apply_persist_failed",
            },
        )
        raise
    except Exception:
        _mark_processing_failed(
            processing_id=processing.id,
            error_code="pipeline_internal_error",
        )
        logger.exception(
            "observation_pipeline_apply_failed",
            extra={
                "observation_id": str(observation.id),
                "establishment_id": str(observation.establishment_id),
                "event": "observation_pipeline_apply_failed",
            },
        )
        raise
    apply_duration_ms = int((time.monotonic() - apply_started_at) * 1000)
    _log_observation_pipeline_signals_applied(
        observation=observation,
        apply_result=apply_result,
        apply_duration_ms=apply_duration_ms,
    )
    _log_observation_pipeline_completed(
        observation=observation,
        processing=processing,
        pipeline_started_at=pipeline_started_at,
        apply_result=apply_result,
        apply_duration_ms=apply_duration_ms,
    )


def _log_pipeline_candidate_applied(
    *,
    observation: Observation,
    aggregation_key: str,
    hint_used: bool,
    hint_rejected_reason: str,
    candidate_outcome: str,
    issue_focus: str = "",
    taxonomy_bucket_key: str = "",
    active_taxonomy_peer_count: int | None = None,
    aggregation_match_mode: str = "",
) -> None:
    logger.info(
        "observation_pipeline_candidate_applied",
        extra=build_observation_pipeline_candidate_apply_log_context(
            observation_id=observation.id,
            establishment_id=observation.establishment_id,
            event="observation_pipeline_candidate_applied",
            aggregation_key=aggregation_key,
            hint_used=hint_used,
            hint_rejected_reason=hint_rejected_reason,
            candidate_outcome=candidate_outcome,
            issue_focus=issue_focus,
            taxonomy_bucket_key=taxonomy_bucket_key,
            active_taxonomy_peer_count=active_taxonomy_peer_count,
            aggregation_match_mode=aggregation_match_mode,
        ),
    )


def _log_observation_pipeline_signals_applied(
    *,
    observation: Observation,
    apply_result: PipelineApplyResult,
    apply_duration_ms: int,
) -> None:
    logger.info(
        "observation_pipeline_signals_applied",
        extra=build_observation_pipeline_timing_log_context(
            observation_id=observation.id,
            establishment_id=observation.establishment_id,
            event="observation_pipeline_signals_applied",
            duration_ms=apply_duration_ms,
            outcome=apply_result.outcome,
            created_count=apply_result.created_count,
            aggregated_count=apply_result.aggregated_count,
        ),
    )


def _log_observation_pipeline_completed(
    *,
    observation: Observation,
    processing: ObservationProcessing,
    pipeline_started_at: float,
    apply_result: PipelineApplyResult,
    apply_duration_ms: int,
) -> None:
    total_duration_ms = int((time.monotonic() - pipeline_started_at) * 1000)
    logger.info(
        "observation_pipeline_completed",
        extra=build_observation_pipeline_timing_log_context(
            observation_id=observation.id,
            establishment_id=observation.establishment_id,
            event="observation_pipeline_completed",
            total_duration_ms=total_duration_ms,
            duration_ms=apply_duration_ms,
            outcome=apply_result.outcome,
            created_count=apply_result.created_count,
            aggregated_count=apply_result.aggregated_count,
            attempt_count=processing.attempt_count,
        ),
    )


def _try_recover_stuck_processing(*, processing: ObservationProcessing) -> bool:
    duration = observation_processing_duration_seconds(processing=processing)
    stuck_threshold = settings.HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS
    is_stuck = duration is not None and duration >= stuck_threshold
    if not is_stuck:
        return False

    logger.warning(
        "observation_pipeline_stuck_processing",
        extra=build_observation_processing_log_context(
            processing=processing,
            event="observation_pipeline_stuck_processing",
        ),
    )

    with transaction.atomic():
        processing = (
            ObservationProcessing.objects.select_for_update()
            .select_related("observation")
            .get(id=processing.id)
        )
        if processing.status != ObservationProcessing.Status.PROCESSING:
            return processing.status == ObservationProcessing.Status.RETRYING

        if processing.attempt_count < _MAX_OBSERVATION_PIPELINE_ATTEMPTS:
            processing.status = ObservationProcessing.Status.RETRYING
            processing.processing_started_at = None
            processing.last_error_code = _STUCK_PROCESSING_RECOVERY_ERROR_CODE
            processing.save(
                update_fields=[
                    "status",
                    "processing_started_at",
                    "last_error_code",
                    "updated_at",
                ]
            )
            _log_observation_processing_outcome(
                processing=processing,
                event="observation_pipeline_stuck_recovered",
                level=logging.WARNING,
            )
            return True

        processing.status = ObservationProcessing.Status.FAILED
        processing.last_error_code = _STUCK_PROCESSING_RECOVERY_ERROR_CODE
        processing.processed_at = timezone.now()
        processing.save(
            update_fields=[
                "status",
                "last_error_code",
                "processed_at",
                "updated_at",
            ]
        )
        _log_observation_processing_outcome(
            processing=processing,
            event="observation_pipeline_failed",
        )
        return False


def _log_observation_processing_skip(*, processing: ObservationProcessing) -> None:
    if processing.status != ObservationProcessing.Status.PROCESSING:
        return

    logger.info(
        "observation_pipeline_skip_in_flight_processing",
        extra=build_observation_processing_log_context(
            processing=processing,
            event="observation_pipeline_skip_in_flight_processing",
        ),
    )


def _log_observation_processing_outcome(
    *,
    processing: ObservationProcessing,
    event: str,
    level: int = logging.WARNING,
) -> None:
    logger.log(
        level,
        event,
        extra=build_observation_processing_log_context(
            processing=processing,
            event=event,
        ),
    )


def _mark_processing_failed(*, processing_id: uuid.UUID, error_code: str) -> None:
    with transaction.atomic():
        processing = (
            ObservationProcessing.objects.select_for_update()
            .select_related("observation")
            .get(id=processing_id)
        )
        processing.status = ObservationProcessing.Status.FAILED
        processing.last_error_code = error_code
        processing.processed_at = timezone.now()
        processing.save(update_fields=["status", "last_error_code", "processed_at", "updated_at"])
    _log_observation_processing_outcome(
        processing=processing,
        event="observation_pipeline_failed",
    )


def _mark_processing_retry_or_failed(*, processing_id: uuid.UUID, error_code: str) -> None:
    with transaction.atomic():
        processing = (
            ObservationProcessing.objects.select_for_update()
            .select_related("observation")
            .get(id=processing_id)
        )
        if processing.attempt_count < _MAX_OBSERVATION_PIPELINE_ATTEMPTS:
            processing.status = ObservationProcessing.Status.RETRYING
            processing.last_error_code = error_code
            processing.save(update_fields=["status", "last_error_code", "updated_at"])
            event = "observation_pipeline_retry_scheduled"
        else:
            processing.status = ObservationProcessing.Status.FAILED
            processing.last_error_code = error_code
            processing.processed_at = timezone.now()
            processing.save(
                update_fields=[
                    "status",
                    "last_error_code",
                    "processed_at",
                    "updated_at",
                ]
            )
            event = "observation_pipeline_failed"
    _log_observation_processing_outcome(processing=processing, event=event)


@transaction.atomic
def pin_signal(*, signal: Signal, membership: EstablishmentMembership) -> Signal:
    if signal.is_pinned:
        return signal
    if signal.status != Signal.Status.OPEN:
        raise SignalStateError("Only open signals can be pinned.")
    now = timezone.now()
    signal.is_pinned = True
    signal.pinned_at = now
    signal.pinned_by_membership = membership
    signal.last_activity_at = now
    signal.save(
        update_fields=[
            "is_pinned",
            "pinned_at",
            "pinned_by_membership",
            "last_activity_at",
            "updated_at",
        ]
    )
    _schedule_signal_invalidation(signal=signal, reason="signal.updated")
    from houston.notifications.scheduling import schedule_signal_pinned_notification

    schedule_signal_pinned_notification(
        signal_id=signal.id,
        actor_membership_id=membership.id,
    )
    return signal


@transaction.atomic
def mark_signal_interesting(
    *,
    signal: Signal,
    actor_membership: EstablishmentMembership | None = None,
) -> Signal:
    locked_self = _lock_signals_by_uuid_order(signal)[0]
    from_status = locked_self.status
    if from_status != Signal.Status.OPEN:
        raise SignalStateError("Only open signals can be marked interesting.")
    from houston.signals.models import SignalResolutionRequest
    from houston.signals.resolution_request_services import (
        cancel_pending_resolution_request_for_signal,
    )

    cancel_pending_resolution_request_for_signal(
        signal=locked_self,
        reason=SignalResolutionRequest.CanceledReason.SIGNAL_MARKED_INTERESTING,
        notify_requester=True,
    )
    now = timezone.now()
    locked_self.status = Signal.Status.INTERESTING
    locked_self.is_pinned = False
    locked_self.pinned_at = None
    locked_self.pinned_by_membership = None
    locked_self.marked_interesting_by_membership = actor_membership
    locked_self.marked_interesting_at = now
    touch_signal_activity(signal=locked_self)
    locked_self.save(
        update_fields=[
            "status",
            "is_pinned",
            "pinned_at",
            "pinned_by_membership",
            "marked_interesting_by_membership",
            "marked_interesting_at",
            "last_activity_at",
            "updated_at",
        ]
    )
    record_signal_lifecycle_event(
        signal=locked_self,
        event_type=SIGNAL_LIFECYCLE_EVENT_MARKED_INTERESTING,
        occurred_at=now,
        actor_membership=actor_membership,
        metadata_safe={
            "from_status": from_status,
            "to_status": Signal.Status.INTERESTING,
        },
    )
    _schedule_signal_invalidation(signal=locked_self, reason="signal.updated")
    return locked_self


@transaction.atomic
def archive_signal(
    *,
    signal: Signal,
    actor_membership: EstablishmentMembership | None = None,
) -> Signal:
    """User archive: interesting → archived. Does not set merged_into."""
    locked_self, related_signals, observation_id = _lock_signal_created_from_set_or_self(
        signal=signal,
    )
    from_status = locked_self.status
    if from_status != Signal.Status.INTERESTING:
        raise SignalStateError("Only interesting signals can be archived.")
    _maybe_delete_created_from_media_under_locks(
        signal=locked_self,
        related_signals=related_signals,
        observation_id=observation_id,
    )
    now = timezone.now()
    locked_self.status = Signal.Status.ARCHIVED
    locked_self.is_pinned = False
    locked_self.pinned_at = None
    locked_self.pinned_by_membership = None
    locked_self.archived_by_membership = actor_membership
    locked_self.archived_at = now
    touch_signal_activity(signal=locked_self)
    locked_self.save(
        update_fields=[
            "status",
            "is_pinned",
            "pinned_at",
            "pinned_by_membership",
            "archived_by_membership",
            "archived_at",
            "last_activity_at",
            "updated_at",
        ]
    )
    record_signal_lifecycle_event(
        signal=locked_self,
        event_type=SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
        occurred_at=now,
        actor_membership=actor_membership,
        metadata_safe={
            "from_status": from_status,
            "to_status": Signal.Status.ARCHIVED,
            "origin": "user_archive",
        },
    )
    _schedule_signal_invalidation(signal=locked_self, reason="signal.updated")
    return locked_self


@transaction.atomic
def unpin_signal(*, signal: Signal) -> Signal:
    signal.is_pinned = False
    signal.pinned_at = None
    signal.pinned_by_membership = None
    touch_signal_activity(signal=signal)
    signal.save(
        update_fields=[
            "is_pinned",
            "pinned_at",
            "pinned_by_membership",
            "last_activity_at",
            "updated_at",
        ]
    )
    _schedule_signal_invalidation(signal=signal, reason="signal.updated")
    return signal


@transaction.atomic
def cancel_signal(
    *,
    signal: Signal,
    actor_membership: EstablishmentMembership | None = None,
) -> Signal:
    locked_self, _, _ = _lock_signal_created_from_set_or_self(signal=signal)
    if locked_self.status == Signal.Status.IN_PROGRESS:
        raise SignalStateError(SIGNAL_IN_PROGRESS_MANUAL_CANCEL_DETAIL)
    from houston.signals.models import SignalResolutionRequest
    from houston.signals.resolution_request_services import (
        cancel_pending_resolution_request_for_signal,
    )

    cancel_pending_resolution_request_for_signal(
        signal=locked_self,
        reason=SignalResolutionRequest.CanceledReason.SIGNAL_CANCELED,
        notify_requester=True,
    )
    result = _transition_active_signal_to_terminal(
        signal=locked_self,
        target_status=Signal.Status.CANCELED,
        actor_membership=actor_membership,
    )
    from houston.notifications.scheduling import schedule_signal_canceled_notification

    schedule_signal_canceled_notification(
        signal_id=result.id,
        actor_membership_id=actor_membership.id if actor_membership is not None else None,
    )
    return result


@transaction.atomic
def resolve_signal(
    *,
    signal: Signal,
    actor_membership: EstablishmentMembership | None = None,
) -> Signal:
    """Manual resolve (API). Refuses in_progress — use action-plan sync instead."""
    original_signal = signal
    locked_self, _, _ = _lock_signal_created_from_set_or_self(signal=signal)
    if locked_self.status == Signal.Status.IN_PROGRESS:
        raise SignalStateError(SIGNAL_IN_PROGRESS_MANUAL_RESOLVE_DETAIL)
    from houston.signals.resolution_request_services import (
        enforce_requester_engagement_or_cancel_pending_on_resolve,
    )

    enforce_requester_engagement_or_cancel_pending_on_resolve(
        signal=locked_self,
        actor_membership=actor_membership,
    )
    result = _resolve_signal_after_lock(
        original_signal=original_signal,
        locked_self=locked_self,
        actor_membership=actor_membership,
        resolution_origin=SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    )
    return result


@transaction.atomic
def resolve_signal_from_execution_sync(*, signal: Signal) -> Signal:
    """Automatic resolve from action-plan execution sync (allows in_progress)."""
    original_signal = signal
    locked_self, _, _ = _lock_signal_created_from_set_or_self(signal=signal)
    from houston.signals.resolution_request_services import (
        enforce_requester_engagement_or_cancel_pending_on_resolve,
    )

    enforce_requester_engagement_or_cancel_pending_on_resolve(
        signal=locked_self,
        actor_membership=None,
    )
    return _resolve_signal_after_lock(
        original_signal=original_signal,
        locked_self=locked_self,
        actor_membership=None,
        resolution_origin=SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN,
    )


def _resolve_signal_after_lock(
    *,
    original_signal: Signal,
    locked_self: Signal,
    actor_membership: EstablishmentMembership | None,
    resolution_origin: str,
) -> Signal:
    from houston.action_plans.services import (
        _cancel_linked_active_executions_for_signal_resolve,
    )

    _cancel_linked_active_executions_for_signal_resolve(
        signal=locked_self,
        actor_membership=actor_membership,
    )
    result = _transition_active_signal_to_terminal(
        signal=locked_self,
        target_status=Signal.Status.RESOLVED,
        actor_membership=actor_membership,
        resolution_origin=resolution_origin,
    )
    from houston.notifications.scheduling import schedule_signal_resolved_notification

    schedule_signal_resolved_notification(
        signal_id=result.id,
        actor_membership_id=actor_membership.id if actor_membership is not None else None,
    )
    # Keep caller-side in-memory Signal up-to-date.
    original_signal.status = result.status
    original_signal.is_pinned = result.is_pinned
    original_signal.pinned_at = result.pinned_at
    original_signal.pinned_by_membership = result.pinned_by_membership
    original_signal.resolved_by_membership = result.resolved_by_membership
    original_signal.resolved_at = result.resolved_at
    original_signal.resolution_origin = result.resolution_origin
    original_signal.last_activity_at = result.last_activity_at
    original_signal.updated_at = result.updated_at
    return result


def _created_from_observation_id_for_signal(*, signal: Signal) -> uuid.UUID | None:
    link = (
        signal.source_observation_links.filter(
            link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        )
        .order_by("observation__created_at", "observation__id")
        .first()
    )
    if link is None:
        return None
    return link.observation_id


def _lock_signal_created_from_set_or_self(
    *,
    signal: Signal,
) -> tuple[Signal, list[Signal], uuid.UUID | None]:
    """Lock CREATED_FROM siblings (or self) in UUID order. Single lock acquisition."""
    observation_id = _created_from_observation_id_for_signal(signal=signal)
    if observation_id is None:
        locked_self = _lock_signals_by_uuid_order(signal)[0]
        return locked_self, [locked_self], None

    related_signals = list(
        Signal.objects.filter(
            source_observation_links__observation_id=observation_id,
            source_observation_links__link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        )
        .select_for_update(of=("self",))
        .order_by("id")
    )
    by_id = {related.id: related for related in related_signals}
    locked_self = by_id.get(signal.id)
    if locked_self is None:
        raise SignalStateError("Signal missing from CREATED_FROM lock set.")
    return locked_self, related_signals, observation_id


def _maybe_delete_created_from_media_under_locks(
    *,
    signal: Signal,
    related_signals: list[Signal],
    observation_id: uuid.UUID | None,
) -> None:
    """Delete CREATED_FROM media when related_signals are already locked."""
    if observation_id is None:
        return

    from houston.observations.media_services import delete_all_observation_media

    active_count = sum(1 for related in related_signals if related.status in ACTIVE_SIGNAL_STATUSES)
    if active_count > 1:
        return
    delete_all_observation_media(observation_id=observation_id)
    prefetched_links = getattr(signal, "created_from_source_links", None)
    if prefetched_links:
        for prefetched_link in prefetched_links:
            observation = prefetched_link.observation
            cache = getattr(observation, "_prefetched_objects_cache", None)
            if cache is not None:
                cache["media_items"] = []


def _transition_active_signal_to_terminal(
    *,
    signal: Signal,
    target_status: str,
    actor_membership: EstablishmentMembership | None = None,
    resolution_origin: str | None = None,
) -> Signal:
    locked_self, related_signals, observation_id = _lock_signal_created_from_set_or_self(
        signal=signal,
    )
    from_status = locked_self.status
    if from_status not in CANCEL_RESOLVE_SIGNAL_STATUSES:
        raise SignalStateError("Only active signals can be canceled or resolved.")
    if from_status == target_status:
        return locked_self
    _maybe_delete_created_from_media_under_locks(
        signal=locked_self,
        related_signals=related_signals,
        observation_id=observation_id,
    )
    now = timezone.now()
    locked_self.status = target_status
    locked_self.is_pinned = False
    locked_self.pinned_at = None
    locked_self.pinned_by_membership = None
    update_fields = [
        "status",
        "is_pinned",
        "pinned_at",
        "pinned_by_membership",
        "last_activity_at",
        "updated_at",
    ]
    event_type = SIGNAL_LIFECYCLE_EVENT_CANCELED
    metadata_safe: dict = {
        "from_status": from_status,
        "to_status": target_status,
    }
    if target_status == Signal.Status.RESOLVED:
        event_type = SIGNAL_LIFECYCLE_EVENT_RESOLVED
        locked_self.resolved_by_membership = actor_membership
        locked_self.resolved_at = now
        locked_self.resolution_origin = resolution_origin
        update_fields.extend(
            ["resolved_by_membership", "resolved_at", "resolution_origin"]
        )
        if resolution_origin is not None:
            metadata_safe["resolution_origin"] = resolution_origin
    elif target_status == Signal.Status.CANCELED:
        locked_self.canceled_by_membership = actor_membership
        locked_self.canceled_at = now
        update_fields.extend(["canceled_by_membership", "canceled_at"])
    touch_signal_activity(signal=locked_self)
    locked_self.save(update_fields=update_fields)
    lifecycle_event = record_signal_lifecycle_event(
        signal=locked_self,
        event_type=event_type,
        occurred_at=now,
        actor_membership=actor_membership,
        metadata_safe=metadata_safe,
    )
    if target_status == Signal.Status.RESOLVED:
        from houston.gamification.services import award_signal_progress_points

        award_signal_progress_points(signal=locked_self, lifecycle_event=lifecycle_event)
    _schedule_signal_invalidation(
        signal=locked_self,
        reason="signal.updated",
    )
    # Keep caller-side in-memory Signal up-to-date.
    # Some call sites (including unit tests) reuse the same Signal instance
    # right after a transition, without always re-fetching from the DB.
    signal.status = locked_self.status
    signal.is_pinned = locked_self.is_pinned
    signal.pinned_at = locked_self.pinned_at
    signal.pinned_by_membership = locked_self.pinned_by_membership
    signal.resolved_by_membership = locked_self.resolved_by_membership
    signal.resolved_at = locked_self.resolved_at
    signal.resolution_origin = locked_self.resolution_origin
    signal.canceled_by_membership = locked_self.canceled_by_membership
    signal.canceled_at = locked_self.canceled_at
    signal.last_activity_at = locked_self.last_activity_at
    signal.updated_at = locked_self.updated_at
    return locked_self


def _schedule_signal_invalidation(*, signal: Signal, reason: str) -> None:
    from houston.realtime.broadcast import schedule_establishment_invalidation

    schedule_establishment_invalidation(
        establishment_id=signal.establishment_id,
        subject_type="signal",
        reason=reason,
        entity_id=signal.id,
    )


QUALIFY_ROUTING_PATCH_FIELDS = frozenset(
    {
        "affected_business_unit_id",
        "responsible_business_unit_id",
        "activity_subject_id",
        "operational_unit_id",
        "issue_focus",
        "expected_action",
    }
)


@dataclass(frozen=True)
class QualifySignalRoutingResult:
    signal: Signal
    qualification_outcome: str
    surviving_signal_id: uuid.UUID
    merged_signal_id: uuid.UUID | None


def _load_active_business_unit(
    *,
    establishment_id: uuid.UUID,
    business_unit_id: uuid.UUID,
) -> BusinessUnit:
    business_unit = BusinessUnit.objects.filter(id=business_unit_id).first()
    if business_unit is None:
        raise SignalValidationError(
            "Unknown business unit.",
            code="invalid_business_unit",
        )
    if business_unit.establishment_id != establishment_id:
        raise SignalValidationError(
            "Business unit belongs to another establishment.",
            code="invalid_business_unit",
        )
    if not business_unit.active:
        raise SignalValidationError(
            "Business unit is inactive.",
            code="inactive_business_unit",
        )
    return business_unit


def _load_active_activity_subject(
    *,
    establishment_id: uuid.UUID,
    activity_subject_id: uuid.UUID,
) -> ActivitySubject:
    subject = (
        ActivitySubject.objects.filter(id=activity_subject_id)
        .select_related("business_unit")
        .first()
    )
    if subject is None:
        raise SignalValidationError(
            "Unknown activity subject.",
            code="invalid_activity_subject",
        )
    if subject.establishment_id != establishment_id:
        raise SignalValidationError(
            "Activity subject belongs to another establishment.",
            code="invalid_activity_subject",
        )
    if not subject.active or not subject.business_unit.active:
        raise SignalValidationError(
            "Activity subject is inactive.",
            code="inactive_activity_subject",
        )
    return subject


def _load_active_operational_unit(
    *,
    establishment_id: uuid.UUID,
    operational_unit_id: uuid.UUID,
) -> OperationalUnit:
    unit = OperationalUnit.objects.filter(id=operational_unit_id).first()
    if unit is None:
        raise SignalValidationError(
            "Unknown operational unit.",
            code="invalid_operational_unit",
        )
    if unit.establishment_id != establishment_id:
        raise SignalValidationError(
            "Operational unit belongs to another establishment.",
            code="invalid_operational_unit",
        )
    if not unit.active:
        raise SignalValidationError(
            "Operational unit is inactive.",
            code="inactive_operational_unit",
        )
    return unit


def _validate_expected_action_value(value: str | None) -> str | None:
    if value is None:
        return None
    valid = {choice.value for choice in ExpectedAction}
    if value not in valid:
        raise SignalValidationError(
            "Invalid expected_action.",
            code="invalid_expected_action",
        )
    return value


def _resolve_patch_entity(
    *,
    establishment_id: uuid.UUID,
    field_name: str,
    value: uuid.UUID | None,
) -> BusinessUnit | ActivitySubject | OperationalUnit | None:
    if value is None:
        return None
    if field_name in {"affected_business_unit_id", "responsible_business_unit_id"}:
        return _load_active_business_unit(
            establishment_id=establishment_id,
            business_unit_id=value,
        )
    if field_name == "activity_subject_id":
        return _load_active_activity_subject(
            establishment_id=establishment_id,
            activity_subject_id=value,
        )
    if field_name == "operational_unit_id":
        return _load_active_operational_unit(
            establishment_id=establishment_id,
            operational_unit_id=value,
        )
    raise SignalValidationError(f"Unknown patch field: {field_name}")


def _apply_routing_patch_to_base(
    *,
    establishment_id: uuid.UUID,
    base_affected: BusinessUnit | None,
    base_responsible: BusinessUnit | None,
    base_subject: ActivitySubject | None,
    base_operational_unit: OperationalUnit | None,
    base_issue_focus: str,
    base_expected_action: str | None,
    patch: dict[str, uuid.UUID | str | None],
) -> tuple[
    BusinessUnit | None,
    BusinessUnit | None,
    ActivitySubject | None,
    OperationalUnit | None,
    str,
    str | None,
]:
    affected = base_affected
    responsible = base_responsible
    subject = base_subject
    operational_unit = base_operational_unit
    issue_focus = base_issue_focus
    expected_action = base_expected_action

    if "affected_business_unit_id" in patch:
        affected = _resolve_patch_entity(
            establishment_id=establishment_id,
            field_name="affected_business_unit_id",
            value=patch["affected_business_unit_id"],  # type: ignore[arg-type]
        )  # type: ignore[assignment]
    if "responsible_business_unit_id" in patch:
        responsible = _resolve_patch_entity(
            establishment_id=establishment_id,
            field_name="responsible_business_unit_id",
            value=patch["responsible_business_unit_id"],  # type: ignore[arg-type]
        )  # type: ignore[assignment]
    if "activity_subject_id" in patch:
        subject = _resolve_patch_entity(
            establishment_id=establishment_id,
            field_name="activity_subject_id",
            value=patch["activity_subject_id"],  # type: ignore[arg-type]
        )  # type: ignore[assignment]
    if "operational_unit_id" in patch:
        operational_unit = _resolve_patch_entity(
            establishment_id=establishment_id,
            field_name="operational_unit_id",
            value=patch["operational_unit_id"],  # type: ignore[arg-type]
        )  # type: ignore[assignment]
    if "issue_focus" in patch:
        raw = patch["issue_focus"]
        if raw is None:
            issue_focus = ""
        else:
            issue_focus = normalize_issue_focus(str(raw))
    if "expected_action" in patch:
        expected_action = _validate_expected_action_value(
            None if patch["expected_action"] is None else str(patch["expected_action"])
        )

    return affected, responsible, subject, operational_unit, issue_focus, expected_action


def _qualification_payload_compatible_with_survivor(
    *,
    survivor: Signal,
    patch: dict[str, uuid.UUID | str | None],
) -> bool:
    (
        affected,
        responsible,
        subject,
        operational_unit,
        issue_focus,
        requested_expected_action,
    ) = _apply_routing_patch_to_base(
        establishment_id=survivor.establishment_id,
        base_affected=survivor.affected_business_unit,
        base_responsible=survivor.responsible_business_unit,
        base_subject=survivor.activity_subject,
        base_operational_unit=survivor.operational_unit,
        base_issue_focus=survivor.issue_focus or "",
        base_expected_action=survivor.expected_action or None,
        patch=patch,
    )
    if (affected.id if affected else None) != survivor.affected_business_unit_id:
        return False
    if (responsible.id if responsible else None) != survivor.responsible_business_unit_id:
        return False
    if (subject.id if subject else None) != survivor.activity_subject_id:
        return False
    if (operational_unit.id if operational_unit else None) != survivor.operational_unit_id:
        return False
    if normalize_issue_focus(issue_focus) != normalize_issue_focus(survivor.issue_focus):
        return False
    effective_expected, _ = _d3_expected_action_decision(
        signal_expected_action=survivor.expected_action or None,
        candidate_expected_action=requested_expected_action,
    )
    return effective_expected == (survivor.expected_action or None)


def _append_qualification_audit(
    *,
    signal: Signal,
    audit_envelope: dict,
) -> None:
    for row in CandidateSignal.objects.filter(result_signal=signal):
        resolution_audit = {**(row.resolution_audit or {})}
        events = list(resolution_audit.get("qualification_events") or [])
        events.append(audit_envelope)
        resolution_audit["qualification_events"] = events
        row.resolution_audit = resolution_audit
        row.save(update_fields=["resolution_audit", "updated_at"])


def _qualification_previous_attention_recipient_ids(
    *,
    source: Signal,
    survivor: Signal | None,
) -> frozenset[uuid.UUID]:
    """Lot 8 E4 baseline under locks: attention(source) [∪ attention(survivor)]."""
    from houston.notifications.recipients import resolve_signal_attention_recipients

    ids = {item.id for item in resolve_signal_attention_recipients(signal=source)}
    if survivor is not None:
        ids.update(item.id for item in resolve_signal_attention_recipients(signal=survivor))
    return frozenset(ids)


def _lock_signals_by_uuid_order(*signals: Signal) -> list[Signal]:
    ordered_ids = sorted({signal.id for signal in signals})
    # of=("self",): avoid FOR UPDATE on nullable outer joins (merged_into).
    locked = list(
        Signal.objects.select_for_update(of=("self",))
        .select_related(
            "affected_business_unit",
            "responsible_business_unit",
            "activity_subject",
            "operational_unit",
            "establishment",
        )
        .filter(id__in=ordered_ids)
        .order_by("id")
    )
    by_id = {signal.id: signal for signal in locked}
    return [by_id[signal_id] for signal_id in ordered_ids]


def merge_signal_into_resolved(
    *,
    source: Signal,
    target: Signal,
    resolution_audit: dict,
    candidate_expected_action: str | None,
) -> Signal:
    """Merge source into target. Caller must hold locks on both in UUID order."""
    if source.id == target.id:
        return target
    if source.merged_into_id == target.id:
        return target

    apply_expected_action_on_aggregation(
        signal=target,
        candidate_expected_action=candidate_expected_action,
        candidate_row=None,
    )

    for link in SignalSourceObservation.objects.filter(signal=source):
        record_source_observation_link(
            signal=target,
            observation=link.observation,
            link_type=SignalSourceObservation.LinkType.MERGED_FROM,
        )

    audit_envelope = {
        "source": "manual_qualification_merged",
        "merged_signal_id": str(source.id),
        "surviving_signal_id": str(target.id),
        "resolution_audit": resolution_audit,
    }
    candidate_ids = list(
        CandidateSignal.objects.filter(result_signal__in=[source, target]).values_list(
            "id",
            flat=True,
        )
    )
    for row in CandidateSignal.objects.filter(id__in=candidate_ids):
        resolution_audit_payload = {**(row.resolution_audit or {})}
        events = list(resolution_audit_payload.get("qualification_events") or [])
        events.append(audit_envelope)
        resolution_audit_payload["qualification_events"] = events
        row.resolution_audit = resolution_audit_payload
        row.save(update_fields=["resolution_audit", "updated_at"])
    CandidateSignal.objects.filter(result_signal=source).update(result_signal=target)

    from_status = source.status
    now = timezone.now()
    source.status = Signal.Status.ARCHIVED
    source.merged_into = target
    source.is_pinned = False
    source.pinned_at = None
    source.pinned_by_membership = None
    source.archived_by_membership = None
    source.archived_at = now
    touch_signal_activity(signal=source)
    source.save(
        update_fields=[
            "status",
            "merged_into",
            "is_pinned",
            "pinned_at",
            "pinned_by_membership",
            "archived_by_membership",
            "archived_at",
            "last_activity_at",
            "updated_at",
        ]
    )
    if from_status != Signal.Status.ARCHIVED:
        record_signal_lifecycle_event(
            signal=source,
            event_type=SIGNAL_LIFECYCLE_EVENT_ARCHIVED,
            occurred_at=now,
            actor_membership=None,
            metadata_safe={
                "from_status": from_status,
                "to_status": Signal.Status.ARCHIVED,
                "origin": "qualify_merge",
                "merged_into_signal_id": target.id,
                "source_signal_id": source.id,
            },
        )
    touch_signal_activity(signal=target)
    target.save(update_fields=["last_activity_at", "updated_at"])
    _schedule_signal_invalidation(signal=source, reason="signal.updated")
    _schedule_signal_invalidation(signal=target, reason="signal.updated")
    return target


@transaction.atomic
def qualify_signal_routing(
    *,
    signal: Signal,
    membership: EstablishmentMembership,
    patch: dict[str, uuid.UUID | str | None],
) -> QualifySignalRoutingResult:
    from houston.signals.permissions import can_qualify_routing

    unknown = set(patch) - QUALIFY_ROUTING_PATCH_FIELDS
    if unknown:
        raise SignalValidationError(
            f"Unsupported qualify fields: {sorted(unknown)}",
            code="invalid_qualify_fields",
        )

    source = (
        Signal.objects.select_related(
            "affected_business_unit",
            "responsible_business_unit",
            "activity_subject",
            "operational_unit",
            "merged_into",
            "establishment",
            "merged_into__affected_business_unit",
            "merged_into__responsible_business_unit",
            "merged_into__activity_subject",
            "merged_into__operational_unit",
        )
        .filter(id=signal.id, establishment_id=membership.establishment_id)
        .first()
    )
    if source is None:
        raise SignalValidationError("Signal not found.", code="signal_not_found")

    # 1–2: idempotence before lifecycle when already merged
    if source.merged_into_id is not None:
        if membership.role == EstablishmentMembership.Role.STAFF:
            raise SignalPermissionError("Permission denied.")
        from houston.establishments.role_constants import ADMIN_ROLES
        from houston.signals.permissions import signal_visible_in_membership_scope
        from houston.signals.selectors import get_signal_for_detail

        survivor = get_signal_for_detail(
            membership=membership,
            signal_id=source.merged_into_id,
        )
        if survivor is None:
            raise SignalPermissionError("Permission denied.")
        # Detail allows general open reads; qualify idempotence still requires BU scope.
        if membership.role not in ADMIN_ROLES and not signal_visible_in_membership_scope(
            membership,
            survivor,
        ):
            raise SignalPermissionError("Permission denied.")
        if _qualification_payload_compatible_with_survivor(survivor=survivor, patch=patch):
            return QualifySignalRoutingResult(
                signal=survivor,
                qualification_outcome="merged",
                surviving_signal_id=survivor.id,
                merged_signal_id=source.id,
            )
        raise SignalAlreadyMergedError("Signal already merged into another signal.")

    # 3: lifecycle active only when not already merged
    if source.status not in ACTIVE_SIGNAL_STATUSES:
        raise SignalStateError("Only active signals can be qualified.")

    (
        affected,
        responsible,
        subject,
        operational_unit,
        issue_focus,
        expected_action,
    ) = _apply_routing_patch_to_base(
        establishment_id=source.establishment_id,
        base_affected=source.affected_business_unit,
        base_responsible=source.responsible_business_unit,
        base_subject=source.activity_subject,
        base_operational_unit=source.operational_unit,
        base_issue_focus=source.issue_focus or "",
        base_expected_action=source.expected_action or None,
        patch=patch,
    )

    # 4: live RBAC with proposed dimensions
    if not can_qualify_routing(
        membership,
        source,
        proposed_affected_business_unit=affected,
        proposed_responsible_business_unit=responsible,
        proposed_activity_subject=subject,
    ):
        raise SignalPermissionError("Permission denied.")

    try:
        resolution = resolve_materialized_routing(
            establishment=source.establishment,
            affected_business_unit=affected,
            responsible_business_unit=responsible,
            activity_subject=subject,
            operational_unit=operational_unit,
        )
    except InvalidSignalClassificationError as exc:
        raise SignalValidationError(str(exc), code="invalid_routing") from exc

    normalized_issue_focus = normalize_issue_focus(issue_focus)
    if resolution.routing_status == Signal.RoutingStatus.RESOLVED:
        try:
            normalized_issue_focus = require_normalized_issue_focus(normalized_issue_focus)
        except SignalPipelineCandidateError as exc:
            raise SignalValidationError(
                "issue_focus is required when routing is resolved.",
                code="invalid_issue_focus",
            ) from exc

    resolved_taxonomy = _resolved_taxonomy_from_resolution(resolution)
    collision: Signal | None = None
    if resolution.routing_status == Signal.RoutingStatus.RESOLVED:
        collision = find_active_signal_for_aggregation(
            establishment_id=source.establishment_id,
            resolved=resolved_taxonomy,
            issue_focus=normalized_issue_focus,
            for_update=False,
        )
        if collision is not None and collision.id == source.id:
            collision = None

    if collision is not None:
        locked = _lock_signals_by_uuid_order(source, collision)
        source = next(item for item in locked if item.id == source.id)
        collision = next(item for item in locked if item.id == collision.id)
        if source.merged_into_id is not None:
            survivor = source.merged_into
            assert survivor is not None
            if _qualification_payload_compatible_with_survivor(survivor=survivor, patch=patch):
                return QualifySignalRoutingResult(
                    signal=survivor,
                    qualification_outcome="merged",
                    surviving_signal_id=survivor.id,
                    merged_signal_id=source.id,
                )
            raise SignalAlreadyMergedError("Signal already merged into another signal.")
        if source.status not in ACTIVE_SIGNAL_STATUSES:
            raise SignalStateError("Only active signals can be qualified.")
        collision = find_active_signal_for_aggregation(
            establishment_id=source.establishment_id,
            resolved=resolved_taxonomy,
            issue_focus=normalized_issue_focus,
            for_update=True,
        )
        if collision is None or collision.id == source.id:
            collision = None
        else:
            locked = _lock_signals_by_uuid_order(source, collision)
            source = next(item for item in locked if item.id == source.id)
            collision = next(item for item in locked if item.id == collision.id)

    if collision is not None:
        # Lot 8 E4: under source+survivor locks, baseline = attention(source) ∪ attention(survivor).
        previous_attention_recipient_ids = _qualification_previous_attention_recipient_ids(
            source=source,
            survivor=collision,
        )
        survivor = merge_signal_into_resolved(
            source=source,
            target=collision,
            resolution_audit={
                **resolution.resolution_audit,
                "event": "manual_qualification_merged",
            },
            candidate_expected_action=expected_action,
        )
        from houston.notifications.scheduling import schedule_signal_qualified_notification

        schedule_signal_qualified_notification(
            signal_id=survivor.id,
            actor_membership_id=membership.id,
            previous_recipient_ids=previous_attention_recipient_ids,
        )
        return QualifySignalRoutingResult(
            signal=survivor,
            qualification_outcome="merged",
            surviving_signal_id=survivor.id,
            merged_signal_id=source.id,
        )

    # Update in place (lock source alone)
    locked_source = _lock_signals_by_uuid_order(source)[0]
    if locked_source.merged_into_id is not None:
        survivor = locked_source.merged_into
        assert survivor is not None
        if _qualification_payload_compatible_with_survivor(survivor=survivor, patch=patch):
            return QualifySignalRoutingResult(
                signal=survivor,
                qualification_outcome="merged",
                surviving_signal_id=survivor.id,
                merged_signal_id=locked_source.id,
            )
        raise SignalAlreadyMergedError("Signal already merged into another signal.")
    if locked_source.status not in ACTIVE_SIGNAL_STATUSES:
        raise SignalStateError("Only active signals can be qualified.")

    previous_attention_recipient_ids = _qualification_previous_attention_recipient_ids(
        source=locked_source,
        survivor=None,
    )

    locked_source.affected_business_unit = resolution.affected_business_unit
    locked_source.responsible_business_unit = resolution.responsible_business_unit
    locked_source.activity_subject = resolution.activity_subject
    locked_source.operational_unit = resolution.operational_unit
    locked_source.routing_status = resolution.routing_status
    locked_source.issue_focus = normalized_issue_focus
    try:
        with transaction.atomic():
            touch_signal_activity(signal=locked_source)
            locked_source.save(
                update_fields=[
                    "affected_business_unit",
                    "responsible_business_unit",
                    "activity_subject",
                    "operational_unit",
                    "routing_status",
                    "issue_focus",
                    "last_activity_at",
                    "updated_at",
                ]
            )
    except IntegrityError as exc:
        if not _is_active_aggregation_unique_violation(exc):
            raise
        collision = find_active_signal_for_aggregation(
            establishment_id=locked_source.establishment_id,
            resolved=resolved_taxonomy,
            issue_focus=normalized_issue_focus,
            for_update=True,
        )
        if collision is None or collision.id == locked_source.id:
            raise
        locked = _lock_signals_by_uuid_order(locked_source, collision)
        locked_source = next(item for item in locked if item.id == locked_source.id)
        collision = next(item for item in locked if item.id == collision.id)
        previous_attention_recipient_ids = _qualification_previous_attention_recipient_ids(
            source=locked_source,
            survivor=collision,
        )
        survivor = merge_signal_into_resolved(
            source=locked_source,
            target=collision,
            resolution_audit={
                **resolution.resolution_audit,
                "event": "manual_qualification_merged",
            },
            candidate_expected_action=expected_action,
        )
        from houston.notifications.scheduling import schedule_signal_qualified_notification

        schedule_signal_qualified_notification(
            signal_id=survivor.id,
            actor_membership_id=membership.id,
            previous_recipient_ids=previous_attention_recipient_ids,
        )
        return QualifySignalRoutingResult(
            signal=survivor,
            qualification_outcome="merged",
            surviving_signal_id=survivor.id,
            merged_signal_id=locked_source.id,
        )

    apply_expected_action_on_aggregation(
        signal=locked_source,
        candidate_expected_action=expected_action,
        candidate_row=None,
    )
    _append_qualification_audit(
        signal=locked_source,
        audit_envelope={
            "source": "manual_qualification",
            "signal_id": str(locked_source.id),
            "resolution_audit": resolution.resolution_audit,
        },
    )
    _schedule_signal_invalidation(signal=locked_source, reason="signal.updated")
    from houston.notifications.scheduling import schedule_signal_qualified_notification

    schedule_signal_qualified_notification(
        signal_id=locked_source.id,
        actor_membership_id=membership.id,
        previous_recipient_ids=previous_attention_recipient_ids,
    )
    locked_source.refresh_from_db()
    return QualifySignalRoutingResult(
        signal=locked_source,
        qualification_outcome="updated",
        surviving_signal_id=locked_source.id,
        merged_signal_id=None,
    )
