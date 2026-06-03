from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from django.db.models import F

from houston.observations.models import Observation, ObservationProcessing
from houston.signals.models import CandidateSignal, Signal

UxStatus = Literal[
    "analysis_queued",
    "analysis_processing",
    "analysis_retrying",
    "signal_created",
    "signal_updated",
    "no_signal_created",
    "analysis_failed",
]


@dataclass(frozen=True)
class ObservationProcessingSignalSummary:
    id: uuid.UUID
    title: str
    operational_module_key: str
    operational_module_label: str
    operational_domain_key: str
    operational_domain_label: str
    operational_subject_key: str
    operational_subject_label: str
    location_text: str


@dataclass(frozen=True)
class ObservationProcessingStatusProjection:
    observation_id: uuid.UUID
    status: str
    outcome: str
    signal_ids: list[uuid.UUID]
    signals: list[ObservationProcessingSignalSummary]
    last_error_code: str
    ux_status: UxStatus
    created_at: object
    updated_at: object
    processed_at: object | None


def resolve_ux_status(*, status: str, outcome: str) -> UxStatus:
    if status == ObservationProcessing.Status.QUEUED:
        return "analysis_queued"
    if status == ObservationProcessing.Status.PROCESSING:
        return "analysis_processing"
    if status == ObservationProcessing.Status.RETRYING:
        return "analysis_retrying"
    if status == ObservationProcessing.Status.FAILED:
        return "analysis_failed"
    if status == ObservationProcessing.Status.PROCESSED:
        if outcome == ObservationProcessing.Outcome.SIGNAL_AGGREGATED:
            return "signal_updated"
        if outcome == ObservationProcessing.Outcome.SIGNALS_CREATED:
            return "signal_created"
        return "no_signal_created"
    return "analysis_queued"


def signal_ids_for_observation(*, observation_id: uuid.UUID) -> list[uuid.UUID]:
    ids = (
        CandidateSignal.objects.filter(
            observation_id=observation_id,
            result_signal_id__isnull=False,
            result_signal__establishment_id=F("observation__establishment_id"),
        )
        .values_list("result_signal_id", flat=True)
        .distinct()
    )
    return list(ids)


def signal_summaries_for_observation(
    *,
    observation_id: uuid.UUID,
) -> list[ObservationProcessingSignalSummary]:
    signal_ids = signal_ids_for_observation(observation_id=observation_id)
    if not signal_ids:
        return []

    summaries: list[ObservationProcessingSignalSummary] = []
    signals = (
        Signal.objects.filter(id__in=signal_ids)
        .select_related(
            "operational_module",
            "operational_domain",
            "operational_subject",
        )
        .order_by("created_at")
    )
    for signal in signals:
        summaries.append(
            ObservationProcessingSignalSummary(
                id=signal.id,
                title=signal.title,
                operational_module_key=signal.operational_module.key,
                operational_module_label=signal.operational_module.label,
                operational_domain_key=signal.operational_domain.key,
                operational_domain_label=signal.operational_domain.label,
                operational_subject_key=signal.operational_subject.key,
                operational_subject_label=signal.operational_subject.label,
                location_text=signal.location_text,
            )
        )
    return summaries


def get_observation_for_establishment(
    *,
    establishment_id: uuid.UUID,
    observation_id: uuid.UUID,
) -> Observation | None:
    return (
        Observation.objects.filter(
            id=observation_id,
            establishment_id=establishment_id,
        )
        .select_related("processing")
        .first()
    )


def get_observation_processing_status(
    *,
    establishment_id: uuid.UUID,
    observation_id: uuid.UUID,
) -> ObservationProcessingStatusProjection | None:
    observation = get_observation_for_establishment(
        establishment_id=establishment_id,
        observation_id=observation_id,
    )
    if observation is None:
        return None

    try:
        processing = observation.processing
    except ObservationProcessing.DoesNotExist:
        return None

    outcome = processing.outcome or ""
    return ObservationProcessingStatusProjection(
        observation_id=observation.id,
        status=processing.status,
        outcome=outcome,
        signal_ids=signal_ids_for_observation(observation_id=observation.id),
        signals=signal_summaries_for_observation(observation_id=observation.id),
        last_error_code=processing.last_error_code or "",
        ux_status=resolve_ux_status(status=processing.status, outcome=outcome),
        created_at=processing.created_at,
        updated_at=processing.updated_at,
        processed_at=processing.processed_at,
    )
