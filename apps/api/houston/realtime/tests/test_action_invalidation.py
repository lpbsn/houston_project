from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone
from houston.actions.exceptions import ActionStateError
from houston.actions.models import Action
from houston.actions.services import (
    accept_action,
    cancel_action,
    create_action,
    mark_action_done,
    reassign_action,
    reopen_action,
    update_action_due_at,
    validate_action,
)
from houston.actions.tests.conftest import (
    build_api_membership,
    build_api_membership_on_establishment,
    create_signal_v3_for_membership,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.taxonomy import hotel_maintenance_setup

pytestmark = pytest.mark.django_db(transaction=True)

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "title",
        "instruction",
        "body",
        "assignee_ids",
        "status",
        "signal",
        "due_at",
    }
)


def _owner_staff_maintenance():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    return owner, staff, hotel, maintenance, electricite


def _create_free_action(*, owner, staff, maintenance, requires_validation: bool = True):
    return create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
        requires_validation=requires_validation,
    )


def _create_linked_action(*, owner, staff, signal):
    return create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked sensitive title",
        instruction="Linked sensitive instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        signal_id=signal.id,
    )


def _linked_signal(*, owner, hotel, maintenance, electricite):
    return create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.OPEN,
    )


def _assert_action_invalidation(
    mock_notify,
    *,
    action: Action,
    reason: str,
    call_index: int = -1,
) -> None:
    call = mock_notify.call_args_list[call_index]
    assert call.kwargs == {
        "establishment_id": action.establishment_id,
        "subject_type": "action",
        "reason": reason,
        "entity_id": action.id,
    }


def test_create_free_action_emits_action_created_after_commit():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        action = _create_free_action(owner=owner, staff=staff, maintenance=maintenance)

        mock_notify.assert_called_once()
        _assert_action_invalidation(mock_notify, action=action, reason="action.created")


def test_create_linked_action_emits_action_created_after_commit():
    owner, staff, hotel, maintenance, electricite = _owner_staff_maintenance()
    signal = _linked_signal(
        owner=owner,
        hotel=hotel,
        maintenance=maintenance,
        electricite=electricite,
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        action = _create_linked_action(owner=owner, staff=staff, signal=signal)

        action_calls = [
            call.kwargs
            for call in mock_notify.call_args_list
            if call.kwargs.get("subject_type") == "action"
        ]
        assert len(action_calls) == 1
        assert action_calls[0] == {
            "establishment_id": action.establishment_id,
            "subject_type": "action",
            "reason": "action.created",
            "entity_id": action.id,
        }


def test_accept_action_emits_action_updated_after_commit():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    action = _create_free_action(owner=owner, staff=staff, maintenance=maintenance)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        accept_action(action_id=action.id, accepted_by=staff)

        mock_notify.assert_called_once()
        _assert_action_invalidation(mock_notify, action=action, reason="action.updated")


def test_mark_action_done_pending_validation_emits_action_updated():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    action = _create_free_action(
        owner=owner,
        staff=staff,
        maintenance=maintenance,
        requires_validation=True,
    )
    accept_action(action_id=action.id, accepted_by=staff)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        updated = mark_action_done(action_id=action.id)

        assert updated.status == Action.Status.PENDING_VALIDATION
        mock_notify.assert_called_once()
        _assert_action_invalidation(mock_notify, action=action, reason="action.updated")


def test_mark_action_done_direct_done_emits_action_updated():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    action = _create_free_action(
        owner=owner,
        staff=staff,
        maintenance=maintenance,
        requires_validation=False,
    )
    accept_action(action_id=action.id, accepted_by=staff)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        updated = mark_action_done(action_id=action.id)

        assert updated.status == Action.Status.DONE
        mock_notify.assert_called_once()
        _assert_action_invalidation(mock_notify, action=action, reason="action.updated")


def test_validate_action_emits_action_updated_after_commit():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    action = _create_free_action(owner=owner, staff=staff, maintenance=maintenance)
    accept_action(action_id=action.id, accepted_by=staff)
    mark_action_done(action_id=action.id)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        validate_action(action_id=action.id)

        mock_notify.assert_called_once()
        _assert_action_invalidation(mock_notify, action=action, reason="action.updated")


def test_reopen_action_emits_action_updated_after_commit():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    action = _create_free_action(owner=owner, staff=staff, maintenance=maintenance)
    accept_action(action_id=action.id, accepted_by=staff)
    mark_action_done(action_id=action.id)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        reopen_action(action_id=action.id)

        mock_notify.assert_called_once()
        _assert_action_invalidation(mock_notify, action=action, reason="action.updated")


def test_cancel_action_emits_action_updated_after_commit():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    action = _create_free_action(owner=owner, staff=staff, maintenance=maintenance)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        cancel_action(action_id=action.id)

        mock_notify.assert_called_once()
        _assert_action_invalidation(mock_notify, action=action, reason="action.updated")


def test_reassign_action_emits_action_updated_after_commit():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    action = _create_free_action(owner=owner, staff=staff, maintenance=maintenance)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        reassign_action(action_id=action.id, assignee_ids=[other_staff.id])

        mock_notify.assert_called_once()
        _assert_action_invalidation(mock_notify, action=action, reason="action.updated")


def test_update_action_due_at_emits_action_updated_after_commit():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    action = _create_free_action(owner=owner, staff=staff, maintenance=maintenance)
    new_due_at = timezone.now() + timezone.timedelta(days=3)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        update_action_due_at(action_id=action.id, due_at=new_due_at)

        mock_notify.assert_called_once()
        _assert_action_invalidation(mock_notify, action=action, reason="action.updated")


def test_action_invalidation_not_emitted_on_accept_rollback():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    action = _create_free_action(owner=owner, staff=staff, maintenance=maintenance)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                accept_action(action_id=action.id, accepted_by=staff)
                raise RuntimeError("force rollback")

        mock_notify.assert_not_called()


def test_action_invalidation_not_emitted_on_cancel_rollback():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    action = _create_free_action(owner=owner, staff=staff, maintenance=maintenance)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                cancel_action(action_id=action.id)
                raise RuntimeError("force rollback")

        mock_notify.assert_not_called()


def test_accept_action_validation_failure_does_not_emit():
    owner, staff, _, maintenance, _ = _owner_staff_maintenance()
    action = _create_free_action(owner=owner, staff=staff, maintenance=maintenance)
    action.status = Action.Status.DONE
    action.save(update_fields=["status", "updated_at"])

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(ActionStateError, match="cannot be accepted"):
            accept_action(action_id=action.id, accepted_by=staff)

        mock_notify.assert_not_called()


@pytest.mark.parametrize("reason", ["action.created", "action.updated"])
def test_action_invalidate_payload_has_no_sensitive_fields(reason: str):
    from houston.realtime.ws_payloads import build_invalidate_payload

    establishment_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    payload = build_invalidate_payload(
        subject_type="action",
        reason=reason,
        establishment_id=establishment_id,
        entity_id=entity_id,
    )

    allowed = {"type", "subject_type", "reason", "establishment_id", "entity_id", "occurred_at"}
    assert set(payload.keys()) == allowed
    assert payload["type"] == "invalidate"
    assert payload["subject_type"] == "action"
    assert payload["reason"] == reason
    assert FORBIDDEN_PAYLOAD_KEYS.isdisjoint(payload.keys())

    payload_blob = " ".join(str(value) for value in payload.values()).lower()
    assert "sensitive" not in payload_blob
    assert "instruction" not in payload_blob
    assert "title" not in payload_blob
