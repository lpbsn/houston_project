from __future__ import annotations

import uuid

import pytest

from houston.accounts.models import User
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.comments.constants import (
    CANNOT_REPLY_TO_REPLY_ERROR_DETAIL,
    CANNOT_REPLY_TO_SIGNAL_COMMENT_FROM_EXECUTION_ERROR_DETAIL,
    INVALID_MENTIONS_ERROR_DETAIL,
    NOT_EXECUTION_ROOT_COMMENT_ERROR_DETAIL,
    SIGNAL_COMMENT_PARENT_NOT_ALLOWED_ERROR_DETAIL,
)
from houston.comments.exceptions import CommentValidationError
from houston.comments.services import (
    create_action_plan_execution_comment,
    create_signal_comment,
    normalize_comment_body,
    resolve_action_plan_execution_comment,
    unresolve_action_plan_execution_comment,
)
from houston.comments.tests.conftest import build_api_membership
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership_on_establishment,
)
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _signal(owner):
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    return create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )


def test_normalize_comment_body_trims_and_validates():
    assert normalize_comment_body("  hello  ") == "hello"


def test_normalize_comment_body_rejects_empty():
    with pytest.raises(CommentValidationError, match="required"):
        normalize_comment_body("   ")


def test_create_signal_comment_dedupes_mentions():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    mentioned_user = User.objects.create_user(
        username=f"m_{uuid.uuid4().hex[:8]}",
        password="secret",
        status=User.Status.ACTIVE,
    )
    mentioned = EstablishmentMembership.objects.create(
        user=mentioned_user,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    signal = _signal(owner)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="Regarde ceci",
        mentioned_membership_ids=[mentioned.id, mentioned.id],
    )

    assert comment.mention_links.count() == 1


def test_create_signal_comment_rejects_invalid_mention():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)

    with pytest.raises(CommentValidationError, match=INVALID_MENTIONS_ERROR_DETAIL):
        create_signal_comment(
            author_membership=owner,
            signal=signal,
            body="hello",
            mentioned_membership_ids=[uuid.uuid4()],
        )


def test_create_signal_comment_allows_self_mention():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="note",
        mentioned_membership_ids=[owner.id],
    )

    assert comment.mention_links.filter(mentioned_membership_id=owner.id).exists()


def test_create_signal_comment_rejects_parent_comment_id():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)

    with pytest.raises(
        CommentValidationError,
        match=SIGNAL_COMMENT_PARENT_NOT_ALLOWED_ERROR_DETAIL,
    ):
        create_signal_comment(
            author_membership=owner,
            signal=signal,
            body="hello",
            parent_comment_id=uuid.uuid4(),
        )


def _linked_execution(owner):
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)
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
    return staff, signal, execution


def test_create_execution_comment_rejects_reply_to_signal_comment():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _, signal, execution = _linked_execution(owner)
    signal_comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="signal",
    )

    with pytest.raises(
        CommentValidationError,
        match=CANNOT_REPLY_TO_SIGNAL_COMMENT_FROM_EXECUTION_ERROR_DETAIL,
    ):
        create_action_plan_execution_comment(
            author_membership=owner,
            execution=execution,
            body="reply",
            parent_comment_id=signal_comment.id,
        )


def test_create_execution_comment_rejects_reply_to_reply():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff, _, execution = _linked_execution(owner)
    root = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="root",
    )
    reply = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="reply",
        parent_comment_id=root.id,
    )

    with pytest.raises(CommentValidationError, match=CANNOT_REPLY_TO_REPLY_ERROR_DETAIL):
        create_action_plan_execution_comment(
            author_membership=owner,
            execution=execution,
            body="nested",
            parent_comment_id=reply.id,
        )


def test_resolve_execution_comment_on_root():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff, _, execution = _linked_execution(owner)
    root = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="root",
    )

    resolved = resolve_action_plan_execution_comment(
        execution=execution,
        comment_id=root.id,
        resolved_by_membership=owner,
    )

    assert resolved.resolved_at is not None
    assert resolved.resolved_by_membership_id == owner.id


def test_resolve_execution_comment_rejects_signal_root():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _, signal, execution = _linked_execution(owner)
    signal_comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="signal",
    )

    with pytest.raises(CommentValidationError, match=NOT_EXECUTION_ROOT_COMMENT_ERROR_DETAIL):
        resolve_action_plan_execution_comment(
            execution=execution,
            comment_id=signal_comment.id,
            resolved_by_membership=owner,
        )


def test_unresolve_execution_comment_on_root():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff, _, execution = _linked_execution(owner)
    root = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="root",
    )
    resolve_action_plan_execution_comment(
        execution=execution,
        comment_id=root.id,
        resolved_by_membership=owner,
    )

    unresolved = unresolve_action_plan_execution_comment(
        execution=execution,
        comment_id=root.id,
    )

    assert unresolved.resolved_at is None
    assert unresolved.resolved_by_membership_id is None
