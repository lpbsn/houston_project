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
from houston.observations.models import Observation, ObservationProcessing
from houston.signals.aggregation_eval import (
    count_active_taxonomy_peers_with_different_focus,
    format_taxonomy_bucket_key,
)
from houston.signals.classification_fallback import try_apply_responsible_affected_fallback
from houston.signals.constants import (
    ACTIVE_SIGNAL_STATUSES,
    AI_ISSUE_FOCUS_MAX_LENGTH,
    AI_LOCATION_TEXT_MAX_LENGTH,
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    MAX_CANDIDATES_PER_OBSERVATION,
    STRUCTURED_SUMMARY_SHORT_MAX_LENGTH,
)
from houston.signals.exceptions import (
    SignalBusinessConflictError,
    SignalPipelineCandidateError,
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

_STUCK_PROCESSING_RECOVERY_ERROR_CODE = "stuck_processing_recovered"
_MAX_OBSERVATION_PIPELINE_ATTEMPTS = 3


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


def is_legacy_empty_issue_focus(value: str | None) -> bool:
    return not normalize_issue_focus(value)


def require_normalized_issue_focus(value: str | None) -> str:
    normalized = normalize_issue_focus(value)
    if not normalized:
        raise SignalPipelineCandidateError("issue_focus is required after normalization.")
    return normalized


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
    return (
        f"{affected_id}|{responsible_id}|{subject_id}|{unit_token}|{issue_focus}"
    )


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
        issue_focus=require_normalized_issue_focus(candidate.issue_focus),
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
    normalized_issue_focus: str | None = None,
) -> Signal:
    now = timezone.now()
    update_fields = ["last_activity_at", "updated_at"]
    signal.last_activity_at = now
    if normalized_issue_focus and is_legacy_empty_issue_focus(signal.issue_focus):
        signal.issue_focus = normalized_issue_focus
        update_fields.insert(0, "issue_focus")
    signal.save(update_fields=update_fields)
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
    )
    if resolved.operational_unit is None:
        queryset = queryset.filter(operational_unit__isnull=True)
    else:
        queryset = queryset.filter(operational_unit=resolved.operational_unit)

    if for_update:
        queryset = queryset.select_for_update()

    return queryset.order_by("-last_activity_at").first()


def find_active_legacy_signal_for_aggregation(
    *,
    establishment_id: uuid.UUID,
    resolved: ResolvedTaxonomy,
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
        issue_focus="",
        status__in=ACTIVE_SIGNAL_STATUSES,
    )
    if resolved.operational_unit is None:
        queryset = queryset.filter(operational_unit__isnull=True)
    else:
        queryset = queryset.filter(operational_unit=resolved.operational_unit)

    matches = list(queryset.select_for_update().order_by("-last_activity_at")[:2])
    if len(matches) != 1:
        return None
    return matches[0]


def _signal_taxonomy_matches(*, signal: Signal, resolved: ResolvedTaxonomy) -> bool:
    assert resolved.affected_business_unit is not None
    assert resolved.responsible_business_unit is not None
    assert resolved.activity_subject is not None
    if signal.affected_business_unit_id != resolved.affected_business_unit.id:
        return False
    if signal.responsible_business_unit_id != resolved.responsible_business_unit.id:
        return False
    if signal.activity_subject_id != resolved.activity_subject.id:
        return False
    if resolved.operational_unit is None:
        return signal.operational_unit_id is None
    return signal.operational_unit_id == resolved.operational_unit.id


def _try_resolve_hint_signal(
    *,
    establishment_id: uuid.UUID,
    candidate: PipelineCandidateOutput,
    resolved: ResolvedTaxonomy,
    normalized_issue_focus: str,
    for_update: bool = False,
) -> tuple[Signal | None, str | None]:
    if not candidate.aggregate_into_signal_id:
        return None, None

    try:
        hint_id = uuid.UUID(str(candidate.aggregate_into_signal_id))
    except (TypeError, ValueError):
        return None, "invalid_hint_id"

    queryset = Signal.objects.filter(id=hint_id, establishment_id=establishment_id)
    if for_update:
        queryset = queryset.select_for_update()
    signal = queryset.first()
    if signal is None:
        return None, "hint_signal_not_found"
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        return None, "hint_signal_not_active"
    if not _signal_taxonomy_matches(signal=signal, resolved=resolved):
        return None, "hint_taxonomy_mismatch"
    if normalize_issue_focus(signal.issue_focus) != normalized_issue_focus:
        return None, "hint_issue_focus_mismatch"
    return signal, None


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
        issue_focus=require_normalized_issue_focus(candidate.issue_focus),
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        ai_aggregate_hint_signal_id=hint_id,
        outcome=CandidateSignal.Outcome.PENDING,
    )


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

    seen_keys: set[tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID | None, str]] = set()
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
                issue_focus=require_normalized_issue_focus(candidate.issue_focus),
                schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                outcome=CandidateSignal.Outcome.REJECTED,
            )
            rejected_count += 1
            continue

        assert resolved.affected_business_unit is not None
        assert resolved.responsible_business_unit is not None
        assert resolved.activity_subject is not None
        normalized_issue_focus = require_normalized_issue_focus(candidate.issue_focus)
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
        if dedupe_key in seen_keys:
            row = _persist_pending_candidate(
                observation=observation,
                candidate=candidate,
                resolved=resolved,
            )
            row.outcome = CandidateSignal.Outcome.REJECTED
            row.save(update_fields=["outcome", "updated_at"])
            rejected_count += 1
            _log_pipeline_candidate_applied(
                observation=observation,
                aggregation_key=format_aggregation_key(dedupe_key),
                hint_used=False,
                hint_rejected_reason="",
                candidate_outcome=CandidateSignal.Outcome.REJECTED,
                issue_focus=str(eval_log_fields["issue_focus"]),
                taxonomy_bucket_key=str(eval_log_fields["taxonomy_bucket_key"]),
            )
            continue
        seen_keys.add(dedupe_key)

        row = _persist_pending_candidate(
            observation=observation,
            candidate=candidate,
            resolved=resolved,
        )

        hint_signal, hint_rejected_reason = _try_resolve_hint_signal(
            establishment_id=observation.establishment_id,
            candidate=candidate,
            resolved=resolved,
            normalized_issue_focus=normalized_issue_focus,
            for_update=True,
        )
        if hint_signal is not None:
            signal = aggregate_candidate_into_signal(
                signal=hint_signal,
                observation=observation,
                normalized_issue_focus=normalized_issue_focus,
            )
            row.outcome = CandidateSignal.Outcome.AGGREGATED_SIGNAL
            row.result_signal = signal
            row.save(update_fields=["outcome", "result_signal", "updated_at"])
            aggregated_count += 1
            _log_pipeline_candidate_applied(
                observation=observation,
                aggregation_key=format_aggregation_key(dedupe_key),
                hint_used=True,
                hint_rejected_reason="",
                candidate_outcome=CandidateSignal.Outcome.AGGREGATED_SIGNAL,
                issue_focus=str(eval_log_fields["issue_focus"]),
                taxonomy_bucket_key=str(eval_log_fields["taxonomy_bucket_key"]),
                aggregation_match_mode="hint",
            )
            continue

        existing = find_active_signal_for_aggregation(
            establishment_id=observation.establishment_id,
            resolved=resolved,
            issue_focus=normalized_issue_focus,
            for_update=True,
        )
        if existing is not None:
            signal = aggregate_candidate_into_signal(
                signal=existing,
                observation=observation,
                normalized_issue_focus=normalized_issue_focus,
            )
            row.outcome = CandidateSignal.Outcome.AGGREGATED_SIGNAL
            row.result_signal = signal
            row.save(update_fields=["outcome", "result_signal", "updated_at"])
            aggregated_count += 1
            _log_pipeline_candidate_applied(
                observation=observation,
                aggregation_key=format_aggregation_key(dedupe_key),
                hint_used=False,
                hint_rejected_reason=hint_rejected_reason or "",
                candidate_outcome=CandidateSignal.Outcome.AGGREGATED_SIGNAL,
                issue_focus=str(eval_log_fields["issue_focus"]),
                taxonomy_bucket_key=str(eval_log_fields["taxonomy_bucket_key"]),
                aggregation_match_mode="exact",
            )
            continue

        legacy_existing = find_active_legacy_signal_for_aggregation(
            establishment_id=observation.establishment_id,
            resolved=resolved,
        )
        if legacy_existing is not None:
            signal = aggregate_candidate_into_signal(
                signal=legacy_existing,
                observation=observation,
                normalized_issue_focus=normalized_issue_focus,
            )
            row.outcome = CandidateSignal.Outcome.AGGREGATED_SIGNAL
            row.result_signal = signal
            row.save(update_fields=["outcome", "result_signal", "updated_at"])
            aggregated_count += 1
            _log_pipeline_candidate_applied(
                observation=observation,
                aggregation_key=format_aggregation_key(dedupe_key),
                hint_used=False,
                hint_rejected_reason=hint_rejected_reason or "",
                candidate_outcome=CandidateSignal.Outcome.AGGREGATED_SIGNAL,
                issue_focus=str(eval_log_fields["issue_focus"]),
                taxonomy_bucket_key=str(eval_log_fields["taxonomy_bucket_key"]),
                aggregation_match_mode="legacy_fallback",
            )
            continue

        create_eval_log_fields = _issue_focus_eval_log_fields(
            establishment_id=observation.establishment_id,
            resolved=resolved,
            normalized_issue_focus=normalized_issue_focus,
            include_peer_count=True,
        )
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
        _log_pipeline_candidate_applied(
            observation=observation,
            aggregation_key=format_aggregation_key(dedupe_key),
            hint_used=False,
            hint_rejected_reason=hint_rejected_reason or "",
            candidate_outcome=CandidateSignal.Outcome.CREATED_SIGNAL,
            issue_focus=str(create_eval_log_fields["issue_focus"]),
            taxonomy_bucket_key=str(create_eval_log_fields["taxonomy_bucket_key"]),
            active_taxonomy_peer_count=int(create_eval_log_fields["active_taxonomy_peer_count"]),
        )

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


def recover_stuck_observation_processing_batch() -> int:
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
        if _try_recover_stuck_processing(processing=processing):
            acted_on += 1
            continue
        processing.refresh_from_db()
        if processing.status == ObservationProcessing.Status.FAILED:
            acted_on += 1
    return acted_on


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
    except ObservationPipelineSkippedError:
        with transaction.atomic():
            processing = ObservationProcessing.objects.select_for_update().get(id=processing.id)
            apply_result = apply_pipeline_output(
                observation=observation,
                output=ObservationPipelineOutput(
                    schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                    candidates=[],
                ),
            )
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
        processing.refresh_from_db()
        _log_observation_pipeline_completed(
            observation=observation,
            processing=processing,
            pipeline_started_at=pipeline_started_at,
            apply_result=apply_result,
            apply_duration_ms=0,
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
def set_signal_urgency(
    *,
    signal: Signal,
    urgency: str,
    actor_membership: EstablishmentMembership | None = None,
) -> Signal:
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        raise SignalStateError("Urgency can only be changed for active signals.")
    if urgency not in {Signal.Urgency.NORMAL, Signal.Urgency.HIGH}:
        raise SignalValidationError("Invalid urgency value.")
    previous_urgency = signal.urgency
    signal.urgency = urgency
    touch_signal_activity(signal=signal)
    signal.save(update_fields=["urgency", "last_activity_at", "updated_at"])
    _schedule_signal_invalidation(signal=signal, reason="signal.updated")
    if previous_urgency != Signal.Urgency.HIGH and urgency == Signal.Urgency.HIGH:
        from houston.notifications.scheduling import schedule_signal_urgency_changed_notification

        schedule_signal_urgency_changed_notification(
            signal_id=signal.id,
            actor_membership_id=actor_membership.id if actor_membership is not None else None,
        )
    return signal


@transaction.atomic
def cancel_signal(
    *,
    signal: Signal,
    actor_membership: EstablishmentMembership | None = None,
) -> Signal:
    result = _transition_active_signal_to_terminal(
        signal=signal,
        target_status=Signal.Status.CANCELED,
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
    from houston.actions.constants import ACTIVE_ACTION_STATUSES as ACTIVE_LINKED_ACTION_STATUSES
    from houston.actions.models import Action

    if Action.objects.filter(
        signal_id=signal.id,
        status__in=ACTIVE_LINKED_ACTION_STATUSES,
    ).exists():
        raise SignalBusinessConflictError(
            "Cannot resolve signal while linked actions are still active."
        )
    result = _transition_active_signal_to_terminal(
        signal=signal,
        target_status=Signal.Status.RESOLVED,
        reset_high_urgency=True,
    )
    from houston.notifications.scheduling import schedule_signal_resolved_notification

    schedule_signal_resolved_notification(
        signal_id=result.id,
        actor_membership_id=actor_membership.id if actor_membership is not None else None,
    )
    return result


def _delete_created_from_media_for_signal_terminal(*, signal: Signal) -> None:
    from houston.observations.media_services import delete_all_observation_media

    link = (
        signal.source_observation_links.filter(
            link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        )
        .order_by("observation__created_at", "observation__id")
        .first()
    )
    if link is None:
        return

    observation_id = link.observation_id
    related_signals = list(
        Signal.objects.filter(
            source_observation_links__observation_id=observation_id,
            source_observation_links__link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        )
        .select_for_update()
        .order_by("id")
    )
    active_count = sum(
        1 for related in related_signals if related.status in ACTIVE_SIGNAL_STATUSES
    )
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
    reset_high_urgency: bool = False,
) -> Signal:
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        raise SignalStateError("Only active signals can be canceled or resolved.")
    _delete_created_from_media_for_signal_terminal(signal=signal)
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
    _schedule_signal_invalidation(signal=signal, reason="signal.updated")
    return signal


def _schedule_signal_invalidation(*, signal: Signal, reason: str) -> None:
    from houston.realtime.broadcast import schedule_establishment_invalidation

    schedule_establishment_invalidation(
        establishment_id=signal.establishment_id,
        subject_type="signal",
        reason=reason,
        entity_id=signal.id,
    )
