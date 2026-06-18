from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.services import accept_action, create_action
from houston.actions.tests.conftest import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
from houston.comments.permissions import (
    can_access_action_comments,
    can_access_signal_comments,
    can_resolve_action_comment,
)
from houston.comments.services import create_action_comment, create_signal_comment
from houston.comments.tests.conftest import build_api_membership
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _linked_action():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager, maintenance)
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
    return owner, staff, manager, action


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
    owner, staff, _, action = _linked_action()
    action.status = Action.Status.DONE
    action.save(update_fields=["status", "updated_at"])

    assert can_access_action_comments(membership=staff, action_id=action.id) is True


def test_can_resolve_action_comment_author_assignee_creator_admin_manager():
    owner, staff, manager, action = _linked_action()
    root = create_action_comment(author_membership=staff, action=action, body="root")

    assert can_resolve_action_comment(membership=staff, action=action, comment=root) is True
    assert can_resolve_action_comment(membership=owner, action=action, comment=root) is True
    assert can_resolve_action_comment(membership=manager, action=action, comment=root) is True

    action.accepted_by = staff
    action.save(update_fields=["accepted_by", "updated_at"])
    assert can_resolve_action_comment(membership=staff, action=action, comment=root) is True

    assert can_resolve_action_comment(membership=owner, action=action, comment=root) is True


def test_can_resolve_action_comment_creator():
    owner, staff, _, action = _linked_action()
    root = create_action_comment(author_membership=staff, action=action, body="root")

    assert can_resolve_action_comment(membership=owner, action=action, comment=root) is True


def test_can_resolve_action_comment_rejects_signal_root():
    owner, staff, _, action = _linked_action()
    signal_comment = create_signal_comment(
        author_membership=owner,
        signal=action.signal,
        body="signal",
    )

    assert (
        can_resolve_action_comment(membership=owner, action=action, comment=signal_comment)
        is False
    )


def test_can_resolve_action_comment_rejects_unrelated_staff():
    owner, staff, _, action = _linked_action()
    outsider = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    root = create_action_comment(author_membership=staff, action=action, body="root")

    assert can_resolve_action_comment(membership=outsider, action=action, comment=root) is False


def test_accepted_by_can_resolve_action_comment():
    owner, staff, _, action = _linked_action()
    action = accept_action(action_id=action.id, accepted_by=staff)
    root = create_action_comment(author_membership=owner, action=action, body="root")

    assert can_resolve_action_comment(membership=staff, action=action, comment=root) is True
