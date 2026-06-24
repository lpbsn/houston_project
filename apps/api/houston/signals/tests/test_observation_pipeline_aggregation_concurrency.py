from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import pytest
from django.db import close_old_connections

from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import ObservationProcessing
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES
from houston.signals.models import CandidateSignal, Signal, SignalSourceObservation
from houston.signals.services import (
    create_signal_from_candidate,
    normalize_issue_focus,
    run_observation_pipeline,
)
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db(transaction=True)


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


def test_concurrent_pipeline_same_aggregation_key_single_active_signal():
    membership = build_membership()
    _setup_hotel_taxonomy(membership.establishment)
    observation_a = create_observation(membership=membership)
    observation_b = create_observation(membership=membership)
    provider = FakeObservationPipelineProvider()
    normalized_focus = normalize_issue_focus("structured issue")

    # Barrier forces both pipelines to reach create concurrently before either inserts.
    barrier = threading.Barrier(2, timeout=10)
    original_create = create_signal_from_candidate

    def synced_create(*args, **kwargs):
        barrier.wait(timeout=10)
        return original_create(*args, **kwargs)

    def run_pipeline(observation_id):
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
            list(executor.map(run_pipeline, [observation_a.id, observation_b.id]))

    active_signals = Signal.objects.filter(
        establishment=membership.establishment,
        status__in=ACTIVE_SIGNAL_STATUSES,
        issue_focus=normalized_focus,
    )
    assert active_signals.count() == 1
    signal = active_signals.get()

    for observation in (observation_a, observation_b):
        processing = observation.processing
        processing.refresh_from_db()
        assert processing.status == ObservationProcessing.Status.PROCESSED

    link_signal_ids = set(
        SignalSourceObservation.objects.filter(
            observation_id__in=[observation_a.id, observation_b.id],
        ).values_list("signal_id", flat=True)
    )
    assert link_signal_ids == {signal.id}

    outcomes = set(
        CandidateSignal.objects.filter(
            observation_id__in=[observation_a.id, observation_b.id],
        ).values_list("outcome", flat=True)
    )
    assert outcomes == {
        CandidateSignal.Outcome.CREATED_SIGNAL,
        CandidateSignal.Outcome.AGGREGATED_SIGNAL,
    }
