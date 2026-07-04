from __future__ import annotations

import pytest

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.comments.selectors import (
    get_action_plan_execution_for_comments,
    get_signal_for_comments,
    list_action_plan_execution_comments_for_detail,
    list_signal_comments,
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


def _signal(owner, *, status=Signal.Status.OPEN):
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    return create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=status,
    )


@pytest.mark.parametrize(
    "status",
    [Signal.Status.ARCHIVED],
)
def test_get_signal_for_comments_returns_none_for_non_detail_statuses(status):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner, status=status)

    loaded = get_signal_for_comments(membership=owner, signal_id=signal.id)
    assert loaded is None


def test_get_signal_for_comments_returns_canceled_signal_for_admin():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner, status=Signal.Status.CANCELED)

    loaded = get_signal_for_comments(membership=owner, signal_id=signal.id)
    assert loaded is not None
    assert loaded.status == Signal.Status.CANCELED


def test_list_signal_comments_sorted_oldest_first():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)

    first = create_signal_comment(author_membership=owner, signal=signal, body="first")
    second = create_signal_comment(author_membership=owner, signal=signal, body="second")

    comments = list_signal_comments(signal=signal)
    assert [comment.id for comment in comments] == [first.id, second.id]


def test_list_execution_comments_for_detail_groups_execution_replies():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal = _signal(owner)
    maintenance = signal.responsible_business_unit
    assign_business_unit_scope(staff, maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Execution comments",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )

    signal_comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="from signal",
    )
    root = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="from execution",
    )
    reply = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="reply",
        parent_comment_id=root.id,
    )

    entries = list_action_plan_execution_comments_for_detail(execution=execution)
    assert len(entries) == 2
    assert entries[0].kind == "inherited_signal"
    assert entries[0].comment.id == signal_comment.id
    assert entries[1].kind == "execution_thread"
    assert entries[1].root.id == root.id
    assert [item.id for item in entries[1].replies] == [reply.id]


def test_get_action_plan_execution_for_comments_returns_none_for_invisible_execution():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    outsider = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Scoped execution",
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )

    loaded = get_action_plan_execution_for_comments(
        membership=outsider,
        execution_id=execution.id,
    )
    assert loaded is None
