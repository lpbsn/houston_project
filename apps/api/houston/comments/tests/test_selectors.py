from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.services import create_action
from houston.actions.tests.conftest import build_api_membership_on_establishment
from houston.comments.selectors import (
    get_action_for_comments,
    get_signal_for_comments,
    list_action_comments,
    list_action_comments_for_detail,
    list_signal_comments,
)
from houston.comments.services import create_action_comment, create_signal_comment
from houston.comments.tests.conftest import build_api_membership
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
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


def test_get_action_for_comments_includes_done_status():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal = _signal(owner)
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

    loaded = get_action_for_comments(membership=staff, action_id=action.id)
    assert loaded is not None


def test_list_action_comments_merges_inherited_signal_comments():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal = _signal(owner)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timedelta(days=1),
        signal_id=signal.id,
    )

    signal_comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="from signal",
    )
    action_comment = create_action_comment(
        author_membership=staff,
        action=action,
        body="from action",
    )

    comments = list_action_comments(action=action)
    assert [comment.id for comment in comments] == [signal_comment.id, action_comment.id]


def test_list_action_comments_without_signal_link():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Free",
        instruction="Do",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    comment = create_action_comment(
        author_membership=owner,
        action=action,
        body="only action",
    )

    comments = list_action_comments(action=action)
    assert len(comments) == 1
    assert comments[0].id == comment.id


def test_list_signal_comments_sorted_oldest_first():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)

    first = create_signal_comment(author_membership=owner, signal=signal, body="first")
    second = create_signal_comment(author_membership=owner, signal=signal, body="second")

    comments = list_signal_comments(signal=signal)
    assert [comment.id for comment in comments] == [first.id, second.id]


def test_list_action_comments_for_detail_groups_action_replies():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal = _signal(owner)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Task",
        instruction="Do",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timedelta(days=1),
        signal_id=signal.id,
    )

    signal_comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="from signal",
    )
    root = create_action_comment(
        author_membership=staff,
        action=action,
        body="from action",
    )
    reply = create_action_comment(
        author_membership=owner,
        action=action,
        body="reply",
        parent_comment_id=root.id,
    )

    entries = list_action_comments_for_detail(action=action)
    assert len(entries) == 2
    assert entries[0].kind == "inherited_signal"
    assert entries[0].comment.id == signal_comment.id
    assert entries[1].kind == "action_thread"
    assert entries[1].root.id == root.id
    assert [item.id for item in entries[1].replies] == [reply.id]
