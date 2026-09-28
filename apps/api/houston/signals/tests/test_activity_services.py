from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.db import close_old_connections, transaction
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.signals.services import (
    aggregate_candidate_into_signal,
    pin_signal,
    touch_signal_activity,
    unpin_signal,
)
from houston.signals.tests.conftest import (
    build_api_membership,
    create_minimal_v3_signal,
    create_observation,
)

pytestmark = pytest.mark.django_db


def test_aggregation_retry_keeps_first_effective_activity_timestamp():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Aggregation activity")
    observation = create_observation(membership=membership)
    baseline = timezone.now() - timedelta(days=1)
    Signal.objects.filter(pk=signal.pk).update(last_activity_at=baseline)
    signal.refresh_from_db()

    aggregate_candidate_into_signal(signal=signal, observation=observation)
    signal.refresh_from_db()
    first_activity = signal.last_activity_at

    aggregate_candidate_into_signal(signal=signal, observation=observation)
    signal.refresh_from_db()

    assert first_activity > baseline
    assert signal.last_activity_at == first_activity


def test_pin_and_unpin_do_not_advance_signal_activity():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Pin activity")
    previous_activity = signal.last_activity_at

    pin_signal(signal=signal, membership=membership)
    signal.refresh_from_db()
    assert signal.last_activity_at == previous_activity

    unpin_signal(signal=signal)
    signal.refresh_from_db()
    assert signal.last_activity_at == previous_activity


@pytest.mark.django_db(transaction=True)
def test_stale_activity_writer_committing_last_cannot_regress_signal_activity():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Concurrent activity")
    older_at = signal.last_activity_at + timedelta(minutes=1)
    newer_at = older_at + timedelta(minutes=1)
    stale_loaded = threading.Event()
    newer_committed = threading.Event()

    def write_older_from_stale_instance() -> None:
        close_old_connections()
        try:
            with transaction.atomic():
                stale_signal = Signal.objects.get(pk=signal.pk)
                stale_loaded.set()
                assert newer_committed.wait(timeout=10)
                stale_signal.title = "Concurrent business update"
                stale_signal.save(update_fields=["title", "updated_at"])
                touch_signal_activity(signal=stale_signal, at=older_at)
        finally:
            close_old_connections()

    def write_newer_activity() -> None:
        close_old_connections()
        try:
            assert stale_loaded.wait(timeout=10)
            with transaction.atomic():
                current_signal = Signal.objects.get(pk=signal.pk)
                touch_signal_activity(signal=current_signal, at=newer_at)
            newer_committed.set()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        older_future = executor.submit(write_older_from_stale_instance)
        newer_future = executor.submit(write_newer_activity)
        older_future.result(timeout=15)
        newer_future.result(timeout=15)

    signal.refresh_from_db()
    assert signal.title == "Concurrent business update"
    assert signal.last_activity_at == newer_at
