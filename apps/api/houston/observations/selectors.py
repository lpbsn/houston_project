from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from django.db.models import F

from houston.establishments.business_unit_identity import (
    business_unit_public_key,
    business_unit_public_label,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.public_serialization import (
    resolve_activity_subject_public_label,
)
from houston.observations.models import Observation, ObservationProcessing
from houston.observations.permissions import can_view_observation_processing_status
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

_TERMINAL_PROCESSING_STATUSES = frozenset(
    {
        ObservationProcessing.Status.PROCESSED,
        ObservationProcessing.Status.FAILED,
    }
)


@dataclass(frozen=True)
class ObservationProcessingSignalSummary:
    id: uuid.UUID
    title: str
    affected_business_unit_key: str
    affected_business_unit_label: str
    responsible_business_unit_key: str
    responsible_business_unit_label: str
    activity_subject_key: str
    activity_subject_label: str
    location_text: str


@dataclass(frozen=True)
class ObservationProcessingStatusProjection:
    observation_id: uuid.UUID
    status: str
    outcome: str
    signal_ids: list[uuid.UUID]
    signals: list[ObservationProcessingSignalSummary]
    created_count: int
    updated_count: int
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


def _signal_summaries_for_ids(
    *,
    signal_ids: list[uuid.UUID],
) -> list[ObservationProcessingSignalSummary]:
    if not signal_ids:
        return []

    summaries: list[ObservationProcessingSignalSummary] = []
    signals = (
        Signal.objects.filter(id__in=signal_ids)
        .select_related(
            "affected_business_unit",
            "responsible_business_unit",
            "activity_subject",
            "activity_subject__catalog_activity_subject",
        )
        .order_by("created_at")
    )
    for signal in signals:
        subject_label = resolve_activity_subject_public_label(
            activity_subject=signal.activity_subject
            if signal.activity_subject_id
            else None
        )
        summaries.append(
            ObservationProcessingSignalSummary(
                id=signal.id,
                title=signal.title,
                affected_business_unit_key=(
                    business_unit_public_key(business_unit=signal.affected_business_unit)
                    if signal.affected_business_unit_id
                    else ""
                ),
                affected_business_unit_label=(
                    business_unit_public_label(business_unit=signal.affected_business_unit)
                    if signal.affected_business_unit_id
                    else ""
                ),
                responsible_business_unit_key=(
                    business_unit_public_key(business_unit=signal.responsible_business_unit)
                    if signal.responsible_business_unit_id
                    else ""
                ),
                responsible_business_unit_label=(
                    business_unit_public_label(
                        business_unit=signal.responsible_business_unit
                    )
                    if signal.responsible_business_unit_id
                    else ""
                ),
                activity_subject_key=(
                    signal.activity_subject.normalized_name if signal.activity_subject_id else ""
                ),
                activity_subject_label=subject_label or "",
                location_text=signal.location_text,
            )
        )
    return summaries


def _terminal_signal_projection(
    *,
    observation_id: uuid.UUID,
) -> tuple[list[uuid.UUID], list[ObservationProcessingSignalSummary], int, int]:
    """Single CandidateSignal pass for terminal processed status."""
    rows = list(
        CandidateSignal.objects.filter(
            observation_id=observation_id,
            result_signal_id__isnull=False,
            result_signal__establishment_id=F("observation__establishment_id"),
            outcome__in=(
                CandidateSignal.Outcome.CREATED_SIGNAL,
                CandidateSignal.Outcome.AGGREGATED_SIGNAL,
            ),
        ).values_list("result_signal_id", "outcome")
    )

    created_ids: set[uuid.UUID] = set()
    updated_ids: set[uuid.UUID] = set()
    linked_ids: set[uuid.UUID] = set()

    for signal_id, outcome in rows:
        linked_ids.add(signal_id)
        if outcome == CandidateSignal.Outcome.CREATED_SIGNAL:
            created_ids.add(signal_id)
        elif outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL:
            updated_ids.add(signal_id)

    summaries = _signal_summaries_for_ids(signal_ids=list(linked_ids))
    return (
        [summary.id for summary in summaries],
        summaries,
        len(created_ids),
        len(updated_ids),
    )


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
    membership: EstablishmentMembership,
    observation_id: uuid.UUID,
) -> ObservationProcessingStatusProjection | None:
    observation = get_observation_for_establishment(
        establishment_id=membership.establishment_id,
        observation_id=observation_id,
    )
    if observation is None:
        return None
    if not can_view_observation_processing_status(membership, observation):
        return None

    try:
        processing = observation.processing
    except ObservationProcessing.DoesNotExist:
        return None

    outcome = processing.outcome or ""
    signal_ids: list[uuid.UUID] = []
    signals: list[ObservationProcessingSignalSummary] = []
    created_count = 0
    updated_count = 0

    if processing.status == ObservationProcessing.Status.PROCESSED:
        signal_ids, signals, created_count, updated_count = _terminal_signal_projection(
            observation_id=observation.id
        )
    elif processing.status not in _TERMINAL_PROCESSING_STATUSES:
        # Non-terminal: skip CandidateSignal / Signal queries entirely.
        pass
    # failed: empty lists and zero counts (no CandidateSignal / Signal queries)

    return ObservationProcessingStatusProjection(
        observation_id=observation.id,
        status=processing.status,
        outcome=outcome,
        signal_ids=signal_ids,
        signals=signals,
        created_count=created_count,
        updated_count=updated_count,
        last_error_code=processing.last_error_code or "",
        ux_status=resolve_ux_status(status=processing.status, outcome=outcome),
        created_at=processing.created_at,
        updated_at=processing.updated_at,
        processed_at=processing.processed_at,
    )
