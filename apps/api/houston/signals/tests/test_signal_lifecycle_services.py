from __future__ import annotations

import pytest
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.signals.exceptions import SignalStateError
from houston.signals.models import Signal
from houston.signals.services import cancel_signal, resolve_signal
from houston.signals.tests.conftest import build_api_membership, create_taxonomy

pytestmark = pytest.mark.django_db


def _signal(*, status: str = Signal.Status.OPEN):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    module, domain, subject = create_taxonomy(membership.establishment)
    now = timezone.now()
    return Signal.objects.create(
        establishment=membership.establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
        title="Issue",
        structured_summary="Summary",
        status=status,
        last_activity_at=now,
    )


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


def test_resolve_signal_sets_resolved():
    signal = _signal(status=Signal.Status.IN_PROGRESS)

    result = resolve_signal(signal=signal)

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


def test_resolve_signal_resets_high_urgency_to_normal():
    signal = _signal()
    signal.urgency = Signal.Urgency.HIGH
    signal.save(update_fields=["urgency", "updated_at"])

    result = resolve_signal(signal=signal)

    assert result.urgency == Signal.Urgency.NORMAL


def test_cancel_signal_does_not_reset_high_urgency():
    signal = _signal()
    signal.urgency = Signal.Urgency.HIGH
    signal.save(update_fields=["urgency", "updated_at"])

    result = cancel_signal(signal=signal)

    assert result.urgency == Signal.Urgency.HIGH


def test_cancel_signal_rejects_terminal_status():
    signal = _signal(status=Signal.Status.RESOLVED)

    with pytest.raises(SignalStateError):
        cancel_signal(signal=signal)
