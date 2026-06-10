from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.permissions import (
    can_accept_action,
    can_cancel_action,
    can_mark_action_done,
    can_reassign_action,
    can_reopen_action,
    can_validate_action_on_object,
)
from houston.actions.services import accept_action, create_action, mark_action_done
from houston.actions.tests.conftest import (
    assign_business_unit_scope,
    build_api_membership,
    build_api_membership_on_establishment,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.taxonomy import hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _action_for_permissions(*, owner, staff, maintenance, status=Action.Status.OPEN):
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do it",
        assigned_to_id=staff.id,
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    if status == Action.Status.IN_PROGRESS:
        action = accept_action(action=action)
    elif status == Action.Status.PENDING_VALIDATION:
        action = accept_action(action=action)
        action = mark_action_done(action=action)
    elif status != Action.Status.OPEN:
        action.status = status
        action.save(update_fields=["status", "updated_at"])
    return action


def test_assignee_can_accept_open_action():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _action_for_permissions(owner=owner, staff=staff, maintenance=maintenance)

    assert can_accept_action(staff, action) is True
    assert can_accept_action(owner, action) is False


def test_assignee_can_mark_done_in_progress_action():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _action_for_permissions(
        owner=owner,
        staff=staff,
        maintenance=maintenance,
        status=Action.Status.IN_PROGRESS,
    )

    assert can_mark_action_done(staff, action) is True
    assert can_mark_action_done(owner, action) is False


def test_owner_can_validate_pending_action():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _action_for_permissions(
        owner=owner,
        staff=staff,
        maintenance=maintenance,
        status=Action.Status.PENDING_VALIDATION,
    )

    assert can_validate_action_on_object(owner, action) is True
    assert can_validate_action_on_object(staff, action) is False


def test_manager_creator_can_reopen_and_cancel():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager, maintenance)
    action = _action_for_permissions(
        owner=manager,
        staff=staff,
        maintenance=maintenance,
        status=Action.Status.PENDING_VALIDATION,
    )

    assert can_reopen_action(manager, action) is True
    assert can_cancel_action(manager, action) is True


def test_staff_cannot_validate_reopen_or_cancel():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _action_for_permissions(
        owner=owner,
        staff=staff,
        maintenance=maintenance,
        status=Action.Status.PENDING_VALIDATION,
    )

    assert can_validate_action_on_object(staff, action) is False
    assert can_reopen_action(staff, action) is False
    assert can_cancel_action(staff, action) is False


def test_owner_can_reassign_open_action():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _action_for_permissions(owner=owner, staff=staff, maintenance=maintenance)

    assert can_reassign_action(owner, action) is True
    assert can_reassign_action(staff, action) is False


def test_cross_establishment_membership_denied():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _action_for_permissions(owner=owner, staff=staff, maintenance=maintenance)

    assert can_accept_action(foreign, action) is False
    assert can_validate_action_on_object(foreign, action) is False
