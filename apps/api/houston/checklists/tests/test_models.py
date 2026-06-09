from __future__ import annotations

from datetime import time

import pytest
from django.db import IntegrityError
from django.utils import timezone

from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTaskTemplate,
    ChecklistTemplate,
)
from houston.checklists.tests.conftest import add_task_template

pytestmark = pytest.mark.django_db


def test_shared_template_requires_business_unit(owner_membership, business_unit):
    establishment = owner_membership.establishment
    template = ChecklistTemplate.objects.create(
        establishment=establishment,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        created_by=owner_membership,
        business_unit=business_unit,
        title="Shared checklist",
    )
    assert template.business_unit_id == business_unit.id


def test_personal_template_rejects_business_unit(staff_membership, business_unit):
    establishment = staff_membership.establishment
    with pytest.raises(IntegrityError):
        ChecklistTemplate.objects.create(
            establishment=establishment,
            checklist_type=ChecklistTemplate.ChecklistType.PERSONAL,
            created_by=staff_membership,
            business_unit=business_unit,
            title="Invalid personal",
        )


def test_shared_template_rejects_missing_business_unit(owner_membership):
    establishment = owner_membership.establishment
    with pytest.raises(IntegrityError):
        ChecklistTemplate.objects.create(
            establishment=establishment,
            checklist_type=ChecklistTemplate.ChecklistType.SHARED,
            created_by=owner_membership,
            business_unit=None,
            title="Invalid shared",
        )


def test_assignment_rejects_end_at_before_start_at(
    establishment,
    shared_template,
    owner_membership,
    staff_membership,
):
    today = timezone.now().date()
    with pytest.raises(IntegrityError):
        ChecklistAssignment.objects.create(
            checklist_template=shared_template,
            establishment=establishment,
            assigned_to=staff_membership,
            assigned_by=owner_membership,
            business_unit=shared_template.business_unit,
            start_date=today,
            end_date=today,
            start_at=time(10, 0),
            end_at=time(9, 0),
        )


def test_task_template_unique_position_per_template(shared_template):
    add_task_template(template=shared_template, task="First", position=1)
    with pytest.raises(IntegrityError):
        add_task_template(template=shared_template, task="Duplicate", position=1)


def test_personal_execution_rejects_end_at(personal_template, staff_membership):
    now = timezone.now()
    with pytest.raises(IntegrityError):
        ChecklistExecution.objects.create(
            checklist_template=personal_template,
            checklist_type=ChecklistExecution.ChecklistType.PERSONAL,
            establishment=personal_template.establishment,
            assigned_to=staff_membership,
            template_title=personal_template.title,
            end_at=now,
            last_activity_at=now,
        )


def test_shared_execution_requires_assignment_and_business_unit(
    establishment,
    shared_template,
    staff_membership,
    owner_membership,
):
    now = timezone.now()
    with pytest.raises(IntegrityError):
        ChecklistExecution.objects.create(
            checklist_template=shared_template,
            checklist_assignment=None,
            checklist_type=ChecklistExecution.ChecklistType.SHARED,
            establishment=establishment,
            assigned_to=staff_membership,
            assigned_by=owner_membership,
            business_unit=shared_template.business_unit,
            template_title=shared_template.title,
            last_activity_at=now,
        )


def test_only_one_active_personal_execution_per_template(
    establishment,
    personal_template,
    staff_membership,
):
    now = timezone.now()
    ChecklistExecution.objects.create(
        checklist_template=personal_template,
        checklist_type=ChecklistExecution.ChecklistType.PERSONAL,
        establishment=establishment,
        assigned_to=staff_membership,
        template_title=personal_template.title,
        status=ChecklistExecution.Status.ASSIGNED,
        last_activity_at=now,
    )
    with pytest.raises(IntegrityError):
        ChecklistExecution.objects.create(
            checklist_template=personal_template,
            checklist_type=ChecklistExecution.ChecklistType.PERSONAL,
            establishment=establishment,
            assigned_to=staff_membership,
            template_title=personal_template.title,
            status=ChecklistExecution.Status.IN_PROGRESS,
            last_activity_at=now,
        )


def test_new_personal_execution_allowed_after_terminal(
    establishment,
    personal_template,
    staff_membership,
):
    now = timezone.now()
    ChecklistExecution.objects.create(
        checklist_template=personal_template,
        checklist_type=ChecklistExecution.ChecklistType.PERSONAL,
        establishment=establishment,
        assigned_to=staff_membership,
        template_title=personal_template.title,
        status=ChecklistExecution.Status.DONE,
        last_activity_at=now,
    )
    second = ChecklistExecution.objects.create(
        checklist_template=personal_template,
        checklist_type=ChecklistExecution.ChecklistType.PERSONAL,
        establishment=establishment,
        assigned_to=staff_membership,
        template_title=personal_template.title,
        status=ChecklistExecution.Status.ASSIGNED,
        last_activity_at=now,
    )
    assert second.status == ChecklistExecution.Status.ASSIGNED


def test_assignment_occurrence_idempotence_key(
    establishment,
    shared_template,
    owner_membership,
    staff_membership,
):
    now = timezone.now()
    assignment = ChecklistAssignment.objects.create(
        checklist_template=shared_template,
        establishment=establishment,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit=shared_template.business_unit,
        start_date=now.date(),

        end_date=now.date(),

        start_at=now.time().replace(microsecond=0),

        end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
    )
    occurrence = now.date()
    ChecklistExecution.objects.create(
        checklist_template=shared_template,
        checklist_assignment=assignment,
        checklist_type=ChecklistExecution.ChecklistType.SHARED,
        establishment=establishment,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit=shared_template.business_unit,
        template_title=shared_template.title,
        occurrence_date=occurrence,
        last_activity_at=now,
    )
    with pytest.raises(IntegrityError):
        ChecklistExecution.objects.create(
            checklist_template=shared_template,
            checklist_assignment=assignment,
            checklist_type=ChecklistExecution.ChecklistType.SHARED,
            establishment=establishment,
            assigned_to=staff_membership,
            assigned_by=owner_membership,
            business_unit=shared_template.business_unit,
            template_title=shared_template.title,
            occurrence_date=occurrence,
            last_activity_at=now,
        )


def test_task_execution_snapshot_fields(shared_execution):
    task = ChecklistTaskTemplate.objects.create(
        checklist_template=shared_execution.checklist_template,
        task="Inspect fridge",
        position=1,
    )
    task_execution = shared_execution.task_executions.create(
        checklist_task_template=task,
        task=task.task,
        position=task.position,
    )
    assert task_execution.task == "Inspect fridge"
    assert task_execution.position == 1


def test_template_defaults_to_inactive(owner_membership, business_unit):
    template = ChecklistTemplate.objects.create(
        establishment=owner_membership.establishment,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        created_by=owner_membership,
        business_unit=business_unit,
        title="Draft checklist",
    )
    assert template.status == ChecklistTemplate.Status.INACTIVE
