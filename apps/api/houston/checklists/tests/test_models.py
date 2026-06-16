from __future__ import annotations

from datetime import time

import pytest
from django.db import IntegrityError
from django.utils import timezone

from houston.checklists.constants import (
    EXECUTION_SOURCE_ASSIGNMENT,
    EXECUTION_SOURCE_TEMPLATE,
)
from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTaskTemplate,
    ChecklistTemplate,
)
from houston.checklists.tests.conftest import add_task_template, stable_assignment_times

pytestmark = pytest.mark.django_db


def test_template_requires_business_unit(owner_membership, business_unit):
    establishment = owner_membership.establishment
    template = ChecklistTemplate.objects.create(
        establishment=establishment,
        created_by=owner_membership,
        business_unit=business_unit,
        title="Registered checklist",
    )
    assert template.business_unit_id == business_unit.id


def test_template_rejects_missing_business_unit(owner_membership):
    establishment = owner_membership.establishment
    with pytest.raises(IntegrityError):
        ChecklistTemplate.objects.create(
            establishment=establishment,
            created_by=owner_membership,
            business_unit=None,
            title="Invalid template",
        )


def test_assignment_rejects_end_at_before_start_at(
    establishment,
    registered_template,
    owner_membership,
    staff_membership,
):
    today = timezone.now().date()
    with pytest.raises(IntegrityError):
        ChecklistAssignment.objects.create(
            checklist_template=registered_template,
            establishment=establishment,
            assigned_to=staff_membership,
            assigned_by=owner_membership,
            business_unit=registered_template.business_unit,
            start_date=today,
            end_date=today,
            start_at=time(10, 0),
            end_at=time(9, 0),
        )


def test_task_template_unique_position_per_template(registered_template):
    add_task_template(template=registered_template, task="First", position=1)
    with pytest.raises(IntegrityError):
        add_task_template(template=registered_template, task="Duplicate", position=1)


def test_assignment_execution_requires_assignment(
    establishment,
    registered_template,
    staff_membership,
    owner_membership,
):
    now = timezone.now()
    with pytest.raises(IntegrityError):
        ChecklistExecution.objects.create(
            checklist_template=registered_template,
            checklist_assignment=None,
            execution_source=EXECUTION_SOURCE_ASSIGNMENT,
            establishment=establishment,
            assigned_to=staff_membership,
            assigned_by=owner_membership,
            business_unit=registered_template.business_unit,
            template_title=registered_template.title,
            last_activity_at=now,
        )


def test_template_execution_requires_template_without_assignment(
    establishment,
    registered_template,
    staff_membership,
    owner_membership,
):
    now = timezone.now()
    with pytest.raises(IntegrityError):
        ChecklistExecution.objects.create(
            checklist_template=None,
            checklist_assignment=None,
            execution_source=EXECUTION_SOURCE_TEMPLATE,
            establishment=establishment,
            assigned_to=staff_membership,
            assigned_by=owner_membership,
            business_unit=registered_template.business_unit,
            template_title=registered_template.title,
            last_activity_at=now,
        )


def test_multiple_active_template_executions_allowed(
    establishment,
    registered_template,
    staff_membership,
):
    now = timezone.now()
    ChecklistExecution.objects.create(
        checklist_template=registered_template,
        execution_source=EXECUTION_SOURCE_TEMPLATE,
        establishment=establishment,
        assigned_to=staff_membership,
        business_unit=registered_template.business_unit,
        template_title=registered_template.title,
        status=ChecklistExecution.Status.ASSIGNED,
        last_activity_at=now,
    )
    second = ChecklistExecution.objects.create(
        checklist_template=registered_template,
        execution_source=EXECUTION_SOURCE_TEMPLATE,
        establishment=establishment,
        assigned_to=staff_membership,
        business_unit=registered_template.business_unit,
        template_title=registered_template.title,
        status=ChecklistExecution.Status.IN_PROGRESS,
        last_activity_at=now,
    )
    assert second.status == ChecklistExecution.Status.IN_PROGRESS


def test_assignment_occurrence_idempotence_key(
    establishment,
    registered_template,
    owner_membership,
    staff_membership,
):
    now = timezone.now()
    assignment = ChecklistAssignment.objects.create(
        checklist_template=registered_template,
        establishment=establishment,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit=registered_template.business_unit,
        start_date=now.date(),
        end_date=now.date(),
        start_at=stable_assignment_times(duration_hours=1)[0],
        end_at=stable_assignment_times(duration_hours=1)[1],
    )
    occurrence = now.date()
    ChecklistExecution.objects.create(
        checklist_template=registered_template,
        checklist_assignment=assignment,
        execution_source=EXECUTION_SOURCE_ASSIGNMENT,
        establishment=establishment,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit=registered_template.business_unit,
        template_title=registered_template.title,
        occurrence_date=occurrence,
        last_activity_at=now,
    )
    with pytest.raises(IntegrityError):
        ChecklistExecution.objects.create(
            checklist_template=registered_template,
            checklist_assignment=assignment,
            execution_source=EXECUTION_SOURCE_ASSIGNMENT,
            establishment=establishment,
            assigned_to=staff_membership,
            assigned_by=owner_membership,
            business_unit=registered_template.business_unit,
            template_title=registered_template.title,
            occurrence_date=occurrence,
            last_activity_at=now,
        )


def test_task_execution_snapshot_fields(assignment_execution):
    task = ChecklistTaskTemplate.objects.create(
        checklist_template=assignment_execution.checklist_template,
        task="Inspect fridge",
        position=1,
    )
    task_execution = assignment_execution.task_executions.create(
        checklist_task_template=task,
        task=task.task,
        position=task.position,
    )
    assert task_execution.task == "Inspect fridge"
    assert task_execution.position == 1


def test_template_defaults_to_inactive(owner_membership, business_unit):
    template = ChecklistTemplate.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        business_unit=business_unit,
        title="Draft checklist",
    )
    assert template.status == ChecklistTemplate.Status.INACTIVE


def test_assignment_execution_stores_execution_source(
    establishment,
    registered_template,
    checklist_assignment,
    staff_membership,
    owner_membership,
):
    now = timezone.now()
    execution = ChecklistExecution.objects.create(
        checklist_template=registered_template,
        checklist_assignment=checklist_assignment,
        execution_source=EXECUTION_SOURCE_ASSIGNMENT,
        establishment=establishment,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit=registered_template.business_unit,
        template_title=registered_template.title,
        last_activity_at=now,
    )
    assert execution.execution_source == EXECUTION_SOURCE_ASSIGNMENT
