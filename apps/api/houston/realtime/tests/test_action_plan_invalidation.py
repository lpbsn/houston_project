from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from houston.action_plans.constants import CATALOG_STATUS_ACTIVE
from houston.action_plans.exceptions import ActionPlanStateError
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import (
    cancel_action_plan_execution,
    create_action_plan,
    create_action_plan_with_execution,
    create_execution_from_action_plan,
    mark_action_plan_execution_done,
    mark_execution_task_done,
    reopen_action_plan_execution,
    validate_action_plan_execution,
)
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.signals.services import resolve_signal

pytestmark = pytest.mark.django_db(transaction=True)

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


def _assert_execution_invalidation(
    mock_notify,
    *,
    execution: ActionPlanExecution,
    reason: str,
    call_index: int = -1,
) -> None:
    call = mock_notify.call_args_list[call_index]
    assert call.kwargs == {
        "establishment_id": execution.establishment_id,
        "subject_type": "action_plan_execution",
        "reason": reason,
        "entity_id": execution.id,
    }


def test_create_catalog_plan_emits_action_plan_created(
    owner_membership,
    business_unit,
):
    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        plan = create_action_plan(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="Catalog plan",
            tasks=[build_task_payload(task="Daily prep", business_unit=business_unit)],
            is_reusable=True,
            catalog_status=CATALOG_STATUS_ACTIVE,
        )
        transaction.on_commit(lambda: None)

    mock_notify.assert_called_once_with(
        establishment_id=plan.establishment_id,
        subject_type="action_plan",
        reason="action_plan.created",
        entity_id=plan.id,
    )


def test_create_ponctuel_emits_plan_and_execution_created(
    owner_membership,
    business_unit,
    staff_membership,
):
    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        plan, execution = create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="One-shot plan",
            tasks=[build_task_payload(task="Task", business_unit=business_unit)],
            assignees=[
                build_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        )
        transaction.on_commit(lambda: None)

    reasons = [
        call.kwargs["reason"]
        for call in mock_notify.call_args_list
        if call.kwargs.get("subject_type") == "action_plan_execution"
    ]
    plan_reasons = [
        call.kwargs["reason"]
        for call in mock_notify.call_args_list
        if call.kwargs.get("subject_type") == "action_plan"
    ]
    assert "action_plan.created" in plan_reasons
    assert "action_plan_execution.created" in reasons
    _assert_execution_invalidation(
        mock_notify,
        execution=execution,
        reason="action_plan_execution.created",
    )


def test_mark_done_pending_validation_emits_pending_validation_reason(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Validation plan",
        requires_validation=True,
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        mark_action_plan_execution_done(
            execution_id=execution.id,
            actor_membership=staff_membership,
        )
        transaction.on_commit(lambda: None)

    _assert_execution_invalidation(
        mock_notify,
        execution=execution,
        reason="action_plan_execution.pending_validation",
    )


def test_mark_done_without_validation_emits_done_reason(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Direct done plan",
        requires_validation=False,
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        mark_action_plan_execution_done(
            execution_id=execution.id,
            actor_membership=staff_membership,
        )
        transaction.on_commit(lambda: None)

    _assert_execution_invalidation(
        mock_notify,
        execution=execution,
        reason="action_plan_execution.done",
    )


def test_validate_emits_done_reason(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Validate plan",
        requires_validation=True,
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=staff_membership,
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        validate_action_plan_execution(
            execution_id=execution.id,
            actor_membership=owner_membership,
        )
        transaction.on_commit(lambda: None)

    _assert_execution_invalidation(
        mock_notify,
        execution=execution,
        reason="action_plan_execution.done",
    )


def test_cancel_emits_canceled_reason(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Cancel plan",
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        cancel_action_plan_execution(
            execution_id=execution.id,
            actor=owner_membership,
        )
        transaction.on_commit(lambda: None)

    _assert_execution_invalidation(
        mock_notify,
        execution=execution,
        reason="action_plan_execution.canceled",
    )


def test_reopen_emits_updated_reason(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Reopen plan",
        requires_validation=False,
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=staff_membership,
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        reopen_action_plan_execution(
            execution_id=execution.id,
            actor=owner_membership,
        )
        transaction.on_commit(lambda: None)

    _assert_execution_invalidation(
        mock_notify,
        execution=execution,
        reason="action_plan_execution.updated",
    )


def test_task_mark_done_emits_task_and_execution_updated(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Task plan",
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    task = execution.task_executions.first()
    assert task is not None

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        mark_execution_task_done(
            task_execution=task,
            actor=staff_membership,
        )
        transaction.on_commit(lambda: None)

    assert any(
        call.kwargs.get("subject_type") == "action_plan_execution_task"
        and call.kwargs.get("reason") == "action_plan_execution_task.updated"
        for call in mock_notify.call_args_list
    )
    assert any(
        call.kwargs
        == {
            "establishment_id": execution.establishment_id,
            "subject_type": "action_plan_execution",
            "reason": "action_plan_execution.updated",
            "entity_id": execution.id,
        }
        for call in mock_notify.call_args_list
    )


def test_create_execution_from_catalog_emits_created(
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        execution = create_execution_from_action_plan(
            action_plan_id=catalog_action_plan.id,
            actor=owner_membership,
            assignees=[
                build_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        )
        transaction.on_commit(lambda: None)

    _assert_execution_invalidation(
        mock_notify,
        execution=execution,
        reason="action_plan_execution.created",
    )


def test_invalidation_not_emitted_on_cancel_rollback(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Rollback plan",
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(ActionPlanStateError):
            with transaction.atomic():
                cancel_action_plan_execution(
                    execution_id=execution.id,
                    actor=owner_membership,
                )
                raise ActionPlanStateError("force rollback")
        transaction.on_commit(lambda: None)

    mock_notify.assert_not_called()


def test_signal_resolve_cancels_linked_executions_with_canceled_invalidation(
    owner_membership,
    signal,
):
    responsible_business_unit = signal.responsible_business_unit
    assert responsible_business_unit is not None
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=responsible_business_unit.id,
        title="Signal linked plan",
        source_signal_id=signal.id,
        tasks=[
            build_task_payload(task="Task", business_unit=responsible_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=responsible_business_unit,
            )
        ],
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        resolve_signal(signal=signal, actor_membership=owner_membership)
        transaction.on_commit(lambda: None)

    execution.refresh_from_db()
    assert execution.status == ActionPlanExecution.Status.CANCELED
    assert any(
        call.kwargs
        == {
            "establishment_id": execution.establishment_id,
            "subject_type": "action_plan_execution",
            "reason": "action_plan_execution.canceled",
            "entity_id": execution.id,
        }
        for call in mock_notify.call_args_list
    )


def test_invalidation_payload_has_no_sensitive_fields(
    owner_membership,
    business_unit,
    staff_membership,
):
    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        _, execution = create_action_plan_with_execution(
            establishment_id=owner_membership.establishment_id,
            created_by=owner_membership,
            pilot_business_unit_id=business_unit.id,
            title="Sensitive plan title",
            description="Sensitive description",
            tasks=[build_task_payload(task="Sensitive task", business_unit=business_unit)],
            assignees=[
                build_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        )
        transaction.on_commit(lambda: None)

    for call in mock_notify.call_args_list:
        allowed_keys = ALLOWED_PAYLOAD_KEYS | {
            "establishment_id",
            "subject_type",
            "reason",
            "entity_id",
        }
        assert set(call.kwargs) <= allowed_keys
        for key, value in call.kwargs.items():
            if key == "entity_id":
                assert isinstance(value, uuid.UUID)
