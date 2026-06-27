from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import close_old_connections
from django.utils import timezone

from houston.checklists.exceptions import ChecklistValidationError
from houston.checklists.materialization import (
    READ_PATH_MATERIALIZATION_HORIZON_DAYS,
    ensure_visible_executions_materialized,
    materialize_assignment_occurrences_in_horizon,
    materialize_execution_from_assignment,
)
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.services import (
    create_checklist_assignment,
    create_checklist_template,
    create_execution_from_template,
)
from houston.checklists.tests.conftest import (
    add_task_template,
    assignment_schedule_from_datetime,
    stable_assignment_times,
)
from houston.establishments.tests.taxonomy_helpers import create_establishment

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


def test_ensure_visible_skips_recently_materialized_assignments(
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
        **assignment_schedule_from_datetime(start_at, duration_hours=1),
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    materialize_assignment_occurrences_in_horizon(
        assignment=assignment,
        horizon_days=READ_PATH_MATERIALIZATION_HORIZON_DAYS,
        now=start_at,
    )

    created = ensure_visible_executions_materialized(
        membership=staff_membership,
        view_mode="personal",
    )

    assert created == 0


def test_partial_stale_assignment_queries_existing_dates_once(
    owner_membership,
    staff_membership,
    business_unit,
    monkeypatch,
):
    from houston.checklists import materialization as materialization_module

    now = timezone.now()
    template = _active_registered_template(owner_membership, business_unit)
    start_at, end_at = stable_assignment_times(duration_hours=2)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=start_at,
        end_at=end_at,
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    materialize_assignment_occurrences_in_horizon(
        assignment=assignment,
        horizon_days=READ_PATH_MATERIALIZATION_HORIZON_DAYS,
        now=now,
    )

    assignment.last_materialized_at = now
    assignment.save(update_fields=["last_materialized_at", "updated_at"])
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()

    call_count = {"n": 0}
    original = materialization_module._existing_occurrence_dates_for_assignment

    def counting_wrapper(**kwargs):
        call_count["n"] += 1
        return original(**kwargs)

    monkeypatch.setattr(
        materialization_module,
        "_existing_occurrence_dates_for_assignment",
        counting_wrapper,
    )

    created = ensure_visible_executions_materialized(
        membership=staff_membership,
        view_mode="personal",
    )

    assert created == 1
    assert call_count["n"] == 1


def test_materialize_requires_occurrence_date(owner_membership, staff_membership, business_unit):
    template = _active_registered_template(owner_membership, business_unit)
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
    with pytest.raises(ChecklistValidationError):
        materialize_execution_from_assignment(
            assignment=assignment,
            occurrence_date=None,
        )


@pytest.mark.django_db(transaction=True)
def test_concurrent_materialize_same_assignment_occurrence_is_idempotent(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
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
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    occurrence_date = now.date()

    def materialize(_: int) -> str:
        close_old_connections()
        try:
            execution = materialize_execution_from_assignment(
                assignment=assignment,
                occurrence_date=occurrence_date,
            )
            return str(execution.id)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(materialize, range(2)))

    assert results[0] == results[1]
    executions = ChecklistExecution.objects.filter(
        checklist_assignment=assignment,
        occurrence_date=occurrence_date,
    )
    assert executions.count() == 1
    execution = executions.get()
    assert execution.task_executions.count() == 1


def test_materialize_is_idempotent(owner_membership, staff_membership, business_unit):
    template = _active_registered_template(owner_membership, business_unit)
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
    first = ChecklistExecution.objects.get(checklist_assignment=assignment)
    second = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=now.date(),
    )
    assert second.id == first.id
    assert ChecklistExecution.objects.filter(checklist_assignment=assignment).count() == 1


def test_materialize_sets_visible_from_one_hour_before_start(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_registered_template(owner_membership, business_unit)
    start_at = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        **assignment_schedule_from_datetime(start_at, duration_hours=2),
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    assert execution.visible_from == start_at - timezone.timedelta(hours=1)


def test_recurring_materialization_within_horizon(
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
        **assignment_schedule_from_datetime(start_at, duration_hours=1),
    )

    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    materialized = materialize_assignment_occurrences_in_horizon(
        assignment=assignment,
        horizon_days=14,
        now=start_at,
    )
    occurrence_dates = sorted(execution.occurrence_date for execution in materialized)
    assert occurrence_dates
    assert all(execution.occurrence_date is not None for execution in materialized)
    assert len({execution.occurrence_date for execution in materialized}) == len(materialized)


def test_staff_template_execution_has_no_assignment_or_occurrence_date(
    staff_membership,
    staff_owned_template,
):
    add_task_template(template=staff_owned_template, task="Task")
    execution = create_execution_from_template(
        template=staff_owned_template,
        actor=staff_membership,
    )
    assert execution.checklist_assignment_id is None
    assert execution.occurrence_date is None
    assert execution.visible_from is None
    assert execution.start_at is None
    assert execution.end_at is None
    assert execution.task_executions.count() == 1


def test_multiple_active_template_executions_allowed(staff_membership, staff_owned_template):
    add_task_template(template=staff_owned_template, task="Task")
    first = create_execution_from_template(template=staff_owned_template, actor=staff_membership)
    second = create_execution_from_template(template=staff_owned_template, actor=staff_membership)
    assert first.id != second.id


def test_staff_template_execution_allowed_after_terminal(staff_membership, staff_owned_template):
    add_task_template(template=staff_owned_template, task="Task")
    first = create_execution_from_template(template=staff_owned_template, actor=staff_membership)
    first.status = ChecklistExecution.Status.DONE
    first.save(update_fields=["status", "updated_at"])
    second = create_execution_from_template(template=staff_owned_template, actor=staff_membership)
    assert second.id != first.id


def test_materialize_rejects_cross_establishment_assignment_template(
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.checklists.models import ChecklistAssignment

    template = _active_registered_template(owner_membership, business_unit)
    now = timezone.now()
    assignment = ChecklistAssignment.objects.create(
        checklist_template=template,
        establishment_id=template.establishment_id,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit_id=template.business_unit_id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=stable_assignment_times(duration_hours=1)[0],
        end_at=stable_assignment_times(duration_hours=1)[1],
    )
    other_establishment = create_establishment(name="Other")
    assignment.establishment_id = other_establishment.id
    assignment.save(update_fields=["establishment_id", "updated_at"])
    with pytest.raises(ChecklistValidationError):
        materialize_execution_from_assignment(
            assignment=assignment,
            occurrence_date=now.date(),
        )


def test_orphan_assignment_does_not_materialize(
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.checklists.models import ChecklistAssignment

    template = _active_registered_template(owner_membership, business_unit)
    now = timezone.now()
    assignment = ChecklistAssignment.objects.create(
        checklist_template=template,
        establishment_id=template.establishment_id,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit_id=template.business_unit_id,
        start_date=now.date(),
        end_date=now.date(),
        start_at=stable_assignment_times(duration_hours=1)[0],
        end_at=stable_assignment_times(duration_hours=1)[1],
        status=ChecklistAssignment.Status.ACTIVE,
    )
    assignment.checklist_template_id = None
    assignment.save(update_fields=["checklist_template_id", "updated_at"])

    with pytest.raises(ChecklistValidationError, match="no checklist template"):
        materialize_execution_from_assignment(
            assignment=assignment,
            occurrence_date=now.date(),
        )

    materialized = materialize_assignment_occurrences_in_horizon(
        assignment=assignment,
        horizon_days=14,
        now=now,
    )
    assert materialized == []
    assert ChecklistExecution.objects.filter(checklist_assignment=assignment).count() == 0
