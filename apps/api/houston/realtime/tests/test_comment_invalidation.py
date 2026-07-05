from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.comments.exceptions import CommentValidationError
from houston.comments.services import (
    create_action_plan_execution_comment,
    create_signal_comment,
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

pytestmark = pytest.mark.django_db(transaction=True)

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "body",
        "mentions",
        "title",
        "instruction",
        "author",
        "parent_comment",
    }
)

ALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "type",
        "subject_type",
        "reason",
        "establishment_id",
        "entity_id",
        "occurred_at",
    }
)


def _signal(owner):
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    return create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )


def _staff(owner, *, maintenance=None):
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    if maintenance is not None:
        assign_business_unit_scope(staff, maintenance)
    return staff


def _comment_calls(mock_notify):
    return [
        call.kwargs
        for call in mock_notify.call_args_list
        if call.kwargs.get("subject_type") == "comment"
    ]


def _assert_comment_invalidation(
    mock_notify,
    *,
    establishment_id: uuid.UUID,
    reason: str,
    entity_id: uuid.UUID,
    call_index: int = -1,
) -> None:
    comment_calls = _comment_calls(mock_notify)
    assert comment_calls[call_index] == {
        "establishment_id": establishment_id,
        "subject_type": "comment",
        "reason": reason,
        "entity_id": entity_id,
    }


def test_create_signal_comment_emits_signal_created():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        create_signal_comment(author_membership=owner, signal=signal, body="Sensitive body text")

        comment_calls = _comment_calls(mock_notify)
        assert len(comment_calls) == 1
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.signal.created",
            entity_id=signal.id,
        )


def test_create_signal_comment_emits_inherited_execution_invalidation():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)
    maintenance = signal.responsible_business_unit
    staff = _staff(owner, maintenance=maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Linked execution",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        create_signal_comment(author_membership=owner, signal=signal, body="signal note")

        comment_calls = _comment_calls(mock_notify)
        inherited_entity_ids = {
            call["entity_id"]
            for call in comment_calls
            if call["reason"] == "comment.signal.inherited"
        }
        assert execution.id in inherited_entity_ids


def test_create_execution_comment_root_emits_execution_created():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    staff = _staff(owner, maintenance=maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Execution",
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        create_action_plan_execution_comment(
            author_membership=owner,
            execution=execution,
            body="Sensitive body text",
        )

        comment_calls = _comment_calls(mock_notify)
        assert len(comment_calls) == 1
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.execution.created",
            entity_id=execution.id,
        )


def test_resolve_execution_comment_emits_execution_resolved():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    staff = _staff(owner, maintenance=maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Execution",
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    root = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="root",
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        resolve_action_plan_execution_comment(
            execution=execution,
            comment_id=root.id,
            resolved_by_membership=owner,
        )

        comment_calls = _comment_calls(mock_notify)
        assert len(comment_calls) == 1
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.execution.resolved",
            entity_id=execution.id,
        )


def test_unresolve_execution_comment_emits_execution_unresolved():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    staff = _staff(owner, maintenance=maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Execution",
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    root = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="root",
    )
    resolve_action_plan_execution_comment(
        execution=execution,
        comment_id=root.id,
        resolved_by_membership=owner,
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        unresolve_action_plan_execution_comment(execution=execution, comment_id=root.id)

        comment_calls = _comment_calls(mock_notify)
        assert len(comment_calls) == 1
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.execution.unresolved",
            entity_id=execution.id,
        )


def test_create_signal_comment_invalidation_not_emitted_on_rollback():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                create_signal_comment(
                    author_membership=owner,
                    signal=signal,
                    body="Sensitive body text",
                )
                raise RuntimeError("force rollback")

        comment_calls = _comment_calls(mock_notify)
        assert comment_calls == []


def test_create_signal_comment_validation_failure_does_not_emit():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(owner)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(CommentValidationError, match="required"):
            create_signal_comment(author_membership=owner, signal=signal, body="   ")

        comment_calls = _comment_calls(mock_notify)
        assert comment_calls == []


@pytest.mark.parametrize(
    "reason",
    [
        "comment.signal.created",
        "comment.signal.inherited",
        "comment.execution.created",
        "comment.execution.resolved",
        "comment.execution.unresolved",
    ],
)
def test_comment_invalidate_payload_allowlist(reason: str):
    from houston.realtime.ws_payloads import build_invalidate_payload

    establishment_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    payload = build_invalidate_payload(
        subject_type="comment",
        reason=reason,
        establishment_id=establishment_id,
        entity_id=entity_id,
    )

    assert set(payload.keys()) == ALLOWED_PAYLOAD_KEYS
    assert payload["type"] == "invalidate"
    assert payload["subject_type"] == "comment"
    assert payload["reason"] == reason
    assert FORBIDDEN_PAYLOAD_KEYS.isdisjoint(payload.keys())

    payload_blob = " ".join(str(value) for value in payload.values()).lower()
    assert "sensitive" not in payload_blob
    assert "body" not in payload_blob
