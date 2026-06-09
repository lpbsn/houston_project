from __future__ import annotations

from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.actions.models import Action
from houston.checklists.exceptions import ChecklistValidationError
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.services import (
    create_checklist_assignment,
    create_checklist_template,
    create_observation_from_task,
    mark_task_done,
    skip_task,
)
from houston.checklists.tests.conftest import add_task_template
from houston.observations.models import Observation
from houston.signals.models import Signal

pytestmark = pytest.mark.django_db


def _shared_execution_with_tasks(owner_membership, staff_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
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

        start_at=now.time().replace(microsecond=0),

        end_at=(now + timezone.timedelta(hours=2)).time().replace(microsecond=0),
    )
    return ChecklistExecution.objects.prefetch_related("task_executions").get(
        checklist_assignment=assignment,
    )


@patch("houston.observations.services._enqueue_observation_processing")
def test_observation_handoff_happy_path(
    mock_enqueue,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _shared_execution_with_tasks(
        owner_membership,
        staff_membership,
        business_unit,
    )
    task = execution.task_executions.order_by("position").first()
    action_count_before = Action.objects.count()
    signal_count_before = Signal.objects.count()

    updated = create_observation_from_task(
        task_execution=task,
        actor=staff_membership,
        text="Broken equipment in kitchen area today",
    )

    observation = Observation.objects.get(id=updated.observation_id)
    assert observation.origin == Observation.Origin.CHECKLIST_TASK
    assert observation.checklist_execution_id == execution.id
    assert observation.checklist_task_execution_id == task.id
    assert updated.status == "observation_created"
    assert Action.objects.count() == action_count_before
    assert Signal.objects.count() == signal_count_before
    mock_enqueue.assert_not_called()


@patch("houston.observations.services._enqueue_observation_processing")
def test_observation_handoff_rejects_short_text(
    mock_enqueue,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _shared_execution_with_tasks(
        owner_membership,
        staff_membership,
        business_unit,
    )
    task = execution.task_executions.order_by("position").first()
    with pytest.raises(ChecklistValidationError, match="too short"):
        create_observation_from_task(
            task_execution=task,
            actor=staff_membership,
            text="short",
        )
    mock_enqueue.assert_not_called()
    assert Observation.objects.count() == 0


@patch("houston.observations.services._enqueue_observation_processing")
def test_observation_handoff_completes_execution_when_all_tasks_treated(
    mock_enqueue,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _shared_execution_with_tasks(
        owner_membership,
        staff_membership,
        business_unit,
    )
    tasks = list(execution.task_executions.order_by("position"))
    create_observation_from_task(
        task_execution=tasks[0],
        actor=staff_membership,
        text="Broken equipment in kitchen area today",
    )
    skip_task(task_execution=tasks[1], actor=staff_membership)

    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.DONE


@patch("houston.observations.services._enqueue_observation_processing")
def test_observation_handoff_does_not_create_signal_or_action_sync(
    mock_enqueue,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _shared_execution_with_tasks(
        owner_membership,
        staff_membership,
        business_unit,
    )
    task = execution.task_executions.order_by("position").first()
    create_observation_from_task(
        task_execution=task,
        actor=staff_membership,
        text="Broken equipment in kitchen area today",
    )
    mark_task_done(
        task_execution=execution.task_executions.exclude(id=task.id).first(),
        actor=staff_membership,
    )
    assert Signal.objects.count() == 0
    assert Action.objects.count() == 0
