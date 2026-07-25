from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from django.db import close_old_connections
from django.utils import timezone

from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES, AI_OBSERVATION_PIPELINE_SCHEMA_VERSION
from houston.signals.exceptions import SignalPipelineCandidateError
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import (
    apply_pipeline_output,
    create_signal_from_candidate,
    normalize_issue_focus,
    run_observation_pipeline,
)
from houston.signals.tests.conftest import create_observation
from houston.signals.tests.pipeline_helpers import (
    legacy_signal as _legacy_signal,
)
from houston.signals.tests.pipeline_helpers import (
    mojito_candidate as _mojito_candidate,
)
from houston.signals.tests.pipeline_helpers import (
    setup_bar_taxonomy as _setup_bar_taxonomy,
)
from houston.signals.tests.pipeline_helpers import (
    setup_hotel_taxonomy as _setup_hotel_taxonomy,
)
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def _resolved_candidate(*, hotel, subject, expected_action="inspect", issue_focus="climatisation"):
    return PipelineCandidateOutput(
        title="Clim en panne",
        structured_summary="La climatisation ne fonctionne plus.",
        issue_focus=issue_focus,
        canonical_object=issue_focus,
        signal_kind="actionable",
        expected_action=expected_action,
        information_type=None,
        affected_business_unit_routing_key=hotel.routing_key,
        responsible_business_unit_routing_key=hotel.routing_key,
        activity_subject_routing_key=subject.routing_key,
        operational_unit_key=None,
        location_text=None,
    )


def _create_resolved_signal(
    *,
    establishment,
    hotel,
    subject,
    issue_focus="climatisation",
    expected_action="inspect",
):
    return Signal.objects.create(
        establishment=establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Existing",
        structured_summary="Existing signal.",
        issue_focus=issue_focus,
        routing_status=Signal.RoutingStatus.RESOLVED,
        expected_action=expected_action,
        last_activity_at=timezone.now(),
    )


def test_two_identical_unassigned_create_two_signals():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    candidate = PipelineCandidateOutput(
        title="Unassigned issue",
        structured_summary="Needs qualification.",
        issue_focus="same-focus",
        canonical_object="object",
        signal_kind="actionable",
        expected_action="inspect",
        information_type=None,
        affected_business_unit_routing_key=None,
        responsible_business_unit_routing_key=None,
        activity_subject_routing_key=None,
        operational_unit_key=None,
        location_text=None,
    )
    result = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[candidate, candidate.model_copy()],
        ),
    )
    assert result.aggregated_count == 0
    assert result.created_count == 2
    signals = Signal.objects.filter(establishment=membership.establishment)
    assert signals.count() == 2
    assert all(s.routing_status == Signal.RoutingStatus.UNASSIGNED for s in signals)
    assert all(s.expected_action == "inspect" for s in signals)


def test_resolved_exact_match_aggregates():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    existing = _create_resolved_signal(
        establishment=membership.establishment,
        hotel=hotel,
        subject=subject,
        expected_action="inspect",
    )
    observation = create_observation(membership=membership)
    result = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[_resolved_candidate(hotel=hotel, subject=subject)],
        ),
    )
    assert result.outcome == ObservationProcessing.Outcome.SIGNAL_AGGREGATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 1
    row = CandidateSignal.objects.get(observation=observation)
    assert row.outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL
    assert row.result_signal_id == existing.id


def test_different_issue_focus_does_not_false_aggregate():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    _create_resolved_signal(
        establishment=membership.establishment,
        hotel=hotel,
        subject=subject,
        issue_focus="climatisation",
    )
    observation = create_observation(membership=membership)
    result = apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                _resolved_candidate(
                    hotel=hotel,
                    subject=subject,
                    issue_focus="chaudiere",
                )
            ],
        ),
    )
    assert result.outcome == ObservationProcessing.Outcome.SIGNALS_CREATED
    assert Signal.objects.filter(establishment=membership.establishment).count() == 2


def test_d3_divergence_keeps_signal_action_and_audits():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    existing = _create_resolved_signal(
        establishment=membership.establishment,
        hotel=hotel,
        subject=subject,
        expected_action="inspect",
    )
    observation = create_observation(membership=membership)
    apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                _resolved_candidate(
                    hotel=hotel,
                    subject=subject,
                    expected_action="repair",
                )
            ],
        ),
    )
    existing.refresh_from_db()
    row = CandidateSignal.objects.get(observation=observation)
    row.refresh_from_db()
    assert existing.expected_action == "inspect"
    assert row.expected_action == "repair"
    assert row.outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL
    audit = row.resolution_audit or {}
    assert "affected" in audit
    assert "responsible" in audit
    assert "subject" in audit
    assert audit["expected_action"]["source"] == "aggregation_expected_action_divergence"
    assert audit["expected_action"]["signal_expected_action"] == "inspect"
    assert audit["expected_action"]["candidate_expected_action"] == "repair"


def test_d3_null_signal_adopts_candidate_action_with_audit():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    existing = _create_resolved_signal(
        establishment=membership.establishment,
        hotel=hotel,
        subject=subject,
        expected_action=None,
    )
    observation = create_observation(membership=membership)
    apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                _resolved_candidate(
                    hotel=hotel,
                    subject=subject,
                    expected_action="repair",
                )
            ],
        ),
    )
    existing.refresh_from_db()
    row = CandidateSignal.objects.get(observation=observation)
    row.refresh_from_db()
    assert existing.expected_action == "repair"
    assert row.expected_action == "repair"
    audit = row.resolution_audit or {}
    assert "affected" in audit
    assert audit["expected_action"]["source"] == "aggregation_initial_expected_action"
    assert audit["expected_action"]["adopted"] == "repair"


def test_d3_signal_non_null_candidate_null_no_audit():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    existing = _create_resolved_signal(
        establishment=membership.establishment,
        hotel=hotel,
        subject=subject,
        expected_action="inspect",
    )
    observation = create_observation(membership=membership)
    apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                _resolved_candidate(
                    hotel=hotel,
                    subject=subject,
                    expected_action=None,
                )
            ],
        ),
    )
    existing.refresh_from_db()
    row = CandidateSignal.objects.get(observation=observation)
    row.refresh_from_db()
    assert existing.expected_action == "inspect"
    assert row.expected_action is None
    assert "expected_action" not in (row.resolution_audit or {})
    assert "affected" in (row.resolution_audit or {})


def test_d3_identical_actions_no_audit_noise():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    existing = _create_resolved_signal(
        establishment=membership.establishment,
        hotel=hotel,
        subject=subject,
        expected_action="inspect",
    )
    observation = create_observation(membership=membership)
    apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                _resolved_candidate(
                    hotel=hotel,
                    subject=subject,
                    expected_action="inspect",
                )
            ],
        ),
    )
    existing.refresh_from_db()
    row = CandidateSignal.objects.get(observation=observation)
    row.refresh_from_db()
    assert existing.expected_action == "inspect"
    assert "expected_action" not in (row.resolution_audit or {})
    assert "affected" in (row.resolution_audit or {})


def test_legacy_empty_focus_signal_does_not_absorb_candidate():
    membership = build_membership()
    bar = _setup_bar_taxonomy(membership.establishment)
    subject = bar.activity_subjects.get()
    legacy = _legacy_signal(
        establishment=membership.establishment,
        bar=bar,
        subject=subject,
    )
    observation = create_observation(membership=membership)
    apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[_mojito_candidate(bar=bar, subject=subject)],
        ),
    )
    assert Signal.objects.filter(establishment=membership.establishment).count() == 2
    row = CandidateSignal.objects.get(observation=observation)
    assert row.outcome == CandidateSignal.Outcome.CREATED_SIGNAL
    assert row.result_signal_id != legacy.id


def test_empty_issue_focus_after_normalize_rolls_back_apply():
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
                    _resolved_candidate(
                        hotel=hotel,
                        subject=subject,
                        issue_focus="   ",
                    )
                ],
            ),
        )

    assert Signal.objects.filter(establishment=membership.establishment).count() == 0
    assert CandidateSignal.objects.filter(observation=observation).count() == 0


def test_create_copies_expected_action_for_resolved_and_unassigned():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation = create_observation(membership=membership)
    apply_pipeline_output(
        observation=observation,
        output=ObservationPipelineOutput(
            schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
            candidates=[
                _resolved_candidate(
                    hotel=hotel,
                    subject=subject,
                    expected_action="repair",
                ),
                PipelineCandidateOutput(
                    title="Unassigned",
                    structured_summary="Needs routing.",
                    issue_focus="other-focus",
                    canonical_object="object",
                    signal_kind="actionable",
                    expected_action="monitor",
                    information_type=None,
                    affected_business_unit_routing_key=None,
                    responsible_business_unit_routing_key=None,
                    activity_subject_routing_key=None,
                    operational_unit_key=None,
                    location_text=None,
                ),
            ],
        ),
    )
    by_status = {
        s.routing_status: s
        for s in Signal.objects.filter(establishment=membership.establishment)
    }
    assert by_status[Signal.RoutingStatus.RESOLVED].expected_action == "repair"
    assert by_status[Signal.RoutingStatus.UNASSIGNED].expected_action == "monitor"


@pytest.mark.django_db(transaction=True)
def test_concurrent_aggregation_d3_different_actions_no_overwrite():
    membership = build_membership()
    hotel = _setup_hotel_taxonomy(membership.establishment)
    subject = hotel.activity_subjects.get()
    observation_a = create_observation(membership=membership)
    observation_b = create_observation(membership=membership)
    normalized_focus = normalize_issue_focus("structured issue")

    payload_inspect = {
        "schema_version": AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        "candidates": [
            {
                "title": "Clim en panne",
                "structured_summary": "La climatisation ne fonctionne plus.",
                "issue_focus": "structured issue",
                "canonical_object": "clim",
                "signal_kind": "actionable",
                "expected_action": "inspect",
                "information_type": None,
                "affected_business_unit_routing_key": hotel.routing_key,
                "responsible_business_unit_routing_key": hotel.routing_key,
                "activity_subject_routing_key": subject.routing_key,
                "operational_unit_key": None,
                "location_text": None,
            }
        ],
    }
    payload_repair = {
        **payload_inspect,
        "candidates": [
            {
                **payload_inspect["candidates"][0],
                "expected_action": "repair",
            }
        ],
    }

    barrier = threading.Barrier(2, timeout=10)
    original_create = create_signal_from_candidate

    def synced_create(*args, **kwargs):
        barrier.wait(timeout=10)
        return original_create(*args, **kwargs)

    def run_pipeline(observation_id, provider):
        close_old_connections()
        try:
            run_observation_pipeline(observation_id, provider=provider)
        finally:
            close_old_connections()

    with patch(
        "houston.signals.services.create_signal_from_candidate",
        side_effect=synced_create,
    ):
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    run_pipeline,
                    observation_a.id,
                    FakeObservationPipelineProvider(payload=payload_inspect),
                ),
                executor.submit(
                    run_pipeline,
                    observation_b.id,
                    FakeObservationPipelineProvider(payload=payload_repair),
                ),
            ]
            for future in futures:
                future.result()

    active_signals = Signal.objects.filter(
        establishment=membership.establishment,
        status__in=ACTIVE_SIGNAL_STATUSES,
        issue_focus=normalized_focus,
        routing_status=Signal.RoutingStatus.RESOLVED,
    )
    assert active_signals.count() == 1
    signal = active_signals.get()
    assert signal.expected_action in {"inspect", "repair"}

    candidates = list(
        CandidateSignal.objects.filter(
            observation_id__in=[observation_a.id, observation_b.id],
        )
    )
    outcomes = {c.outcome for c in candidates}
    assert outcomes == {
        CandidateSignal.Outcome.CREATED_SIGNAL,
        CandidateSignal.Outcome.AGGREGATED_SIGNAL,
    }
    created = next(
        c for c in candidates if c.outcome == CandidateSignal.Outcome.CREATED_SIGNAL
    )
    aggregated = next(
        c for c in candidates if c.outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL
    )
    created.refresh_from_db()
    aggregated.refresh_from_db()
    signal.refresh_from_db()

    # First non-null action on the surviving Signal is never overwritten.
    assert signal.expected_action == created.expected_action
    assert aggregated.expected_action in {"inspect", "repair"}
    assert aggregated.expected_action != signal.expected_action
    audit = aggregated.resolution_audit or {}
    assert audit["expected_action"]["source"] == "aggregation_expected_action_divergence"
    assert audit["expected_action"]["signal_expected_action"] == signal.expected_action
    assert (
        audit["expected_action"]["candidate_expected_action"] == aggregated.expected_action
    )
    assert "affected" in audit
