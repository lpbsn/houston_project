import pytest

from houston.action_plans.tests.helpers import create_execution, create_open_signal
from houston.notifications.models import Notification
from houston.notifications.recipients import resolve_signal_reporter_recipients
from houston.notifications.scheduling import (
    emit_action_plan_execution_availability_if_due,
    schedule_signal_resolved_notification,
)
from houston.signals.models import SignalSourceObservation
from houston.testing.factories import create_membership
from houston.testing.pipeline import create_observation

pytestmark = pytest.mark.django_db(transaction=True)


def link(signal, member, link_type="aggregated_from"):
    return SignalSourceObservation.objects.create(
        signal=signal,
        observation=create_observation(membership=member),
        link_type=link_type,
    )


def test_all_reporters_are_deduplicated_and_inactive_members_excluded(
    owner_membership, staff_membership
):
    signal = create_open_signal(owner_membership=owner_membership)
    link(signal, staff_membership, "created_from")
    link(signal, staff_membership)
    inactive = create_membership(
        establishment=signal.establishment, role="staff", status="deactivated"
    )
    link(signal, inactive)
    assert [m.id for m in resolve_signal_reporter_recipients(signal=signal)] == [
        staff_membership.id
    ]


def test_resolved_signal_notifies_reporter_outside_its_pole(owner_membership, staff_membership):
    signal = create_open_signal(owner_membership=owner_membership)
    link(signal, staff_membership)
    signal.status = "resolved"
    signal.save(update_fields=["status"])
    schedule_signal_resolved_notification(
        signal_id=signal.id, actor_membership_id=owner_membership.id
    )
    assert (
        Notification.objects.filter(
            recipient_membership=staff_membership,
            subject_id=signal.id,
            event_key="signal.resolved",
        ).count()
        == 1
    )


def test_plan_followup_points_to_signal_and_is_idempotent(
    owner_membership, staff_membership, business_unit
):
    signal = create_open_signal(owner_membership=owner_membership)
    link(signal, staff_membership)
    execution = create_execution(owner_membership, business_unit=business_unit, title="Corriger")
    execution.source_signal = signal
    execution.availability_notified_at = None
    execution.save(update_fields=["source_signal", "availability_notified_at"])
    for _ in range(2):
        emit_action_plan_execution_availability_if_due(
            execution_id=execution.id,
            actor_membership_id=owner_membership.id,
        )
    notices = Notification.objects.filter(
        recipient_membership=staff_membership,
        event_key="action_plan.execution.created_from_signal",
    )
    assert notices.count() == 1
    assert notices.get().subject_type == "signal"
    assert notices.get().subject_id == signal.id
