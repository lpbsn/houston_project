from __future__ import annotations

import pytest

from houston.signals.models import CandidateSignal, Signal, SignalSourceObservation
from houston.signals.tests.conftest import create_minimal_v3_signal, create_observation
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def test_signal_defaults_to_open():
    membership = build_membership()
    signal = create_minimal_v3_signal(membership, title="Issue")
    assert signal.status == Signal.Status.OPEN
    assert signal.urgency == Signal.Urgency.NORMAL
    assert signal.is_pinned is False


def test_candidate_signal_outcome_choices():
    membership = build_membership()
    observation = create_observation(membership=membership)
    row = CandidateSignal.objects.create(
        observation=observation,
        establishment=membership.establishment,
        outcome=CandidateSignal.Outcome.PENDING,
    )
    assert row.outcome == CandidateSignal.Outcome.PENDING


def test_signal_source_observation_unique_link():
    membership = build_membership()
    observation = create_observation(membership=membership)
    signal = create_minimal_v3_signal(membership, title="Issue")
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    with pytest.raises(Exception):
        SignalSourceObservation.objects.create(
            signal=signal,
            observation=observation,
            link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        )
