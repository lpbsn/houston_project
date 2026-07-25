from __future__ import annotations

import logging
import uuid
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.utils import timezone

from houston.ai.observation_pipeline import (
    PRECONDITION_INVALID_ESTABLISHMENT,
    PRECONDITION_NO_ACTIVE_BUSINESS_UNIT,
    FakeObservationPipelineProvider,
    ObservationPipelineSkippedError,
    call_observation_pipeline,
    establishment_can_run_observation_pipeline,
    evaluate_observation_pipeline_precondition,
)
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.establishments.models import Establishment
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
from houston.signals.tests.pipeline_helpers import (
    fake_provider_payload as _fake_provider_payload,
)
from houston.signals.tests.pipeline_helpers import (
    output_with_candidate as _output_with_candidate,
)
from houston.signals.tests.pipeline_helpers import (
    setup_hotel_taxonomy as _setup_hotel_taxonomy,
)
from houston.testing.factories import build_membership
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db


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
                        affected_business_unit_routing_key="hotel--hotel--0123456789abcdef",
                        responsible_business_unit_routing_key="hotel--hotel--0123456789abcdef",
                        activity_subject_routing_key="custom--maintenance--0123456789abcdef",
                        operational_unit_key=None,
                        location_text=None,
                        aggregate_into_signal_id=None,
                    )
                ],
            )
        )


def test_apply_pipeline_rejects_whitespace_only_issue_focus():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
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
                        affected_business_unit_routing_key=hotel.routing_key,
                        responsible_business_unit_routing_key=hotel.routing_key,
                        activity_subject_routing_key=subject.routing_key,
                        operational_unit_key=None,
                        location_text=None,
                        aggregate_into_signal_id=None,
                    )
                ],
            ),
        )


def test_run_pipeline_marks_failed_on_invalid_issue_focus():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider(
        payload=_fake_provider_payload(
            affected_routing_key=hotel.routing_key,
            subject_routing_key=subject.routing_key,
            issue_focus="   ",
        )
    )

    run_observation_pipeline(observation.id, provider=provider)

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
    assert processing.last_error_code == "invalid_issue_focus"
    assert processing.status != ObservationProcessing.Status.PROCESSING


def test_run_pipeline_marks_failed_when_establishment_deactivated():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    establishment = membership.establishment
    establishment.status = Establishment.Status.DEACTIVATED
    establishment.save(update_fields=["status", "updated_at"])
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider(
        payload={"schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION, "candidates": []}
    )

    with patch.object(provider, "propose", wraps=provider.propose) as propose:
        run_observation_pipeline(observation.id, provider=provider)
        propose.assert_not_called()

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
    assert processing.last_error_code == PRECONDITION_INVALID_ESTABLISHMENT
    assert CandidateSignal.objects.filter(observation=observation).count() == 0
    assert Signal.objects.filter(establishment=establishment).count() == 0


def test_run_pipeline_marks_failed_when_no_active_business_unit():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    hotel.active = False
    hotel.save(update_fields=["active", "updated_at"])
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider(
        payload={"schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION, "candidates": []}
    )

    with patch.object(provider, "propose", wraps=provider.propose) as propose:
        run_observation_pipeline(observation.id, provider=provider)
        propose.assert_not_called()

    processing = observation.processing
    processing.refresh_from_db()
    assert processing.status == ObservationProcessing.Status.FAILED
    assert processing.last_error_code == PRECONDITION_NO_ACTIVE_BUSINESS_UNIT
    assert CandidateSignal.objects.filter(observation=observation).count() == 0
    assert Signal.objects.filter(establishment=membership.establishment).count() == 0


def test_evaluate_precondition_missing_establishment_uuid():
    missing_id = uuid.uuid4()
    with pytest.raises(ObservationPipelineSkippedError) as exc_info:
        evaluate_observation_pipeline_precondition(establishment_id=missing_id)
    assert exc_info.value.error_code == PRECONDITION_INVALID_ESTABLISHMENT
    assert establishment_can_run_observation_pipeline(establishment_id=missing_id) is False


def test_active_business_unit_without_subjects_allows_precondition():
    membership = build_membership()
    create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    assert (
        establishment_can_run_observation_pipeline(
            establishment_id=membership.establishment_id,
        )
        is True
    )
    evaluate_observation_pipeline_precondition(
        establishment_id=membership.establishment_id,
    )


def test_precondition_gate_does_not_consult_snapshot_ready_and_calls_provider():
    membership = build_membership()
    create_business_unit(
        establishment=membership.establishment,
        key="hotel",
        label="Hôtel",
    )
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider(
        payload={"schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION, "candidates": []}
    )
    minimal_input = {
        "observation_id": str(observation.id),
        "establishment_id": str(membership.establishment_id),
        "validated_text": observation.raw_text,
        "submitted_at": observation.submitted_at.isoformat(),
        "media_count": 0,
        "establishment_context": {
            "id": str(membership.establishment_id),
            "name": membership.establishment.name,
            "activity_description": None,
            "active_business_units": [],
        },
        "routing_taxonomy": {
            "capabilities_version": "catalog_capabilities_v1",
            "business_units": [],
            "operational_units": [],
        },
        "submission_context": {"author_scope_business_unit_routing_keys": []},
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "prompt_version": "test",
    }

    def _forbid_snapshot_ready(**_kwargs):
        raise AssertionError(
            "precondition/gate must not consult snapshot_ready_business_units"
        )

    with (
        patch(
            "houston.establishments.taxonomy_snapshot.snapshot_ready_business_units",
            side_effect=_forbid_snapshot_ready,
        ),
        patch(
            "houston.establishments.taxonomy_snapshot.establishment_has_active_business_units",
            side_effect=_forbid_snapshot_ready,
        ),
        patch(
            "houston.ai.observation_pipeline.build_pipeline_input",
            return_value=minimal_input,
        ),
        patch.object(provider, "propose", wraps=provider.propose) as propose,
    ):
        call_observation_pipeline(observation=observation, provider=provider)
        propose.assert_called_once()


def test_no_candidate_signal_on_invalid_issue_focus():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider(
        payload=_fake_provider_payload(
            affected_routing_key=hotel.routing_key,
            subject_routing_key=subject.routing_key,
            issue_focus="   ",
        )
    )

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
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)

    run_observation_pipeline(
        observation.id,
        provider=FakeObservationPipelineProvider(
            payload=_fake_provider_payload(
                affected_routing_key=hotel.routing_key,
                subject_routing_key=subject.routing_key,
                issue_focus="   ",
            )
        ),
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
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(
            affected_routing_key=hotel.routing_key,
            subject_routing_key=subject.routing_key,
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    signal = Signal.objects.get()
    assert signal.status == Signal.Status.OPEN
    assert signal.affected_business_unit.catalog_business_unit.key == "hotel"
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.CREATED_SIGNAL).exists()


def test_invalid_taxonomy_key_rejects_candidate():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)

    outcome = apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(
            affected_routing_key="unknown--missing--0000000000000000",
            subject_routing_key=subject.routing_key,
        ),
    ).outcome

    assert outcome == ObservationProcessing.Outcome.NO_SIGNAL_CREATED
    assert Signal.objects.count() == 0
    assert CandidateSignal.objects.filter(outcome=CandidateSignal.Outcome.REJECTED).count() == 1


def test_observation_pipeline_links_created_signal_to_source_observation():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)

    apply_pipeline_output(
        observation=observation,
        output=_output_with_candidate(
            affected_routing_key=hotel.routing_key,
            subject_routing_key=subject.routing_key,
        ),
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
        routing_status=Signal.RoutingStatus.RESOLVED,
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
                    affected_business_unit_routing_key=hotel.routing_key,
                    responsible_business_unit_routing_key=hotel.routing_key,
                    activity_subject_routing_key=subject.routing_key,
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
        routing_status=Signal.RoutingStatus.RESOLVED,
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
                    affected_business_unit_routing_key=hotel.routing_key,
                    responsible_business_unit_routing_key=hotel.routing_key,
                    activity_subject_routing_key=subject.routing_key,
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
        routing_status=Signal.RoutingStatus.RESOLVED,
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
                        affected_business_unit_routing_key=hotel.routing_key,
                        responsible_business_unit_routing_key=hotel.routing_key,
                        activity_subject_routing_key=subject.routing_key,
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
        routing_status=Signal.RoutingStatus.RESOLVED,
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
                        affected_business_unit_routing_key=hotel.routing_key,
                        responsible_business_unit_routing_key=hotel.routing_key,
                        activity_subject_routing_key=subject.routing_key,
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
