from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone
from houston.actions.services import create_action
from houston.actions.tests.conftest import build_api_membership_on_establishment
from houston.comments.constants import (
    ALREADY_RESOLVED_ERROR_DETAIL,
    NOT_RESOLVED_ERROR_DETAIL,
)
from houston.comments.exceptions import CommentValidationError
from houston.comments.services import (
    create_action_comment,
    create_signal_comment,
    resolve_action_comment,
    unresolve_action_comment,
)
from houston.comments.tests.conftest import build_api_membership
from houston.establishments.models import EstablishmentMembership
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


def _staff(owner):
    return build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)


def _create_linked_action(*, owner, staff, signal, title: str = "Linked task"):
    return create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title=title,
        instruction="Sensitive instruction text",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timedelta(days=1),
        signal_id=signal.id,
    )


def _create_free_action(*, owner, staff):
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    return create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Free task",
        instruction="Sensitive instruction text",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )


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


def test_create_signal_comment_emits_signal_created_without_linked_action():
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


def test_create_signal_comment_emits_inherited_for_one_linked_action():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = _staff(owner)
    signal = _signal(owner)
    action = _create_linked_action(owner=owner, staff=staff, signal=signal)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        create_signal_comment(author_membership=owner, signal=signal, body="Sensitive body text")

        comment_calls = _comment_calls(mock_notify)
        assert len(comment_calls) == 2
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.signal.created",
            entity_id=signal.id,
            call_index=0,
        )
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.signal.inherited",
            entity_id=action.id,
            call_index=1,
        )


def test_create_signal_comment_emits_inherited_for_two_linked_actions():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = _staff(owner)
    signal = _signal(owner)
    action_one = _create_linked_action(owner=owner, staff=staff, signal=signal, title="First")
    action_two = _create_linked_action(owner=owner, staff=staff, signal=signal, title="Second")

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        create_signal_comment(author_membership=owner, signal=signal, body="Sensitive body text")

        comment_calls = _comment_calls(mock_notify)
        assert len(comment_calls) == 3
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.signal.created",
            entity_id=signal.id,
            call_index=0,
        )
        inherited_entity_ids = {
            call["entity_id"]
            for call in comment_calls
            if call["reason"] == "comment.signal.inherited"
        }
        assert inherited_entity_ids == {action_one.id, action_two.id}


def test_create_action_comment_root_emits_action_created():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = _staff(owner)
    action = _create_free_action(owner=owner, staff=staff)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        create_action_comment(author_membership=owner, action=action, body="Sensitive body text")

        comment_calls = _comment_calls(mock_notify)
        assert len(comment_calls) == 1
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.action.created",
            entity_id=action.id,
        )


def test_create_action_comment_reply_emits_action_created():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = _staff(owner)
    action = _create_free_action(owner=owner, staff=staff)
    root = create_action_comment(author_membership=owner, action=action, body="root")

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        create_action_comment(
            author_membership=staff,
            action=action,
            body="Sensitive reply text",
            parent_comment_id=root.id,
        )

        comment_calls = _comment_calls(mock_notify)
        assert len(comment_calls) == 1
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.action.created",
            entity_id=action.id,
        )


def test_resolve_action_comment_emits_action_resolved():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = _staff(owner)
    action = _create_free_action(owner=owner, staff=staff)
    root = create_action_comment(author_membership=owner, action=action, body="root")

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        resolve_action_comment(
            action=action,
            comment_id=root.id,
            resolved_by_membership=owner,
        )

        comment_calls = _comment_calls(mock_notify)
        assert len(comment_calls) == 1
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.action.resolved",
            entity_id=action.id,
        )


def test_unresolve_action_comment_emits_action_unresolved():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = _staff(owner)
    action = _create_free_action(owner=owner, staff=staff)
    root = create_action_comment(author_membership=owner, action=action, body="root")
    resolve_action_comment(
        action=action,
        comment_id=root.id,
        resolved_by_membership=owner,
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        unresolve_action_comment(action=action, comment_id=root.id)

        comment_calls = _comment_calls(mock_notify)
        assert len(comment_calls) == 1
        _assert_comment_invalidation(
            mock_notify,
            establishment_id=owner.establishment_id,
            reason="comment.action.unresolved",
            entity_id=action.id,
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


def test_resolve_action_comment_invalidation_not_emitted_on_rollback():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = _staff(owner)
    action = _create_free_action(owner=owner, staff=staff)
    root = create_action_comment(author_membership=owner, action=action, body="root")

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                resolve_action_comment(
                    action=action,
                    comment_id=root.id,
                    resolved_by_membership=owner,
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


def test_resolve_action_comment_already_resolved_does_not_emit():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = _staff(owner)
    action = _create_free_action(owner=owner, staff=staff)
    root = create_action_comment(author_membership=owner, action=action, body="root")
    resolve_action_comment(
        action=action,
        comment_id=root.id,
        resolved_by_membership=owner,
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(CommentValidationError, match=ALREADY_RESOLVED_ERROR_DETAIL):
            resolve_action_comment(
                action=action,
                comment_id=root.id,
                resolved_by_membership=owner,
            )

        comment_calls = _comment_calls(mock_notify)
        assert comment_calls == []


def test_unresolve_action_comment_not_resolved_does_not_emit():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = _staff(owner)
    action = _create_free_action(owner=owner, staff=staff)
    root = create_action_comment(author_membership=owner, action=action, body="root")

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(CommentValidationError, match=NOT_RESOLVED_ERROR_DETAIL):
            unresolve_action_comment(action=action, comment_id=root.id)

        comment_calls = _comment_calls(mock_notify)
        assert comment_calls == []


@pytest.mark.parametrize(
    "reason",
    [
        "comment.signal.created",
        "comment.signal.inherited",
        "comment.action.created",
        "comment.action.resolved",
        "comment.action.unresolved",
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
