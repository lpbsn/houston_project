from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone
from houston.checklists.constants import EXECUTION_SOURCE_ASSIGNMENT
from houston.checklists.exceptions import ChecklistPermissionError
from houston.checklists.models import ChecklistAssignment, ChecklistExecution, ChecklistTemplate
from houston.checklists.services import (
    add_task_template,
    create_checklist_assignment,
    create_checklist_template,
    create_execution_from_template,
    create_observation_from_task,
    create_registered_checklist_template,
    mark_task_done,
    update_checklist_template,
)
from houston.checklists.tests.conftest import add_task_template as add_task_fixture
from houston.checklists.tests.conftest import stable_assignment_times
from houston.observations.models import Observation

pytestmark = pytest.mark.django_db(transaction=True)

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "title",
        "description",
        "task",
        "template_title",
        "body",
        "raw_text",
        "status",
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


def _assert_checklist_invalidation(
    mock_notify,
    *,
    template: ChecklistTemplate,
    call_index: int = -1,
) -> None:
    call = mock_notify.call_args_list[call_index]
    assert call.kwargs == {
        "establishment_id": template.establishment_id,
        "subject_type": "checklist",
        "reason": "checklist.updated",
        "entity_id": template.id,
    }


def _assert_execution_invalidation(
    mock_notify,
    *,
    execution: ChecklistExecution,
    reason: str,
    call_index: int = -1,
) -> None:
    call = mock_notify.call_args_list[call_index]
    assert call.kwargs == {
        "establishment_id": execution.establishment_id,
        "subject_type": "execution",
        "reason": reason,
        "entity_id": execution.id,
    }


def _active_template_with_task(owner_membership, business_unit) -> ChecklistTemplate:
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        title="Sensitive checklist title",
        description="Sensitive checklist description",
        business_unit_id=business_unit.id,
    )
    add_task_fixture(template=template, task="Sensitive task text", position=1)
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    return template


def test_create_checklist_template_emits_checklist_updated_after_commit(
    owner_membership,
    business_unit,
):
    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        template = create_checklist_template(
            establishment_id=owner_membership.establishment_id,
            actor=owner_membership,
            title="Opening",
            business_unit_id=business_unit.id,
        )

        mock_notify.assert_called_once()
        _assert_checklist_invalidation(mock_notify, template=template)


def test_update_checklist_template_emits_checklist_updated(owner_membership, business_unit):
    template = _active_template_with_task(owner_membership, business_unit)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        update_checklist_template(
            template=template,
            actor=owner_membership,
            title="Updated title",
        )

        mock_notify.assert_called_once()
        _assert_checklist_invalidation(mock_notify, template=template)


def test_add_task_template_emits_checklist_updated(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        title="Tasks",
        business_unit_id=business_unit.id,
    )

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        add_task_template(
            template=template,
            actor=owner_membership,
            task="New task",
        )

        mock_notify.assert_called_once()
        _assert_checklist_invalidation(mock_notify, template=template)


def test_create_execution_from_template_emits_execution_created(
    owner_membership,
    business_unit,
    staff_membership,
):
    template = _active_template_with_task(owner_membership, business_unit)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        execution = create_execution_from_template(
            template=template,
            actor=owner_membership,
            assigned_to_id=staff_membership.id,
        )

        mock_notify.assert_called_once()
        _assert_execution_invalidation(
            mock_notify,
            execution=execution,
            reason="execution.created",
        )


def test_create_checklist_assignment_emits_checklist_and_execution_created(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_template_with_task(owner_membership, business_unit)
    start_at, end_at = stable_assignment_times(duration_hours=2)
    today = timezone.now().date()

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        create_checklist_assignment(
            template=template,
            actor=owner_membership,
            assigned_to_id=staff_membership.id,
            start_date=today,
            end_date=today,
            start_at=start_at,
            end_at=end_at,
        )

        assert mock_notify.call_count == 2
        _assert_checklist_invalidation(mock_notify, template=template, call_index=0)
        execution = ChecklistExecution.objects.get(checklist_template=template)
        _assert_execution_invalidation(
            mock_notify,
            execution=execution,
            reason="execution.created",
            call_index=1,
        )


def test_create_checklist_assignment_skips_execution_created_when_already_materialized(
    owner_membership,
    staff_membership,
    business_unit,
    establishment,
):
    template = _active_template_with_task(owner_membership, business_unit)
    start_at, end_at = stable_assignment_times(duration_hours=2)
    today = timezone.now().date()
    real_create = ChecklistAssignment.objects.create
    existing_execution_holder: list[ChecklistExecution] = []

    def create_assignment_with_existing_execution(**kwargs):
        assignment = real_create(**kwargs)
        execution = ChecklistExecution.objects.create(
            checklist_template=template,
            checklist_assignment=assignment,
            establishment_id=establishment.id,
            assigned_to=staff_membership,
            assigned_by=owner_membership,
            business_unit=template.business_unit,
            template_title=template.title,
            start_at=timezone.now(),
            visible_from=timezone.now(),
            end_at=timezone.now() + timezone.timedelta(hours=2),
            occurrence_date=today,
            status=ChecklistExecution.Status.ASSIGNED,
            execution_source=EXECUTION_SOURCE_ASSIGNMENT,
            last_activity_at=timezone.now(),
        )
        existing_execution_holder.append(execution)
        return assignment

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with patch(
            "houston.checklists.services.ChecklistAssignment.objects.create",
            side_effect=create_assignment_with_existing_execution,
        ):
            with patch(
                "houston.checklists.services.materialize_execution_from_assignment",
                side_effect=lambda **kwargs: existing_execution_holder[0],
            ):
                create_checklist_assignment(
                    template=template,
                    actor=owner_membership,
                    assigned_to_id=staff_membership.id,
                    start_date=today,
                    end_date=today,
                    start_at=start_at,
                    end_at=end_at,
                )

        mock_notify.assert_called_once()
        _assert_checklist_invalidation(mock_notify, template=template)


def test_create_registered_checklist_template_emits_single_checklist_without_assign_now(
    owner_membership,
    business_unit,
):
    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        template, execution = create_registered_checklist_template(
            establishment_id=owner_membership.establishment_id,
            actor=owner_membership,
            title="Registered",
            business_unit_id=business_unit.id,
            tasks=[{"title": "Step 1"}],
            assign_now=False,
        )

        assert execution is None
        assert mock_notify.call_count == 1
        _assert_checklist_invalidation(mock_notify, template=template)


def test_create_registered_checklist_template_emits_checklist_and_execution_with_assign_now(
    owner_membership,
    business_unit,
    staff_membership,
):
    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        template, execution = create_registered_checklist_template(
            establishment_id=owner_membership.establishment_id,
            actor=owner_membership,
            title="Registered assign",
            business_unit_id=business_unit.id,
            tasks=[{"title": "Step 1"}],
            assign_now=True,
            assigned_to_id=staff_membership.id,
        )

        assert execution is not None
        assert mock_notify.call_count == 2
        _assert_execution_invalidation(
            mock_notify,
            execution=execution,
            reason="execution.created",
            call_index=0,
        )
        _assert_checklist_invalidation(mock_notify, template=template, call_index=1)


def test_mark_task_done_emits_execution_updated(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_template_with_task(owner_membership, business_unit)
    start_at, end_at = stable_assignment_times(duration_hours=2)
    today = timezone.now().date()
    create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=today,
        end_date=today,
        start_at=start_at,
        end_at=end_at,
    )
    execution = ChecklistExecution.objects.get(checklist_template=template)
    task = execution.task_executions.order_by("position").first()

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        mark_task_done(task_execution=task, actor=staff_membership)

        mock_notify.assert_called_once()
        _assert_execution_invalidation(
            mock_notify,
            execution=execution,
            reason="execution.updated",
        )


def test_create_observation_from_task_emits_single_execution_updated(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_template_with_task(owner_membership, business_unit)
    start_at, end_at = stable_assignment_times(duration_hours=2)
    today = timezone.now().date()
    create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=today,
        end_date=today,
        start_at=start_at,
        end_at=end_at,
    )
    execution = ChecklistExecution.objects.get(checklist_template=template)
    task = execution.task_executions.order_by("position").first()

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with patch("houston.checklists.services.submit_observation") as submit_mock:
            observation = Observation.objects.create(
                establishment_id=execution.establishment_id,
                submitted_by_membership=staff_membership,
                raw_text="Sensitive observation body text",
                submitted_at=timezone.now(),
            )
            submit_mock.return_value = observation
            create_observation_from_task(
                task_execution=task,
                actor=staff_membership,
                text="Sensitive observation body text",
            )

        mock_notify.assert_called_once()
        _assert_execution_invalidation(
            mock_notify,
            execution=execution,
            reason="execution.updated",
        )


def test_checklist_invalidation_not_emitted_on_permission_error(
    owner_membership,
    staff_membership,
    business_unit,
    other_staff_membership,
):
    template = _active_template_with_task(owner_membership, business_unit)

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(ChecklistPermissionError):
            create_execution_from_template(
                template=template,
                actor=staff_membership,
                assigned_to_id=other_staff_membership.id,
            )

        mock_notify.assert_not_called()


def test_checklist_invalidation_not_emitted_on_transaction_rollback(
    owner_membership,
    business_unit,
):
    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                create_checklist_template(
                    establishment_id=owner_membership.establishment_id,
                    actor=owner_membership,
                    title="Rollback",
                    business_unit_id=business_unit.id,
                )
                raise RuntimeError("force rollback")

        mock_notify.assert_not_called()


@pytest.mark.parametrize(
    ("subject_type", "reason"),
    [
        ("checklist", "checklist.updated"),
        ("execution", "execution.created"),
        ("execution", "execution.updated"),
    ],
)
def test_checklist_invalidate_payload_allowlist(subject_type: str, reason: str):
    from houston.realtime.ws_payloads import build_invalidate_payload

    establishment_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    payload = build_invalidate_payload(
        subject_type=subject_type,
        reason=reason,
        establishment_id=establishment_id,
        entity_id=entity_id,
    )

    assert set(payload.keys()) == ALLOWED_PAYLOAD_KEYS
    assert payload["type"] == "invalidate"
    assert payload["subject_type"] == subject_type
    assert payload["reason"] == reason
    assert FORBIDDEN_PAYLOAD_KEYS.isdisjoint(payload.keys())

    payload_blob = " ".join(str(value) for value in payload.values()).lower()
    assert "sensitive" not in payload_blob
    assert "description" not in payload_blob
    assert "task" not in payload_blob
