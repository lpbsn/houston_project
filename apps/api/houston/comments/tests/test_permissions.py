from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.services import create_action
from houston.actions.tests.conftest import build_api_membership_on_establishment
from houston.comments.permissions import can_access_action_comments, can_access_signal_comments
from houston.comments.tests.conftest import build_api_membership
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def test_owner_cannot_access_signal_comments_on_archived_signal():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.ARCHIVED,
    )

    assert can_access_signal_comments(membership=owner, signal_id=signal.id) is False


def test_assignee_can_access_done_action_comments():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timedelta(days=1),
        signal_id=signal.id,
    )
    action.status = Action.Status.DONE
    action.save(update_fields=["status", "updated_at"])

    assert can_access_action_comments(membership=staff, action_id=action.id) is True
