from __future__ import annotations

import pytest
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.signals.constants import (
    SIGNAL_IN_PROGRESS_MANUAL_CANCEL_DETAIL,
    SIGNAL_IN_PROGRESS_MANUAL_RESOLVE_DETAIL,
)
from houston.signals.exceptions import SignalStateError
from houston.signals.models import Signal
from houston.signals.services import (
    cancel_signal,
    resolve_signal,
    resolve_signal_from_execution_sync,
)
from houston.signals.tests.conftest import build_api_membership, create_minimal_v3_signal

pytestmark = pytest.mark.django_db


def _signal(*, status: str = Signal.Status.OPEN):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    return create_minimal_v3_signal(membership, title="Issue", status=status)


def test_cancel_signal_sets_canceled_and_clears_pin():
    signal = _signal()
    signal.is_pinned = True
    signal.pinned_at = timezone.now()
    signal.save(update_fields=["is_pinned", "pinned_at", "updated_at"])

    result = cancel_signal(signal=signal)

    assert result.status == Signal.Status.CANCELED
    assert result.is_pinned is False
    assert result.pinned_at is None
    assert result.pinned_by_membership_id is None


def test_resolve_signal_sets_resolved_from_open():
    signal = _signal(status=Signal.Status.OPEN)

    result = resolve_signal(signal=signal)

    assert result.status == Signal.Status.RESOLVED


def test_resolve_signal_rejects_in_progress():
    signal = _signal(status=Signal.Status.IN_PROGRESS)

    with pytest.raises(SignalStateError, match=SIGNAL_IN_PROGRESS_MANUAL_RESOLVE_DETAIL):
        resolve_signal(signal=signal)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS


def test_cancel_signal_rejects_in_progress():
    signal = _signal(status=Signal.Status.IN_PROGRESS)

    with pytest.raises(SignalStateError, match=SIGNAL_IN_PROGRESS_MANUAL_CANCEL_DETAIL):
        cancel_signal(signal=signal)

    signal.refresh_from_db()
    assert signal.status == Signal.Status.IN_PROGRESS


def test_resolve_signal_from_execution_sync_allows_in_progress():
    signal = _signal(status=Signal.Status.IN_PROGRESS)

    result = resolve_signal_from_execution_sync(signal=signal)

    assert result.status == Signal.Status.RESOLVED


def test_resolve_signal_clears_pin_fields():
    signal = _signal()
    signal.is_pinned = True
    signal.pinned_at = timezone.now()
    signal.save(update_fields=["is_pinned", "pinned_at", "updated_at"])

    result = resolve_signal(signal=signal)

    assert result.is_pinned is False
    assert result.pinned_at is None
    assert result.pinned_by_membership_id is None


def test_cancel_signal_rejects_terminal_status():
    signal = _signal(status=Signal.Status.RESOLVED)

    with pytest.raises(SignalStateError):
        cancel_signal(signal=signal)
