from __future__ import annotations

import pytest
from django.utils import timezone

from houston.checklists.constants import EXECUTION_SOURCE_TEMPLATE
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
    create_registered_checklist_template,
    deactivate_checklist_template,
    delete_checklist_template,
    delete_task_template,
    reorder_task_templates,
    update_checklist_template,
)
from houston.checklists.tests.conftest import add_task_template as _add_task_template
from houston.establishments.tests.taxonomy_helpers import create_establishment

pytestmark = pytest.mark.django_db


def test_create_registered_template_requires_business_unit(owner_membership):
    with pytest.raises(ChecklistValidationError):
        create_checklist_template(
            establishment_id=owner_membership.establishment_id,
            actor=owner_membership,
            title="Registered",
            business_unit_id=None,
        )


def test_scoped_staff_can_create_registered_template(staff_membership, business_unit):
    template = create_checklist_template(
        establishment_id=staff_membership.establishment_id,
        actor=staff_membership,
        title="Mine",
        business_unit_id=business_unit.id,
    )
    assert template.business_unit_id == business_unit.id


def test_unscoped_staff_cannot_create_registered_template(establishment, business_unit):
    from houston.establishments.models import EstablishmentMembership
    from houston.establishments.tests.taxonomy_helpers import create_membership

    unscoped_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    with pytest.raises(ChecklistPermissionError):
        create_checklist_template(
            establishment_id=establishment.id,
            actor=unscoped_staff,
            title="Denied",
            business_unit_id=business_unit.id,
        )


def test_registered_template_rejects_cross_establishment_business_unit(
    owner_membership,
    business_unit,
):
    other_establishment = create_establishment(name="Other Hotel")
    with pytest.raises(ChecklistValidationError):
        create_checklist_template(
            establishment_id=other_establishment.id,
            actor=owner_membership,
            title="Registered",
            business_unit_id=business_unit.id,
        )


def test_add_task_template_auto_activates_inactive_template(staff_membership, business_unit):
    template = create_checklist_template(
        establishment_id=staff_membership.establishment_id,
        actor=staff_membership,
        title="Mine",
        business_unit_id=business_unit.id,
    )
    assert template.status == ChecklistTemplate.Status.INACTIVE

    add_task_template(template=template, actor=staff_membership, task="Task 1")

    template.refresh_from_db()
    assert template.status == ChecklistTemplate.Status.ACTIVE


def test_activate_requires_at_least_one_task(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        title="Registered",
        business_unit_id=business_unit.id,
    )
    with pytest.raises(ChecklistValidationError):
        activate_checklist_template(template=template, actor=owner_membership)


def test_activate_and_deactivate_template(owner_membership, business_unit):
    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        title="Registered",
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
        title="Registered",
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
        title="Registered",
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
        title="Registered",
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


def test_registered_template_crud_for_staff(staff_membership, business_unit):
    template = create_checklist_template(
        establishment_id=staff_membership.establishment_id,
        actor=staff_membership,
        title="Mine",
        business_unit_id=business_unit.id,
    )
    _add_task_template(template=template, task="Task")
    activate_checklist_template(template=template, actor=staff_membership)
    template.refresh_from_db()
    assert template.status == ChecklistTemplate.Status.ACTIVE


def test_delete_registered_template_detaches_terminal_executions(
    staff_membership,
    staff_owned_template,
):
    now = timezone.now()
    execution = ChecklistExecution.objects.create(
        checklist_template=staff_owned_template,
        execution_source=EXECUTION_SOURCE_TEMPLATE,
        establishment_id=staff_owned_template.establishment_id,
        assigned_to=staff_membership,
        business_unit=staff_owned_template.business_unit,
        template_title=staff_owned_template.title,
        status=ChecklistExecution.Status.DONE,
        last_activity_at=now,
    )

    delete_checklist_template(template=staff_owned_template, actor=staff_membership)

    assert not ChecklistTemplate.objects.filter(id=staff_owned_template.id).exists()
    execution.refresh_from_db()
    assert execution.checklist_template_id is None


def test_delete_registered_template_blocks_active_execution(
    staff_membership,
    staff_template_execution,
):
    template = staff_template_execution.checklist_template
    with pytest.raises(ChecklistConflictError) as exc_info:
        delete_checklist_template(template=template, actor=staff_membership)

    assert exc_info.value.active_execution_id == staff_template_execution.id
    assert ChecklistTemplate.objects.filter(
        id=staff_template_execution.checklist_template_id
    ).exists()


def test_create_registered_checklist_template_composite_assign_now(
    staff_membership,
    business_unit,
    other_staff_membership,
):
    template, execution = create_registered_checklist_template(
        establishment_id=staff_membership.establishment_id,
        actor=staff_membership,
        title="Composite",
        business_unit_id=business_unit.id,
        tasks=[{"title": "Step 1"}],
        assign_now=True,
        assigned_to_id=other_staff_membership.id,
    )
    assert template.status == ChecklistTemplate.Status.ACTIVE
    assert template.task_templates.count() == 1
    assert execution is not None
    assert execution.assigned_to_id == other_staff_membership.id


def test_create_registered_checklist_template_rolls_back_on_execution_failure(
    staff_membership,
    business_unit,
    other_staff_membership,
    monkeypatch,
):
    def _fail_execution(**kwargs):
        raise ChecklistValidationError("Execution creation failed.")

    monkeypatch.setattr(
        "houston.checklists.services.create_execution_from_template",
        _fail_execution,
    )

    with pytest.raises(ChecklistValidationError):
        create_registered_checklist_template(
            establishment_id=staff_membership.establishment_id,
            actor=staff_membership,
            title="Composite rollback",
            business_unit_id=business_unit.id,
            tasks=[{"title": "Step 1"}],
            assign_now=True,
            assigned_to_id=other_staff_membership.id,
        )

    assert not ChecklistTemplate.objects.filter(title="Composite rollback").exists()
    assert ChecklistTaskTemplate.objects.filter(
        checklist_template__title="Composite rollback",
    ).count() == 0
