from __future__ import annotations

import pytest
from django.utils import timezone

from houston.checklists.materialization import materialize_execution_from_assignment
from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTemplate,
)
from houston.checklists.selectors import (
    active_assignments_for_management,
    assignments_for_management,
    checklist_execution_feed_queryset,
    get_checklist_execution_for_detail,
    personal_templates_for_membership,
    shared_templates_for_catalogue,
)
from houston.checklists.services import (
    create_checklist_assignment,
    create_checklist_template,
)
from houston.checklists.tests.conftest import add_task_template, assignment_schedule_from_datetime
from houston.establishments.tests.taxonomy_helpers import create_business_unit

pytestmark = pytest.mark.django_db


def _active_shared_template(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Shared routine",
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = ChecklistTemplate.Status.ACTIVE
    template.save(update_fields=["status", "updated_at"])
    return template


def test_shared_catalogue_owner_sees_all(owner_membership, business_unit):
    template = _active_shared_template(owner_membership, business_unit)
    ids = set(
        shared_templates_for_catalogue(membership=owner_membership).values_list("id", flat=True)
    )
    assert template.id in ids


def test_shared_catalogue_staff_is_empty(staff_membership, shared_template):
    ids = set(
        shared_templates_for_catalogue(membership=staff_membership).values_list("id", flat=True)
    )
    assert ids == set()


def test_manager_catalogue_is_scoped_to_membership_scope(
    owner_membership,
    manager_membership,
    business_unit,
    establishment,
):
    in_scope = _active_shared_template(owner_membership, business_unit)
    other_bu = create_business_unit(establishment=establishment, key="spa")
    out_scope = create_checklist_template(
        establishment_id=establishment.id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Spa routine",
        business_unit_id=other_bu.id,
    )
    add_task_template(template=out_scope, task="Task")
    out_scope.status = ChecklistTemplate.Status.ACTIVE
    out_scope.save(update_fields=["status", "updated_at"])

    ids = set(
        shared_templates_for_catalogue(membership=manager_membership).values_list("id", flat=True)
    )
    assert in_scope.id in ids
    assert out_scope.id not in ids


def test_personal_catalogue_is_own_only(
    staff_membership,
    other_staff_membership,
    personal_template,
):
    own_ids = set(
        personal_templates_for_membership(membership=staff_membership).values_list("id", flat=True)
    )
    other_ids = set(
        personal_templates_for_membership(membership=other_staff_membership).values_list(
            "id",
            flat=True,
        )
    )
    assert personal_template.id in own_ids
    assert personal_template.id not in other_ids


def test_assignments_for_management_scoped_for_manager(
    owner_membership,
    manager_membership,
    staff_membership,
    business_unit,
    establishment,
):
    template = _active_shared_template(owner_membership, business_unit)
    now = timezone.now()
    in_scope = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),

        end_date=now.date(),

        start_at=now.time().replace(microsecond=0),

        end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
    )
    other_bu = create_business_unit(establishment=establishment, key="bar")
    out_template = create_checklist_template(
        establishment_id=establishment.id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Bar routine",
        business_unit_id=other_bu.id,
    )
    add_task_template(template=out_template, task="Task")
    out_template.status = ChecklistTemplate.Status.ACTIVE
    out_template.save(update_fields=["status", "updated_at"])
    out_scope = create_checklist_assignment(
        template=out_template,
        actor=owner_membership,
        assigned_to_id=owner_membership.id,
        start_date=now.date(),

        end_date=now.date(),

        start_at=now.time().replace(microsecond=0),

        end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
    )

    ids = set(
        assignments_for_management(membership=manager_membership).values_list("id", flat=True)
    )
    assert in_scope.id in ids
    assert out_scope.id not in ids


def test_active_assignments_for_management_excludes_inactive(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_shared_template(owner_membership, business_unit)
    now = timezone.now()
    active = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        start_date=now.date(),

        end_date=now.date(),

        start_at=now.time().replace(microsecond=0),

        end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
    )
    inactive = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=owner_membership.id,
        **assignment_schedule_from_datetime(
            now + timezone.timedelta(hours=2),
            duration_hours=1,
        ),
    )
    inactive.status = ChecklistAssignment.Status.INACTIVE
    inactive.save(update_fields=["status", "updated_at"])

    ids = set(
        active_assignments_for_management(membership=owner_membership).values_list(
            "id",
            flat=True,
        )
    )
    assert active.id in ids
    assert inactive.id not in ids


def test_get_checklist_execution_for_detail_respects_visibility(
    owner_membership,
    staff_membership,
    other_staff_membership,
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

        end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)

    assert get_checklist_execution_for_detail(
        membership=staff_membership,
        execution_id=execution.id,
    ) is not None
    assert get_checklist_execution_for_detail(
        membership=other_staff_membership,
        execution_id=execution.id,
    ) is None


def test_feed_selector_invisible_two_hours_before_start_at(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_shared_template(owner_membership, business_unit)
    start_at = timezone.now() + timezone.timedelta(hours=2)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        **assignment_schedule_from_datetime(start_at, duration_hours=1),
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=start_at.date(),
    )

    ids = set(
        checklist_execution_feed_queryset(
            membership=staff_membership,
            view_mode="personal",
        ).values_list("id", flat=True)
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    assert execution.id not in ids


def test_feed_selector_visible_one_hour_before_start_at(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_shared_template(owner_membership, business_unit)
    start_at = timezone.now() + timezone.timedelta(hours=1)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        **assignment_schedule_from_datetime(start_at, duration_hours=1),
    )
    ChecklistExecution.objects.filter(checklist_assignment=assignment).delete()
    execution = materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=start_at.date(),
    )

    ids = set(
        checklist_execution_feed_queryset(
            membership=staff_membership,
            view_mode="personal",
        ).values_list("id", flat=True)
    )
    assert execution.id in ids


def test_feed_selector_keeps_overdue_execution_visible(
    owner_membership,
    staff_membership,
    business_unit,
):
    template = _active_shared_template(owner_membership, business_unit)
    start_at = timezone.now() - timezone.timedelta(hours=3)
    assignment = create_checklist_assignment(
        template=template,
        actor=owner_membership,
        assigned_to_id=staff_membership.id,
        **assignment_schedule_from_datetime(start_at, duration_hours=1),
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    execution.status = ChecklistExecution.Status.IN_PROGRESS
    execution.save(update_fields=["status", "updated_at"])

    ids = set(
        checklist_execution_feed_queryset(
            membership=staff_membership,
            view_mode="personal",
        ).values_list("id", flat=True)
    )
    assert execution.id in ids


def test_feed_selector_excludes_done_and_canceled(
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

        end_at=(now + timezone.timedelta(hours=1)).time().replace(microsecond=0),
    )
    execution = ChecklistExecution.objects.get(checklist_assignment=assignment)
    execution.status = ChecklistExecution.Status.DONE
    execution.save(update_fields=["status", "updated_at"])

    ids = set(
        checklist_execution_feed_queryset(
            membership=staff_membership,
            view_mode="personal",
        ).values_list("id", flat=True)
    )
    assert execution.id not in ids
