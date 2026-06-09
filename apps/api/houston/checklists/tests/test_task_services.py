from __future__ import annotations

import pytest
from django.utils import timezone

from houston.checklists.exceptions import ChecklistPermissionError
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.services import (
    cancel_checklist_execution,
    create_checklist_assignment,
    create_checklist_template,
    create_execution_from_template,
    create_observation_from_task,
    mark_task_done,
    record_task_observation_created,
    skip_task,
)
from houston.checklists.tests.conftest import add_task_template, stable_assignment_times
from houston.observations.models import Observation

pytestmark = pytest.mark.django_db


def _execution_with_tasks(owner_membership, staff_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        title="Routine",
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, task="Task 1", position=1)
    add_task_template(template=template, task="Task 2", position=2)
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    now = timezone.now()
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=stable_assignment_times(duration_hours=2)[0],
        end_at=stable_assignment_times(duration_hours=2)[1],
    )
    return ChecklistExecution.objects.prefetch_related("task_executions").get(
        checklist_assignment=assignment,
    )


def test_mark_done_starts_execution_and_updates_activity(
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    task = execution.task_executions.order_by("position").first()
    assert execution.status == ChecklistExecution.Status.ASSIGNED

    mark_task_done(task_execution=task, actor=staff_membership)
    execution.refresh_from_db()
    task.refresh_from_db()

    assert task.status == "done"
    assert execution.status == ChecklistExecution.Status.IN_PROGRESS
    assert execution.started_at is not None
    assert execution.last_activity_at is not None


def test_execution_done_when_all_tasks_treated(
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    tasks = list(execution.task_executions.order_by("position"))
    mark_task_done(task_execution=tasks[0], actor=staff_membership)
    mark_task_done(task_execution=tasks[1], actor=staff_membership)

    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.DONE
    assert execution.done_at is not None


def test_skip_task_with_optional_reason(
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    task = execution.task_executions.order_by("position").first()
    skip_task(task_execution=task, actor=staff_membership, skipped_reason="  Not needed  ")
    task.refresh_from_db()
    assert task.status == "skipped"
    assert task.skipped_reason == "Not needed"


def test_staff_cannot_execute_unassigned_assignment_task(
    owner_membership,
    staff_membership,
    other_staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    task = execution.task_executions.order_by("position").first()
    with pytest.raises(ChecklistPermissionError):
        mark_task_done(task_execution=task, actor=other_staff_membership)


def test_record_task_observation_created_completes_execution(
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    tasks = list(execution.task_executions.order_by("position"))
    now = timezone.now()
    observation = Observation.objects.create(
        establishment_id=execution.establishment_id,
        submitted_by_membership=staff_membership,
        raw_text="Broken equipment in kitchen area today",
        submitted_at=now,
    )
    record_task_observation_created(
        task_execution=tasks[0],
        actor=staff_membership,
        observation=observation,
    )
    skip_task(task_execution=tasks[1], actor=staff_membership)

    execution.refresh_from_db()
    tasks[0].refresh_from_db()
    assert tasks[0].status == "observation_created"
    assert tasks[0].observation_id == observation.id
    assert execution.status == ChecklistExecution.Status.DONE


def test_create_observation_from_task_delegates_to_submit_observation(
    owner_membership,
    staff_membership,
    business_unit,
):
    from unittest.mock import patch

    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    task = execution.task_executions.order_by("position").first()
    with patch("houston.checklists.services.submit_observation") as submit_mock:
        submit_mock.return_value = object()
        with patch("houston.checklists.services.record_task_observation_created") as record_mock:
            record_mock.return_value = task
            create_observation_from_task(
                task_execution=task,
                actor=staff_membership,
                text="Broken equipment in kitchen area today",
            )
    submit_mock.assert_called_once()


def test_cancel_assignment_execution_by_owner(
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    canceled = cancel_checklist_execution(execution=execution, actor=owner_membership)
    assert canceled.status == ChecklistExecution.Status.CANCELED
    assert canceled.canceled_at is not None


def test_staff_assignee_can_cancel_assignment_execution(
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_tasks(owner_membership, staff_membership, business_unit)
    canceled = cancel_checklist_execution(execution=execution, actor=staff_membership)
    assert canceled.status == ChecklistExecution.Status.CANCELED


def test_cancel_staff_template_execution_by_assignee(staff_membership, staff_owned_template):
    add_task_template(template=staff_owned_template, task="Task")
    execution = create_execution_from_template(
        template=staff_owned_template,
        actor=staff_membership,
    )
    canceled = cancel_checklist_execution(execution=execution, actor=staff_membership)
    assert canceled.status == ChecklistExecution.Status.CANCELED
