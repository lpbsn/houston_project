from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.utils import timezone

from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.exceptions import SignalPipelineCandidateError
from houston.signals.models import CandidateSignal, Signal, SignalSourceObservation
from houston.signals.services import (
    apply_pipeline_output,
    run_observation_pipeline,
    validate_pipeline_output_issue_focus,
)
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership

pytestmark = [pytest.mark.django_db, pytest.mark.slow]


def _setup_hotel_taxonomy(establishment):
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )
    return hotel


def _output_with_candidate(
    *,
    affected_key: str = "hotel",
    responsible_key: str = "hotel",
    subject_key: str = "maintenance",
):
    return ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[
            PipelineCandidateOutput(
                title="Clim en panne",
                structured_summary="La climatisation ne fonctionne plus.",
                issue_focus="climatisation",
                affected_business_unit_key=affected_key,
                responsible_business_unit_key=responsible_key,
                activity_subject_key=subject_key,
                operational_unit_key=None,
                location_text=None,
                aggregate_into_signal_id=None,
            )
        ],
    )


def _fake_provider_payload(*, issue_focus: str = "climatisation"):
    return {
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "candidates": [
            {
                "title": "Clim en panne",
                "structured_summary": "La climatisation ne fonctionne plus.",
                "issue_focus": issue_focus,
                "affected_business_unit_key": "hotel",
                "responsible_business_unit_key": "hotel",
                "activity_subject_key": "maintenance",
                "operational_unit_key": None,
                "location_text": None,
                "aggregate_into_signal_id": None,
            }
        ],
    }


def test_validate_pipeline_output_rejects_whitespace_only_issue_focus():
    with pytest.raises(SignalPipelineCandidateError):
        validate_pipeline_output_issue_focus(
            output=ObservationPipelineOutput(
                schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                candidates=[
                    PipelineCandidateOutput(
                        title="Clim en panne",
                        structured_summary="La climatisation ne fonctionne plus.",
                        issue_focus="   ",
                        affected_business_unit_key="hotel",
                        responsible_business_unit_key="hotel",
                        activity_subject_key="maintenance",
                        operational_unit_key=None,
                        location_text=None,
                        aggregate_into_signal_id=None,
                    )
                ],
            )
        )


def test_apply_pipeline_rejects_whitespace_only_issue_focus():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    with pytest.raises(SignalPipelineCandidateError):
        apply_pipeline_output(
            observation=observation,
            output=ObservationPipelineOutput(
                schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                candidates=[
                    PipelineCandidateOutput(
                        title="Clim en panne",
                        structured_summary="La climatisation ne fonctionne plus.",
                        issue_focus="   ",
                        affected_business_unit_key="hotel",
                        responsible_business_unit_key="hotel",
                        activity_subject_key="maintenance",
                        operational_unit_key=None,
                        location_text=None,
                        aggregate_into_signal_id=None,
                    )
                ],
            ),
        )


def test_run_pipeline_marks_failed_on_invalid_issue_focus():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider(payload=_fake_provider_payload(issue_focus="   "))

    run_observation_pipeline(observation.id, provider=provider)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
    assert processing.last_error_code == "invalid_issue_focus"
    assert processing.status != ObservationProcessing.Status.PROCESSING


def test_no_candidate_signal_on_invalid_issue_focus():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider(payload=_fake_provider_payload(issue_focus="   "))

    run_observation_pipeline(observation.id, provider=provider)

    assert CandidateSignal.objects.filter(observation=observation).count() == 0


def test_run_pipeline_marks_failed_on_apply_integrity_error():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider()

    with patch(
        "houston.signals.services._persist_pending_candidate",
        side_effect=IntegrityError(
            'null value in column "issue_focus" violates not-null constraint'
        ),
    ):
        with pytest.raises(IntegrityError):
            run_observation_pipeline(observation.id, provider=provider)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
    assert processing.last_error_code == "pipeline_persist_error"
    assert processing.status != ObservationProcessing.Status.PROCESSING


def test_no_observation_stuck_in_processing_after_apply_error():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    run_observation_pipeline(
        observation.id,
        provider=FakeObservationPipelineProvider(payload=_fake_provider_payload(issue_focus="   ")),
    )
    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status != ObservationProcessing.Status.PROCESSING

    observation_two = create_observation(membership=membership)
    with patch(
        "houston.signals.services._persist_pending_candidate",
        side_effect=IntegrityError("persist failed"),
    ):
        with pytest.raises(IntegrityError):
            run_observation_pipeline(observation_two.id, provider=FakeObservationPipelineProvider())
    processing_two = observation_two.processing
    processing_two.refresh_from_db()
    assert processing_two.status != ObservationProcessing.Status.PROCESSING


def test_apply_pipeline_creates_open_signal():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    signal = Signal.objects.get()
    assert signal.status == Signal.Status.OPEN
    assert signal.affected_business_unit.key == "hotel"
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.CREATED_SIGNAL).exists()


def test_invalid_taxonomy_key_rejects_candidate():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(affected_key="unknown"),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.NO_SIGNAL_CREATED
    assert Signal.objects.count() == 0
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.REJECTED).count() == 1


def test_observation_pipeline_links_created_signal_to_source_observation():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(),
    )

    signal = Signal.objects.get()
    link = SignalSourceObservation.objects.get(signal=signal, observation=observation)
    assert link.link_type == SignalSourceObservation.LinkType.CREATED_FROM


def test_apply_pipeline_persists_aggregate_hint_signal_id():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)
    existing = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Signal actif",
        structured_summary="Situation en cours.",
        issue_focus="maintenance",
        last_activity_at=timezone.now(),
    )

    outcome = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                PipelineCandidateOutput(
                    title="Prolongation",
                    structured_summary="Même sujet, aggravation.",
                    issue_focus="maintenance",
                    affected_business_unit_key="hotel",
                    responsible_business_unit_key="hotel",
                    activity_subject_key="maintenance",
                    operational_unit_key=None,
                    location_text=None,
                    aggregate_into_signal_id=str(existing.id),
                )
            ],
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNAL_AGGREGATED
    row = CandidateSignal.objects.get(observation=observation)
    assert row.ai_aggregate_hint_signal_id == existing.id
    assert row.outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL
    assert row.result_signal_id == existing.id


def test_run_pipeline_with_fake_provider():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider()

    run_observation_pipeline(observation.id, provider=provider)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.PROCESSED
    assert Signal.objects.filter(establishment=membership.establishment).exists()


def test_apply_pipeline_rejects_hint_when_issue_focus_mismatch():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)
    mojito_signal = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Rupture sirop mojito",
        structured_summary="Sirop mojito manquant.",
        issue_focus="sirop mojito",
        last_activity_at=timezone.now(),
    )

    outcome = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                PipelineCandidateOutput(
                    title="Rupture de pain",
                    structured_summary="Plus de pain disponible.",
                    issue_focus="pain",
                    affected_business_unit_key="hotel",
                    responsible_business_unit_key="hotel",
                    activity_subject_key="maintenance",
                    operational_unit_key=None,
                    location_text=None,
                    aggregate_into_signal_id=str(mojito_signal.id),
                )
            ],
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 2
    row = CandidateSignal.objects.get(observation=observation)
    assert row.outcome == CandidateSignal.Outcome.CREATED_SIGNAL
    assert row.result_signal_id != mojito_signal.id
    assert row.result_signal.issue_focus == "pain"


def test_apply_pipeline_logs_candidate_applied_audit(caplog):
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)
    existing = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Signal actif",
        structured_summary="Situation en cours.",
        issue_focus="maintenance",
        last_activity_at=timezone.now(),
    )

    with caplog.at_level(logging.INFO, logger="houston.signals.services"):
        apply_pipeline_output(
            observation=observation,
            output=ObservationPipelineOutput(
                schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                candidates=[
                    PipelineCandidateOutput(
                        title="Prolongation",
                        structured_summary="Même sujet, aggravation.",
                        issue_focus="maintenance",
                        affected_business_unit_key="hotel",
                        responsible_business_unit_key="hotel",
                        activity_subject_key="maintenance",
                        operational_unit_key=None,
                        location_text=None,
                        aggregate_into_signal_id=str(existing.id),
                    )
                ],
            ),
        )

    applied_records = [
        record
        for record in caplog.records
        if record.getMessage() == "observation_pipeline_candidate_applied"
    ]
    assert len(applied_records) == 1
    record = applied_records[0]
    assert record.hint_used is True
    assert getattr(record, "hint_rejected_reason", "") == ""
    assert record.candidate_outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL
    assert record.aggregation_key
    assert observation.raw_text not in caplog.text


def test_apply_pipeline_logs_hint_rejected_on_issue_focus_mismatch(caplog):
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)
    mojito_signal = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Rupture sirop mojito",
        structured_summary="Sirop mojito manquant.",
        issue_focus="sirop mojito",
        last_activity_at=timezone.now(),
    )

    with caplog.at_level(logging.INFO, logger="houston.signals.services"):
        apply_pipeline_output(
            observation=observation,
            output=ObservationPipelineOutput(
                schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
                candidates=[
                    PipelineCandidateOutput(
                        title="Rupture de pain",
                        structured_summary="Plus de pain disponible.",
                        issue_focus="pain",
                        affected_business_unit_key="hotel",
                        responsible_business_unit_key="hotel",
                        activity_subject_key="maintenance",
                        operational_unit_key=None,
                        location_text=None,
                        aggregate_into_signal_id=str(mojito_signal.id),
                    )
                ],
            ),
        )

    applied_records = [
        record
        for record in caplog.records
        if record.getMessage() == "observation_pipeline_candidate_applied"
    ]
    assert len(applied_records) == 1
    record = applied_records[0]
    assert record.hint_used is False
    assert record.hint_rejected_reason == "hint_issue_focus_mismatch"
    assert record.candidate_outcome == CandidateSignal.Outcome.CREATED_SIGNAL
