from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction
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
    build_observation_processing_log_context,
    observation_processing_duration_seconds,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    EstablishmentMembership,
    OperationalUnit,
)
from houston.observations.models import Observation, ObservationProcessing
from houston.signals.classification_fallback import try_apply_responsible_affected_fallback
from houston.signals.constants import (
    ACTIVE_SIGNAL_STATUSES,
    AI_LOCATION_TEXT_MAX_LENGTH,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    MAX_CANDIDATES_PER_OBSERVATION,
    STRUCTURED_SUMMARY_SHORT_MAX_LENGTH,
)
from houston.signals.exceptions import (
    SignalBusinessConflictError,
    SignalStateError,
    SignalValidationError,
)
from houston.signals.models import CandidateSignal, Signal, SignalSourceObservation
from houston.signals.signal_classification import (
    InvalidSignalClassificationError,
    validate_signal_classification,
)

if TYPE_CHECKING:
    from houston.ai.observation_pipeline import ObservationPipelineProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedTaxonomy:
    operational_unit: OperationalUnit | None
    affected_business_unit: BusinessUnit | None = None
    responsible_business_unit: BusinessUnit | None = None
    activity_subject: ActivitySubject | None = None


def normalize_location_text(value: str | None) -> str:
    normalized = (value or "").strip()
    if not normalized:
        return ""
    if len(normalized) > AI_LOCATION_TEXT_MAX_LENGTH:
        return normalized[:AI_LOCATION_TEXT_MAX_LENGTH]
    return normalized


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
) -> Signal:
    now = timezone.now()
    location_text = resolve_signal_location_text(
        candidate=candidate,
        resolved=resolved,
        observation=observation,
    )

    signal = Signal.objects.create(
        establishment=observation.establishment,
        operational_unit=resolved.operational_unit,
        affected_business_unit=resolved.affected_business_unit,
        responsible_business_unit=resolved.responsible_business_unit,
        activity_subject=resolved.activity_subject,
        status=Signal.Status.OPEN,
        urgency=Signal.Urgency.NORMAL,
        title=title.strip(),
        structured_summary=structured_summary.strip(),
        location_text=location_text,
        last_activity_at=now,
    )
    record_source_observation_link(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    return signal


@transaction.atomic
def aggregate_candidate_into_signal(
    *,
    signal: Signal,
    observation: Observation,
) -> Signal:
    touch_signal_activity(signal=signal)
    record_source_observation_link(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )
    return signal


def _candidate_dedupe_key(
    *,
    affected_business_unit_id: uuid.UUID,
    responsible_business_unit_id: uuid.UUID,
    activity_subject_id: uuid.UUID,
    unit_id: uuid.UUID | None,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID | None]:
    return (
        affected_business_unit_id,
        responsible_business_unit_id,
        activity_subject_id,
        unit_id,
    )


def _resolve_activity_subject(
    *,
    establishment_id: uuid.UUID,
    business_unit: BusinessUnit | None,
    activity_subject_key: str,
) -> ActivitySubject | None:
    if business_unit is None:
        return None
    subject = ActivitySubject.objects.filter(
        establishment_id=establishment_id,
        normalized_name=activity_subject_key,
        active=True,
        business_unit=business_unit,
    ).first()
    if subject is not None:
        return subject
    return ActivitySubject.objects.filter(
        establishment_id=establishment_id,
        business_unit=business_unit,
        active=True,
        label__iexact=activity_subject_key,
    ).first()


def resolve_taxonomy_from_candidate(
    *,
    establishment_id: uuid.UUID,
    candidate: PipelineCandidateOutput,
) -> ResolvedTaxonomy:
    return _resolve_v3_candidate(establishment_id=establishment_id, candidate=candidate)


def _resolve_v3_candidate(
    *,
    establishment_id: uuid.UUID,
    candidate: PipelineCandidateOutput,
) -> ResolvedTaxonomy:
    affected = BusinessUnit.objects.filter(
        establishment_id=establishment_id,
        key=candidate.affected_business_unit_key,
        active=True,
    ).first()
    if affected is None:
        raise SignalValidationError("Invalid affected business unit key.")

    responsible = BusinessUnit.objects.filter(
        establishment_id=establishment_id,
        key=candidate.responsible_business_unit_key,
        active=True,
    ).first()
    activity_subject = _resolve_activity_subject(
        establishment_id=establishment_id,
        business_unit=responsible,
        activity_subject_key=candidate.activity_subject_key,
    )
    subject_under_affected = _resolve_activity_subject(
        establishment_id=establishment_id,
        business_unit=affected,
        activity_subject_key=candidate.activity_subject_key,
    )

    establishment = affected.establishment

    if responsible is None:
        fallback = try_apply_responsible_affected_fallback(
            establishment=establishment,
            affected=affected,
            responsible=None,
            activity_subject=None,
            subject_under_affected=subject_under_affected,
        )
        if fallback is None:
            raise SignalValidationError("Invalid responsible business unit key.")
        resolved_affected = fallback.affected_business_unit
        resolved_responsible = fallback.responsible_business_unit
        resolved_subject = fallback.activity_subject
    elif activity_subject is None:
        raise SignalValidationError("activity_subject must belong to responsible_business_unit.")
    else:
        if activity_subject.business_unit_id != responsible.id:
            raise SignalValidationError(
                "activity_subject must belong to responsible_business_unit."
            )
        try:
            validate_signal_classification(
                establishment=establishment,
                affected_business_unit=affected,
                responsible_business_unit=responsible,
                activity_subject=activity_subject,
            )
        except InvalidSignalClassificationError as exc:
            raise SignalValidationError(str(exc)) from exc
        resolved_affected = affected
        resolved_responsible = responsible
        resolved_subject = activity_subject

    unit = None
    if candidate.operational_unit_key:
        unit = OperationalUnit.objects.filter(
            establishment_id=establishment_id,
            key=candidate.operational_unit_key,
            active=True,
        ).first()

    return ResolvedTaxonomy(
        operational_unit=unit,
        affected_business_unit=resolved_affected,
        responsible_business_unit=resolved_responsible,
        activity_subject=resolved_subject,
    )


def find_active_signal_for_aggregation(
    *,
    establishment_id: uuid.UUID,
    resolved: ResolvedTaxonomy,
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
        status__in=ACTIVE_SIGNAL_STATUSES,
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
    resolved: ResolvedTaxonomy | None,
) -> CandidateSignal:
    hint_id = None
    if candidate.aggregate_into_signal_id:
        try:
            hint_id = uuid.UUID(str(candidate.aggregate_into_signal_id))
        except (TypeError, ValueError):
            hint_id = None

    return CandidateSignal.objects.create(
        observation=observation,
        establishment=observation.establishment,
        operational_unit=resolved.operational_unit if resolved else None,
        affected_business_unit=resolved.affected_business_unit if resolved else None,
        responsible_business_unit=resolved.responsible_business_unit if resolved else None,
        activity_subject=resolved.activity_subject if resolved else None,
        location_text=normalize_location_text(candidate.location_text),
        title=candidate.title.strip(),
        structured_summary=candidate.structured_summary.strip(),
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        ai_aggregate_hint_signal_id=hint_id,
        outcome=CandidateSignal.Outcome.PENDING,
    )


@transaction.atomic
def apply_pipeline_output(
    *,
    observation: Observation,
    output: ObservationPipelineOutput,
) -> ObservationProcessing.Outcome:
    candidates = output.candidates[:MAX_CANDIDATES_PER_OBSERVATION]
    if not candidates:
        return ObservationProcessing.Outcome.NO_SIGNAL_CREATED

    seen_keys: set[tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID | None]] = set()
    created_count = 0
    aggregated_count = 0
    rejected_count = 0

    for candidate in candidates:
        try:
            resolved = resolve_taxonomy_from_candidate(
                establishment_id=observation.establishment_id,
                candidate=candidate,
            )
        except SignalValidationError:
            CandidateSignal.objects.create(
                observation=observation,
                establishment=observation.establishment,
                title=candidate.title.strip()[:200],
                structured_summary=candidate.structured_summary.strip()[:2000],
                schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                outcome=CandidateSignal.Outcome.REJECTED,
            )
            rejected_count += 1
            continue

        assert resolved.affected_business_unit is not None
        assert resolved.responsible_business_unit is not None
        assert resolved.activity_subject is not None
        dedupe_key = _candidate_dedupe_key(
            affected_business_unit_id=resolved.affected_business_unit.id,
            responsible_business_unit_id=resolved.responsible_business_unit.id,
            activity_subject_id=resolved.activity_subject.id,
            unit_id=resolved.operational_unit.id if resolved.operational_unit else None,
        )
        if dedupe_key in seen_keys:
            row = _persist_pending_candidate(
                observation=observation,
                candidate=candidate,
                resolved=resolved,
            )
            row.outcome = CandidateSignal.Outcome.REJECTED
            row.save(update_fields=["outcome", "updated_at"])
            rejected_count += 1
            continue
        seen_keys.add(dedupe_key)

        row = _persist_pending_candidate(
            observation=observation,
            candidate=candidate,
            resolved=resolved,
        )

        existing = find_active_signal_for_aggregation(
            establishment_id=observation.establishment_id,
            resolved=resolved,
            for_update=True,
        )
        if existing is not None:
            signal = aggregate_candidate_into_signal(signal=existing, observation=observation)
            row.outcome = CandidateSignal.Outcome.AGGREGATED_SIGNAL
            row.result_signal = signal
            row.save(update_fields=["outcome", "result_signal", "updated_at"])
            aggregated_count += 1
            continue

        signal = create_signal_from_candidate(
            observation=observation,
            candidate=candidate,
            resolved=resolved,
            title=candidate.title,
            structured_summary=candidate.structured_summary,
        )
        row.outcome = CandidateSignal.Outcome.CREATED_SIGNAL
        row.result_signal = signal
        row.save(update_fields=["outcome", "result_signal", "updated_at"])
        created_count += 1

    if created_count == 0 and aggregated_count == 0:
        if rejected_count == len(candidates):
            return ObservationProcessing.Outcome.NO_SIGNAL_CREATED
        return ObservationProcessing.Outcome.NO_SIGNAL_CREATED

    if created_count > 0 and aggregated_count > 0:
        return ObservationProcessing.Outcome.SIGNALS_CREATED
    if aggregated_count > 0:
        return ObservationProcessing.Outcome.SIGNAL_AGGREGATED
    return ObservationProcessing.Outcome.SIGNALS_CREATED


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

    try:
        output = call_observation_pipeline(
            observation=observation,
            provider=provider,
        )
    except ObservationPipelineSkippedError:
        with transaction.atomic():
            processing = ObservationProcessing.objects.select_for_update().get(id=processing.id)
            outcome = apply_pipeline_output(
                observation=observation,
                output=ObservationPipelineOutput(
                    schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                    candidates=[],
                ),
            )
            processing.status = ObservationProcessing.Status.PROCESSED
            processing.processed_at = timezone.now()
            processing.outcome = outcome
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

    with transaction.atomic():
        processing = ObservationProcessing.objects.select_for_update().get(id=processing.id)
        outcome = apply_pipeline_output(observation=observation, output=output)
        processing.status = ObservationProcessing.Status.PROCESSED
        processing.processed_at = timezone.now()
        processing.outcome = outcome
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


def _log_observation_processing_skip(*, processing: ObservationProcessing) -> None:
    if processing.status != ObservationProcessing.Status.PROCESSING:
        return

    duration = observation_processing_duration_seconds(processing=processing)
    stuck_threshold = settings.HOUSTON_OBSERVATION_PROCESSING_STUCK_WARNING_SECONDS
    is_stuck = duration is not None and duration >= stuck_threshold
    log_context = build_observation_processing_log_context(
        processing=processing,
        event=(
            "observation_pipeline_stuck_processing"
            if is_stuck
            else "observation_pipeline_skip_in_flight_processing"
        ),
    )
    if is_stuck:
        logger.warning("observation_pipeline_stuck_processing", extra=log_context)
    else:
        logger.info("observation_pipeline_skip_in_flight_processing", extra=log_context)


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
        if processing.attempt_count < 3:
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
    return signal


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
    return signal


@transaction.atomic
def set_signal_urgency(*, signal: Signal, urgency: str) -> Signal:
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        raise SignalStateError("Urgency can only be changed for active signals.")
    if urgency not in {Signal.Urgency.NORMAL, Signal.Urgency.HIGH}:
        raise SignalValidationError("Invalid urgency value.")
    signal.urgency = urgency
    touch_signal_activity(signal=signal)
    signal.save(update_fields=["urgency", "last_activity_at", "updated_at"])
    return signal


@transaction.atomic
def cancel_signal(*, signal: Signal) -> Signal:
    return _transition_active_signal_to_terminal(
        signal=signal,
        target_status=Signal.Status.CANCELED,
    )


@transaction.atomic
def resolve_signal(*, signal: Signal) -> Signal:
    from houston.actions.constants import ACTIVE_ACTION_STATUSES as ACTIVE_LINKED_ACTION_STATUSES
    from houston.actions.models import Action

    if Action.objects.filter(
        signal_id=signal.id,
        status__in=ACTIVE_LINKED_ACTION_STATUSES,
    ).exists():
        raise SignalBusinessConflictError(
            "Cannot resolve signal while linked actions are still active."
        )
    return _transition_active_signal_to_terminal(
        signal=signal,
        target_status=Signal.Status.RESOLVED,
        reset_high_urgency=True,
    )


def _transition_active_signal_to_terminal(
    *,
    signal: Signal,
    target_status: str,
    reset_high_urgency: bool = False,
) -> Signal:
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        raise SignalStateError("Only active signals can be canceled or resolved.")
    signal.status = target_status
    signal.is_pinned = False
    signal.pinned_at = None
    signal.pinned_by_membership = None
    update_fields = [
        "status",
        "is_pinned",
        "pinned_at",
        "pinned_by_membership",
        "last_activity_at",
        "updated_at",
    ]
    if reset_high_urgency and signal.urgency == Signal.Urgency.HIGH:
        signal.urgency = Signal.Urgency.NORMAL
        update_fields.append("urgency")
    touch_signal_activity(signal=signal)
    signal.save(update_fields=update_fields)
    return signal
