from __future__ import annotations

import pytest

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.comments.permissions import (
    can_access_action_plan_execution_comments,
    can_access_signal_comments,
    can_resolve_execution_comment,
)
from houston.comments.services import (
    create_action_plan_execution_comment,
    create_signal_comment,
)
from houston.comments.tests.conftest import build_api_membership
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
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


def _linked_execution():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
    assign_business_unit_scope(manager, maintenance)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Execution",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    return owner, staff, manager, execution


def test_assignee_can_access_execution_comments():
    owner, staff, _, execution = _linked_execution()
    assert (
        can_access_action_plan_execution_comments(
            membership=staff,
            execution_id=execution.id,
        )
        is True
    )


def test_can_resolve_execution_comment_author_assignee_creator_admin_manager():
    owner, staff, manager, execution = _linked_execution()
    root = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="root",
    )

    assert (
        can_resolve_execution_comment(membership=staff, execution=execution, comment=root) is True
    )
    assert (
        can_resolve_execution_comment(membership=owner, execution=execution, comment=root) is True
    )
    assert (
        can_resolve_execution_comment(membership=manager, execution=execution, comment=root) is True
    )


def test_can_resolve_execution_comment_rejects_signal_root():
    owner, staff, _, execution = _linked_execution()
    signal_comment = create_signal_comment(
        author_membership=owner,
        signal=execution.source_signal,
        body="signal",
    )

    assert (
        can_resolve_execution_comment(
            membership=owner,
            execution=execution,
            comment=signal_comment,
        )
        is False
    )


def test_can_resolve_execution_comment_rejects_unrelated_staff():
    owner, staff, _, execution = _linked_execution()
    outsider = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    root = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="root",
    )

    assert (
        can_resolve_execution_comment(membership=outsider, execution=execution, comment=root)
        is False
    )
