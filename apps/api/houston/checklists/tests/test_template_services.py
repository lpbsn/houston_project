from __future__ import annotations

import pytest
from django.utils import timezone

from houston.checklists.exceptions import (
    ChecklistConflictError,
    ChecklistPermissionError,
    ChecklistValidationError,
)
from houston.checklists.models import ChecklistExecution, ChecklistTaskTemplate, ChecklistTemplate
from houston.checklists.services import (
    activate_checklist_template,
    add_task_template,
    create_checklist_template,
    deactivate_checklist_template,
    delete_checklist_template,
    delete_task_template,
    reorder_task_templates,
    update_checklist_template,
)
from houston.checklists.tests.conftest import add_task_template as _add_task_template
from houston.establishments.tests.taxonomy_helpers import create_establishment

pytestmark = pytest.mark.django_db


def test_create_shared_template_requires_business_unit(owner_membership, business_unit):
    with pytest.raises(ChecklistValidationError):
        create_checklist_template(
            establishment_id=owner_membership.establishment_id,
            actor=owner_membership,
            checklist_type=ChecklistTemplate.ChecklistType.SHARED,
            title="Shared",
        )


def test_staff_cannot_create_shared_template(staff_membership, business_unit):
    with pytest.raises(ChecklistPermissionError):
        create_checklist_template(
            establishment_id=staff_membership.establishment_id,
            actor=staff_membership,
            checklist_type=ChecklistTemplate.ChecklistType.SHARED,
            title="Shared",
            business_unit_id=business_unit.id,
        )


def test_create_personal_template_rejects_business_unit(staff_membership, business_unit):
    with pytest.raises(ChecklistValidationError):
        create_checklist_template(
            establishment_id=staff_membership.establishment_id,
            actor=staff_membership,
            checklist_type=ChecklistTemplate.ChecklistType.PERSONAL,
            title="Personal",
            business_unit_id=business_unit.id,
        )


def test_shared_template_rejects_cross_establishment_business_unit(
    owner_membership,
    business_unit,
):
    other_establishment = create_establishment(name="Other Hotel")
    with pytest.raises(ChecklistValidationError):
        create_checklist_template(
            establishment_id=other_establishment.id,
            actor=owner_membership,
            checklist_type=ChecklistTemplate.ChecklistType.SHARED,
            title="Shared",
            business_unit_id=business_unit.id,
        )


def test_add_task_template_auto_activates_inactive_template(staff_membership):
    template = create_checklist_template(
        establishment_id=staff_membership.establishment_id,
        actor=staff_membership,
        checklist_type=ChecklistTemplate.ChecklistType.PERSONAL,
        title="Mine",
    )
    assert template.status == ChecklistTemplate.Status.INACTIVE

    add_task_template(template=template, actor=staff_membership, task="Task 1")

    template.refresh_from_db()
    assert template.status == ChecklistTemplate.Status.ACTIVE


def test_activate_requires_at_least_one_task(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Shared",
        business_unit_id=business_unit.id,
    )
    with pytest.raises(ChecklistValidationError):
        activate_checklist_template(template=template, actor=owner_membership)


def test_activate_and_deactivate_template(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Shared",
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, actor=owner_membership, task="Task 1")
    activated = activate_checklist_template(template=template, actor=owner_membership)
    assert activated.status == ChecklistTemplate.Status.ACTIVE

    deactivated = deactivate_checklist_template(template=activated, actor=owner_membership)
    assert deactivated.status == ChecklistTemplate.Status.INACTIVE


def test_delete_last_task_deactivates_active_template(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Shared",
        business_unit_id=business_unit.id,
    )
    task = add_task_template(template=template, actor=owner_membership, task="Only task")
    activate_checklist_template(template=template, actor=owner_membership)
    delete_task_template(task_template=task, actor=owner_membership)

    template.refresh_from_db()
    assert template.status == ChecklistTemplate.Status.INACTIVE
    assert not ChecklistTaskTemplate.objects.filter(checklist_template=template).exists()


def test_reorder_task_templates(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Shared",
        business_unit_id=business_unit.id,
    )
    first = add_task_template(template=template, actor=owner_membership, task="A", position=1)
    second = add_task_template(template=template, actor=owner_membership, task="B", position=2)

    reordered = reorder_task_templates(
        template=template,
        actor=owner_membership,
        ordered_task_template_ids=[second.id, first.id],
    )
    assert [task.id for task in reordered] == [second.id, first.id]
    assert [task.position for task in reordered] == [1, 2]


def test_update_checklist_template(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        title="Shared",
        business_unit_id=business_unit.id,
        description="Before",
    )
    updated = update_checklist_template(
        template=template,
        actor=owner_membership,
        title="Updated",
        description="After",
    )
    assert updated.title == "Updated"
    assert updated.description == "After"


def test_personal_template_crud_for_staff(staff_membership):
    template = create_checklist_template(
        establishment_id=staff_membership.establishment_id,
        actor=staff_membership,
        checklist_type=ChecklistTemplate.ChecklistType.PERSONAL,
        title="Mine",
    )
    _add_task_template(template=template, task="Task")
    activate_checklist_template(template=template, actor=staff_membership)
    template.refresh_from_db()
    assert template.status == ChecklistTemplate.Status.ACTIVE


def test_delete_personal_template_detaches_terminal_executions(staff_membership, personal_template):
    now = timezone.now()
    execution = ChecklistExecution.objects.create(
        checklist_template=personal_template,
        checklist_type=ChecklistExecution.ChecklistType.PERSONAL,
        establishment_id=personal_template.establishment_id,
        assigned_to=staff_membership,
        template_title=personal_template.title,
        status=ChecklistExecution.Status.DONE,
        last_activity_at=now,
    )

    delete_checklist_template(template=personal_template, actor=staff_membership)

    assert not ChecklistTemplate.objects.filter(id=personal_template.id).exists()
    execution.refresh_from_db()
    assert execution.checklist_template_id is None


def test_delete_personal_template_blocks_active_execution(staff_membership, personal_execution):
    template = personal_execution.checklist_template
    with pytest.raises(ChecklistConflictError) as exc_info:
        delete_checklist_template(template=template, actor=staff_membership)

    assert exc_info.value.active_execution_id == personal_execution.id
    assert ChecklistTemplate.objects.filter(id=personal_execution.checklist_template_id).exists()


def test_delete_shared_template_blocks_active_execution(shared_execution, owner_membership):
    template_id = shared_execution.checklist_template_id
    template = shared_execution.checklist_template

    with pytest.raises(ChecklistConflictError) as exc_info:
        delete_checklist_template(template=template, actor=owner_membership)

    assert exc_info.value.active_execution_id == shared_execution.id
    assert ChecklistTemplate.objects.filter(id=template_id).exists()
    shared_execution.refresh_from_db()
    assert shared_execution.checklist_template_id == template_id


def test_delete_shared_template_detaches_terminal_executions(
    shared_execution,
    owner_membership,
):
    template = shared_execution.checklist_template
    shared_execution.status = ChecklistExecution.Status.DONE
    shared_execution.save(update_fields=["status", "updated_at"])

    delete_checklist_template(template=template, actor=owner_membership)

    assert not ChecklistTemplate.objects.filter(id=template.id).exists()
    shared_execution.refresh_from_db()
    assert shared_execution.checklist_template_id is None
    assert shared_execution.template_title == template.title
