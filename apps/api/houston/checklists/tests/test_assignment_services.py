from __future__ import annotations

from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from houston.checklists.constants import EXECUTION_STATUS_ASSIGNED, EXECUTION_STATUS_CANCELED
from houston.checklists.exceptions import (
    ChecklistConflictError,
    ChecklistPermissionError,
    ChecklistValidationError,
)
from houston.checklists.materialization import materialize_execution_from_assignment
from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTaskExecution,
    ChecklistTemplate,
)
from houston.checklists.services import (
    _ASSIGNEE_OUT_OF_SCOPE_MESSAGE,
    _ASSIGNMENT_INACTIVE_PATCH_MESSAGE,
    _REMOVE_ASSIGNMENT_IN_PROGRESS_MESSAGE,
    _execution_still_matches_assignment_schedule,
    create_checklist_assignment,
    create_checklist_template,
    deactivate_checklist_assignment,
    mark_task_done,
    normalize_recurrence_days,
    update_checklist_assignment,
)
from houston.checklists.tests.conftest import add_task_template, assignment_schedule_from_datetime
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_membership,
)

pytestmark = pytest.mark.django_db


def _active_shared_template(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Opening",
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    return template


def _next_weekday_datetime(weekday: int, *, hour: int = 8) -> datetime:
    now = timezone.now()
    days_ahead = (weekday - now.weekday()) % 7
    target_date = (now + timedelta(days=days_ahead)).date()
    return datetime.combine(
        target_date,
        datetime.min.time().replace(hour=hour),
        tzinfo=now.tzinfo,
    )


def _create_assignment(
    owner_membership,
    staff_membership,
    business_unit,
    *,
    task_count: int = 1,
    **kwargs,
):
    template = _active_shared_template(owner_membership, business_unit)
    for position in range(2, task_count + 1):
        add_task_template(template=template, task=f"Task {position}", position=position)
    legacy_start = kwargs.pop("start_at", None)
    legacy_end = kwargs.pop("end_at", None)
    if legacy_start is not None and isinstance(legacy_start, datetime):
        duration_hours = 1
        if isinstance(legacy_end, datetime):
            duration_hours = max(1, int((legacy_end - legacy_start).total_seconds() // 3600))
        schedule = assignment_schedule_from_datetime(legacy_start, duration_hours=duration_hours)
        start_date = kwargs.pop("start_date", schedule["start_date"])
        end_date = kwargs.pop("end_date", schedule["end_date"])
        start_at = kwargs.pop("start_at", schedule["start_at"])
        end_at = kwargs.pop("end_at", schedule["end_at"])
    else:
        default_date = timezone.now().date()
        start_date = kwargs.pop("start_date", default_date)
        end_date = kwargs.pop("end_date", start_date + timedelta(days=14))
        start_at = legacy_start if isinstance(legacy_start, time) else time(8, 0)
        end_at = legacy_end if isinstance(legacy_end, time) else time(10, 0)
    return create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=start_date,
        end_date=end_date,
        start_at=start_at,
        end_at=end_at,
        **kwargs,
    )


def test_normalize_recurrence_days_one_shot():
    assert normalize_recurrence_days(None) == []
    assert normalize_recurrence_days([]) == []


def test_normalize_recurrence_days_rejects_invalid_day():
    with pytest.raises(ChecklistValidationError):
        normalize_recurrence_days(["funday"])


def test_normalize_recurrence_days_deduplicates():
    assert normalize_recurrence_days(["monday", "Monday", "tuesday"]) == [
        "monday",
        "tuesday",
    ]


def test_create_assignment_rejects_end_at_before_start_at(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_shared_template(owner_membership, business_unit)
    now = timezone.now()
    with pytest.raises(ChecklistValidationError):
        create_checklist_assignment(
            template=template,
            actor=owner_membership,
            assigned_to_id=staff_membership.id,
            start_date=now.date(),

            end_date=now.date(),

            start_at=time(10, 0),

            end_at=time(9, 0),
        )


def test_create_one_shot_assignment_materializes_first_execution(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_shared_template(owner_membership, business_unit)
    now = timezone.now()
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),

        end_date=now.date(),

        start_at=now.time().replace(microsecond=0),

        end_at=(now + timezone.timedelta(hours=2)).time().replace(microsecond=0),
        recurrence_days=None,
    )

    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    assert execution.occurrence_date == now.date()
    assert execution.visible_from == execution.start_at - timezone.timedelta(hours=1)
    assert execution.assigned_to_id == staff_membership.id
    assert execution.assigned_by_id == owner_membership.id


def test_create_assignment_rejects_cross_establishment_assignee(
    owner_membership,
    business_unit,
):
    template = _active_shared_template(owner_membership, business_unit)
    other_establishment = create_establishment(name="Other")
    other_staff = create_membership(establishment=other_establishment)
    now = timezone.now()
    with pytest.raises(ChecklistValidationError):
        create_checklist_assignment(
            template=template,
            actor=owner_membership,
            assigned_to_id=other_staff.id,
            start_date=now.date(),

            end_date=now.date(),

            start_at=now.time().replace(microsecond=0),

            end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
        )


def test_staff_cannot_create_shared_assignment(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_shared_template(owner_membership, business_unit)
    now = timezone.now()
    with pytest.raises(ChecklistPermissionError):
        create_checklist_assignment(
            template=template,
            actor=staff_membership,
            assigned_to_id=staff_membership.id,
            start_date=now.date(),

            end_date=now.date(),

            start_at=now.time().replace(microsecond=0),

            end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
        )


def test_update_assignment_syncs_assigned_executions(
    owner_membership,
    staff_membership,
    other_staff_membership,
    business_unit,
):
    start_at = _next_weekday_datetime(0)
    assignment = _create_assignment(
        owner_membership,
        staff_membership,
        business_unit,
        start_at=start_at,
        end_at=start_at + timedelta(hours=2),
        recurrence_days=["monday"],
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    new_start_time = time(10, 0)
    new_end_time = time(13, 0)

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        assigned_to_id=other_staff_membership.id,
        start_at=new_start_time,
        end_at=new_end_time,
        recurrence_days=["monday"],
    )

    assignment.refresh_from_db()
    execution.refresh_from_db()
    expected_start = timezone.make_aware(
        datetime.combine(execution.occurrence_date, new_start_time),
        timezone.get_current_timezone(),
    )
    expected_end = timezone.make_aware(
        datetime.combine(execution.occurrence_date, new_end_time),
        timezone.get_current_timezone(),
    )
    assert assignment.assigned_to_id == other_staff_membership.id
    assert assignment.recurrence_days == ["monday"]
    assert execution.assigned_to_id == other_staff_membership.id
    assert execution.status == EXECUTION_STATUS_ASSIGNED
    assert execution.start_at == expected_start
    assert execution.end_at == expected_end
    assert execution.visible_from == expected_start - timezone.timedelta(hours=1)


def test_update_assignment_does_not_change_in_progress_execution(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_assignment(
        owner_membership,
        staff_membership,
        business_unit,
        task_count=2,
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    task = execution.task_executions.order_by("position").first()
    mark_task_done(task_execution=task, actor=staff_membership)
    execution.refresh_from_db()
    original_start = execution.start_at
    original_end = execution.end_at
    original_assignee = execution.assigned_to_id

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        start_date=assignment.start_date + timedelta(days=2),
        end_date=assignment.end_date + timedelta(days=2),
    )

    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.IN_PROGRESS
    assert execution.start_at == original_start
    assert execution.end_at == original_end
    assert execution.assigned_to_id == original_assignee


def test_update_assignment_does_not_change_done_execution(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, staff_membership, business_unit)
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    execution.status = ChecklistExecution.Status.DONE
    execution.done_at = timezone.now()
    execution.save(update_fields=["status", "done_at", "updated_at"])
    original_start = execution.start_at

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        end_at=time(12, 0),
    )

    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.DONE
    assert execution.start_at == original_start


def test_update_assignment_does_not_change_canceled_execution(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, staff_membership, business_unit)
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    execution.status = ChecklistExecution.Status.CANCELED
    execution.canceled_at = timezone.now()
    execution.save(update_fields=["status", "canceled_at", "updated_at"])
    original_end = execution.end_at

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        end_at=time(12, 0),
    )

    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.CANCELED
    assert execution.end_at == original_end


def test_update_assignment_rejects_inactive_assignment(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, staff_membership, business_unit)
    assignment.status = ChecklistAssignment.Status.INACTIVE
    assignment.save(update_fields=["status", "updated_at"])

    with pytest.raises(ChecklistValidationError, match=_ASSIGNMENT_INACTIVE_PATCH_MESSAGE):
        update_checklist_assignment(
            assignment=assignment,
            actor=owner_membership,
            end_at=time(12, 0),
        )


def test_manager_in_scope_can_update_assignment(
    owner_membership,
    manager_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, staff_membership, business_unit)
    updated = update_checklist_assignment(
        assignment=assignment,
        actor=manager_membership,
        recurrence_days=["friday"],
    )
    assert updated.recurrence_days == ["friday"]


def test_manager_out_of_scope_cannot_update_assignment(
    owner_membership,
    manager_membership,
    staff_membership,
    establishment,
):
    from houston.establishments.tests.taxonomy_helpers import create_business_unit

    other_business_unit = create_business_unit(establishment=establishment, key="spa")
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Spa routine",
        business_unit_id=other_business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    now = timezone.now()
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=owner_membership.id,
        start_date=now.date(),

        end_date=now.date(),

        start_at=now.time().replace(microsecond=0),

        end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
    )

    with pytest.raises(ChecklistPermissionError):
        update_checklist_assignment(
            assignment=assignment,
            actor=manager_membership,
            recurrence_days=["monday"],
        )


def test_staff_cannot_update_assignment(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, staff_membership, business_unit)
    with pytest.raises(ChecklistPermissionError):
        update_checklist_assignment(
            assignment=assignment,
            actor=staff_membership,
            recurrence_days=["monday"],
        )


def test_deactivate_assignment_without_executions_deletes_row(
    establishment,
    shared_template,
    owner_membership,
    staff_membership,
):
    assignment = ChecklistAssignment.objects.create(
        checklist_template=shared_template,
        establishment=establishment,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit=shared_template.business_unit,
        start_date=timezone.now().date(),

        end_date=timezone.now().date(),

        start_at=time(8, 0),

        end_at=time(10, 0),
    )
    assignment_id = assignment.id

    result = deactivate_checklist_assignment(assignment=assignment, actor=owner_membership)

    assert result is None
    assert not ChecklistAssignment.objects.filter(id=assignment_id).exists()


def test_deactivate_assignment_cancels_assigned_executions(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, staff_membership, business_unit)
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)

    deactivated = deactivate_checklist_assignment(assignment=assignment, actor=owner_membership)

    assert deactivated is not None
    assert deactivated.status == "inactive"
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.CANCELED
    assert execution.canceled_at is not None


def test_deactivate_assignment_blocks_in_progress(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_assignment(
        owner_membership,
        staff_membership,
        business_unit,
        task_count=2,
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    task = execution.task_executions.order_by("position").first()
    mark_task_done(task_execution=task, actor=staff_membership)
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.IN_PROGRESS

    with pytest.raises(ChecklistConflictError) as exc_info:
        deactivate_checklist_assignment(assignment=assignment, actor=owner_membership)

    assert exc_info.value.active_execution_id == execution.id
    assert str(exc_info.value) == _REMOVE_ASSIGNMENT_IN_PROGRESS_MESSAGE
    assignment.refresh_from_db()
    assert assignment.status == ChecklistAssignment.Status.ACTIVE


def test_deactivate_assignment_preserves_terminal_history(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, staff_membership, business_unit)
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    execution.status = ChecklistExecution.Status.DONE
    execution.done_at = timezone.now()
    execution.save(update_fields=["status", "done_at", "updated_at"])

    deactivated = deactivate_checklist_assignment(assignment=assignment, actor=owner_membership)

    assert deactivated is not None
    assert deactivated.status == "inactive"
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.DONE


def test_update_assignment_cancels_assigned_execution_removed_from_recurrence(
    owner_membership,
    staff_membership,
    business_unit,
):
    monday_start = _next_weekday_datetime(0)
    tuesday_date = monday_start.date() + timedelta(days=1)
    assignment = _create_assignment(
        owner_membership,
        staff_membership,
        business_unit,
        start_at=monday_start,
        end_at=monday_start + timedelta(hours=2),
        recurrence_days=["monday", "tuesday"],
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    monday_execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=monday_start.date(),
    )
    tuesday_execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=tuesday_date,
    )

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        recurrence_days=["monday"],
    )

    assignment.refresh_from_db()
    monday_execution.refresh_from_db()
    tuesday_execution.refresh_from_db()
    assert assignment.recurrence_days == ["monday"]
    assert monday_execution.status == EXECUTION_STATUS_ASSIGNED
    assert tuesday_execution.status == EXECUTION_STATUS_CANCELED
    assert tuesday_execution.canceled_at is not None
    assert not _execution_still_matches_assignment_schedule(
        execution=tuesday_execution,
        assignment=assignment,
    )
    assert _execution_still_matches_assignment_schedule(
        execution=monday_execution,
        assignment=assignment,
    )


def test_update_assignment_cancels_assigned_execution_before_new_start_date(
    owner_membership,
    staff_membership,
    business_unit,
):
    monday_start = _next_weekday_datetime(0)
    wednesday_date = monday_start.date() + timedelta(days=2)
    assignment = _create_assignment(
        owner_membership,
        staff_membership,
        business_unit,
        start_at=monday_start,
        end_at=monday_start + timedelta(hours=2),
        recurrence_days=["monday"],
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    monday_execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=monday_start.date(),
    )

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        start_date=wednesday_date,
        end_date=wednesday_date + timedelta(days=14),
    )

    assignment.refresh_from_db()
    monday_execution.refresh_from_db()
    assert assignment.start_date == wednesday_date
    assert monday_execution.status == EXECUTION_STATUS_CANCELED
    assert not _execution_still_matches_assignment_schedule(
        execution=monday_execution,
        assignment=assignment,
    )


def test_update_assignment_updates_assigned_to_on_valid_assigned_execution(
    owner_membership,
    staff_membership,
    other_staff_membership,
    business_unit,
):
    monday_start = _next_weekday_datetime(0)
    assignment = _create_assignment(
        owner_membership,
        staff_membership,
        business_unit,
        start_at=monday_start,
        end_at=monday_start + timedelta(hours=2),
        recurrence_days=["monday"],
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        assigned_to_id=other_staff_membership.id,
    )

    execution.refresh_from_db()
    assert execution.status == EXECUTION_STATUS_ASSIGNED
    assert execution.assigned_to_id == other_staff_membership.id


def test_update_assignment_auto_cancel_preserves_task_executions(
    owner_membership,
    staff_membership,
    business_unit,
):
    monday_start = _next_weekday_datetime(0)
    tuesday_date = monday_start.date() + timedelta(days=1)
    assignment = _create_assignment(
        owner_membership,
        staff_membership,
        business_unit,
        task_count=2,
        start_at=monday_start,
        end_at=monday_start + timedelta(hours=2),
        recurrence_days=["monday", "tuesday"],
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=monday_start.date(),
    )
    tuesday_execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=tuesday_date,
    )
    task_count = tuesday_execution.task_executions.count()
    assert task_count == 2

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        recurrence_days=["monday"],
    )

    tuesday_execution.refresh_from_db()
    assert tuesday_execution.status == EXECUTION_STATUS_CANCELED
    assert tuesday_execution.task_executions.count() == task_count


def test_update_assignment_auto_cancel_preserves_linked_observation(
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.observations.models import Observation

    monday_start = _next_weekday_datetime(0)
    tuesday_date = monday_start.date() + timedelta(days=1)
    assignment = _create_assignment(
        owner_membership,
        staff_membership,
        business_unit,
        task_count=2,
        start_at=monday_start,
        end_at=monday_start + timedelta(hours=2),
        recurrence_days=["monday", "tuesday"],
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=monday_start.date(),
    )
    tuesday_execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=tuesday_date,
    )
    task = tuesday_execution.task_executions.order_by("position").first()
    observation = Observation.objects.create(
        establishment_id=assignment.establishment_id,
        submitted_by_membership=staff_membership,
        raw_text="Issue on tuesday task",
        origin=Observation.Origin.CHECKLIST_TASK,
        checklist_execution=tuesday_execution,
        checklist_task_execution=task,
        submitted_at=timezone.now(),
    )
    task.status = ChecklistTaskExecution.Status.OBSERVATION_CREATED
    task.observation = observation
    task.save(update_fields=["status", "observation", "updated_at"])

    update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        recurrence_days=["monday"],
    )

    tuesday_execution.refresh_from_db()
    task.refresh_from_db()
    observation.refresh_from_db()
    assert tuesday_execution.status == EXECUTION_STATUS_CANCELED
    assert task.observation_id == observation.id
    assert observation.checklist_execution_id == tuesday_execution.id


# --- Assignee scope (éligibilité périmètre BU) ---


def test_create_assignment_assignee_in_business_unit_succeeds(
    owner_membership,
    staff_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, staff_membership, business_unit)
    assert assignment.assigned_to_id == staff_membership.id


def test_create_assignment_rejects_assignee_outside_business_unit(
    owner_membership,
    business_unit,
    establishment,
):
    unscoped_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    template = _active_shared_template(owner_membership, business_unit)
    now = timezone.now()
    with pytest.raises(ChecklistValidationError, match=_ASSIGNEE_OUT_OF_SCOPE_MESSAGE):
        create_checklist_assignment(
            template=template,
            actor=owner_membership,
            assigned_to_id=unscoped_staff.id,
            start_date=now.date(),

            end_date=now.date(),

            start_at=now.time().replace(microsecond=0),

            end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
        )


def test_create_assignment_manager_assignee_in_business_unit_succeeds(
    owner_membership,
    manager_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, manager_membership, business_unit)
    assert assignment.assigned_to_id == manager_membership.id


def test_create_assignment_rejects_manager_assignee_outside_business_unit(
    owner_membership,
    manager_membership,
    establishment,
):
    other_business_unit = create_business_unit(establishment=establishment, key="spa")
    template = _active_shared_template(owner_membership, other_business_unit)
    now = timezone.now()
    with pytest.raises(ChecklistValidationError, match=_ASSIGNEE_OUT_OF_SCOPE_MESSAGE):
        create_checklist_assignment(
            template=template,
            actor=owner_membership,
            assigned_to_id=manager_membership.id,
            start_date=now.date(),

            end_date=now.date(),

            start_at=now.time().replace(microsecond=0),

            end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
        )


def test_create_assignment_owner_assignee_succeeds(
    owner_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, owner_membership, business_unit)
    assert assignment.assigned_to_id == owner_membership.id


def test_create_assignment_director_assignee_succeeds(
    owner_membership,
    director_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, director_membership, business_unit)
    assert assignment.assigned_to_id == director_membership.id


def test_update_assignment_to_assignee_in_business_unit_succeeds(
    owner_membership,
    staff_membership,
    other_staff_membership,
    business_unit,
):
    assignment = _create_assignment(owner_membership, staff_membership, business_unit)
    updated = update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        assigned_to_id=other_staff_membership.id,
    )
    assert updated.assigned_to_id == other_staff_membership.id


def test_update_assignment_rejects_assignee_outside_business_unit(
    owner_membership,
    staff_membership,
    business_unit,
    establishment,
):
    unscoped_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    assignment = _create_assignment(owner_membership, staff_membership, business_unit)
    with pytest.raises(ChecklistValidationError, match=_ASSIGNEE_OUT_OF_SCOPE_MESSAGE):
        update_checklist_assignment(
            assignment=assignment,
            actor=owner_membership,
            assigned_to_id=unscoped_staff.id,
        )


def test_update_assignment_schedule_without_changing_legacy_out_of_scope_assignee(
    owner_membership,
    staff_membership,
    business_unit,
    establishment,
):
    unscoped_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    template = _active_shared_template(owner_membership, business_unit)
    now = timezone.now()
    assignment = ChecklistAssignment.objects.create(
        checklist_template=template,
        establishment_id=establishment.id,
        assigned_to=unscoped_staff,
        assigned_by=owner_membership,
        business_unit=business_unit,
        start_date=now.date(),

        end_date=now.date(),

        start_at=time(8, 0),

        end_at=time(10, 0),
        recurrence_days=[],
        status=ChecklistAssignment.Status.ACTIVE,
    )
    updated = update_checklist_assignment(
        assignment=assignment,
        actor=owner_membership,
        end_at=time(12, 0),
    )
    assert updated.assigned_to_id == unscoped_staff.id


def test_create_assignment_rejects_inactive_assignee(
    owner_membership,
    business_unit,
    establishment,
):
    inactive_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    inactive_staff.status = EstablishmentMembership.Status.DEACTIVATED
    inactive_staff.save(update_fields=["status", "updated_at"])
    template = _active_shared_template(owner_membership, business_unit)
    now = timezone.now()
    with pytest.raises(ChecklistValidationError, match="Invalid establishment membership."):
        create_checklist_assignment(
            template=template,
            actor=owner_membership,
            assigned_to_id=inactive_staff.id,
            start_date=now.date(),

            end_date=now.date(),

            start_at=now.time().replace(microsecond=0),

            end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
        )


# --- Actor permissions (qui assigne) ---


def test_manager_in_scope_can_create_assignment(
    manager_membership,
    staff_membership,
    business_unit,
):
    template = _active_shared_template(manager_membership, business_unit)
    now = timezone.now()
    assignment = create_checklist_assignment(
        template=template,
        actor=manager_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),

        end_date=now.date(),

        start_at=now.time().replace(microsecond=0),

        end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
    )
    assert assignment.assigned_by_id == manager_membership.id


def test_manager_out_of_scope_cannot_create_assignment(
    owner_membership,
    manager_membership,
    staff_membership,
    establishment,
):
    other_business_unit = create_business_unit(establishment=establishment, key="spa")
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Spa routine",
        business_unit_id=other_business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    now = timezone.now()
    with pytest.raises(ChecklistPermissionError):
        create_checklist_assignment(
            template=template,
            actor=manager_membership,
            assigned_to_id=staff_membership.id,
            start_date=now.date(),

            end_date=now.date(),

            start_at=now.time().replace(microsecond=0),

            end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
        )
