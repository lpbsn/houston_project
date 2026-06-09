from __future__ import annotations

import pytest
from django.utils import timezone

from houston.checklists.materialization import (
    MATERIALIZATION_HORIZON_DAYS,
    materialize_assignments_horizon,
)
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.services import create_checklist_assignment, create_checklist_template
from houston.checklists.tasks import materialize_checklist_assignments_horizon_task
from houston.checklists.tests.conftest import add_task_template, assignment_schedule_from_datetime

pytestmark = pytest.mark.django_db


def _active_registered_template(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        title="Routine",
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    return template


def test_horizon_task_materializes_recurring_occurrences(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
    start_at = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        recurrence_days=["monday", "wednesday", "friday"],
        **assignment_schedule_from_datetime(start_at, duration_hours=1, period_days=14),
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()

    created = materialize_checklist_assignments_horizon_task.run()
    assert created > 0
    assert ChecklistExecution.objects.filter(checklist_assignment=assignment).count() == created


def test_horizon_task_is_idempotent(owner_membership, staff_membership, business_unit):
    template = _active_registered_template(owner_membership, business_unit)
    start_at = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        recurrence_days=["monday", "wednesday", "friday"],
        **assignment_schedule_from_datetime(start_at, duration_hours=1, period_days=14),
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()

    materialize_checklist_assignments_horizon_task.run()
    count_after_first = ChecklistExecution.objects.filter(
        checklist_assignment=assignment,
    ).count()
    materialize_checklist_assignments_horizon_task.run()
    count_after_second = ChecklistExecution.objects.filter(
        checklist_assignment=assignment,
    ).count()

    assert count_after_first > 0
    assert count_after_second == count_after_first


def test_horizon_does_not_materialize_after_end_date(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
    start_at = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        recurrence_days=["monday", "wednesday", "friday"],
        start_date=start_at.date(),
        end_date=start_at.date() + timezone.timedelta(days=2),
        start_at=start_at.time().replace(microsecond=0),
        end_at=(start_at + timezone.timedelta(hours=1)).time().replace(microsecond=0),
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()

    materialize_assignments_horizon(
        establishment_id=owner_membership.establishment_id,
        horizon_days=MATERIALIZATION_HORIZON_DAYS,
    )

    occurrence_dates = list(
        ChecklistExecution.objects.filter(checklist_assignment=assignment).values_list(
            "occurrence_date",
            flat=True,
        )
    )
    assert occurrence_dates
    assert all(occurrence_date <= assignment.end_date for occurrence_date in occurrence_dates)
    assert all(occurrence_date >= assignment.start_date for occurrence_date in occurrence_dates)
