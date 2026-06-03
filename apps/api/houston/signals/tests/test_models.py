from __future__ import annotations

import pytest
from django.utils import timezone

from houston.establishments.tests.test_permissions import build_membership
from houston.signals.models import CandidateSignal, Signal, SignalSourceObservation
from houston.signals.tests.conftest import create_observation, create_taxonomy

pytestmark = pytest.mark.django_db


def test_signal_defaults_to_open():
    membership = build_membership()
    module, domain, subject = create_taxonomy(membership.establishment)
    now = timezone.now()
    signal = Signal.objects.create(
        establishment=membership.establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
        title="Issue",
        structured_summary="Summary",
        last_activity_at=now,
    )
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
    module, domain, subject = create_taxonomy(membership.establishment)
    observation = create_observation(membership=membership)
    now = timezone.now()
    signal = Signal.objects.create(
        establishment=membership.establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
        title="Issue",
        structured_summary="Summary",
        last_activity_at=now,
    )
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
