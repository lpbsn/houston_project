from __future__ import annotations

import pytest
from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.observations.selectors import (
    get_observation_processing_status,
    signal_ids_for_observation,
)
from houston.signals.models import CandidateSignal, Signal
from houston.signals.services import run_observation_pipeline
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership


def _setup_pipeline_taxonomy(establishment):
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )


pytestmark = pytest.mark.django_db


def test_get_observation_processing_status_none_when_wrong_establishment():
    membership = build_membership()
    other = build_membership()
    observation = create_observation(membership=other)

    assert (
        get_observation_processing_status(
            establishment_id=membership.establishment_id,
            observation_id=observation.id,
        )
        is None
    )


def test_get_observation_processing_status_collects_signal_ids():
    membership = build_membership()
    _setup_pipeline_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)

    run_observation_pipeline(observation.id, provider=FakeObservationPipelineProvider())

    projection = get_observation_processing_status(
        establishment_id=membership.establishment_id,
        observation_id=observation.id,
    )

    assert projection is not None
    assert projection.status == ObservationProcessing.Status.PROCESSED
    assert len(projection.signal_ids) == 1
    assert Signal.objects.filter(id=projection.signal_ids[0]).exists()
    assert CandidateSignal.objects.filter(result_signal_id=projection.signal_ids[0]).exists()


def test_processing_status_does_not_return_unrelated_signal():
    from django.utils import timezone

    membership = build_membership()
    _setup_pipeline_taxonomy(membership.establishment)
    observation_a = create_observation(membership=membership, text="Observation A text here.")
    observation_b = create_observation(membership=membership, text="Observation B text here.")

    run_observation_pipeline(observation_a.id, provider=FakeObservationPipelineProvider())
    signal_ids_a = signal_ids_for_observation(observation_id=observation_a.id)
    assert len(signal_ids_a) == 1

    now = timezone.now()
    signal_b = Signal.objects.create(
        establishment=membership.establishment,
        title="Other observation signal",
        structured_summary="Linked only to observation B.",
        last_activity_at=now,
    )
    CandidateSignal.objects.create(
        observation=observation_b,
        establishment=membership.establishment,
        title=signal_b.title,
        structured_summary=signal_b.structured_summary,
        outcome=CandidateSignal.Outcome.CREATED_SIGNAL,
        result_signal=signal_b,
    )

    projection_a = get_observation_processing_status(
        establishment_id=membership.establishment_id,
        observation_id=observation_a.id,
    )
    assert projection_a is not None
    assert signal_b.id not in projection_a.signal_ids
    assert signal_ids_a[0] in projection_a.signal_ids


def test_processing_status_does_not_return_cross_establishment_signal():
    membership = build_membership()
    other = build_membership()
    _setup_pipeline_taxonomy(membership.establishment)
    _setup_pipeline_taxonomy(other.establishment)
    observation = create_observation(membership=membership)

    run_observation_pipeline(observation.id, provider=FakeObservationPipelineProvider())
    other_observation = create_observation(membership=other)
    run_observation_pipeline(other_observation.id, provider=FakeObservationPipelineProvider())

    other_signal_id = signal_ids_for_observation(observation_id=other_observation.id)[0]
    CandidateSignal.objects.filter(observation=observation).update(result_signal_id=other_signal_id)

    signal_ids = signal_ids_for_observation(observation_id=observation.id)
    assert other_signal_id not in signal_ids
    assert signal_ids == []
