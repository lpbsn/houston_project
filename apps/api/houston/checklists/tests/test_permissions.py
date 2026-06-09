from __future__ import annotations

import pytest

from houston.checklists.permissions import (
    can_access_checklist_management,
    can_cancel_checklist_execution,
    can_cancel_shared_execution,
    can_create_personal_execution,
    can_create_personal_template,
    can_create_shared_assignment,
    can_create_shared_template,
    can_delete_shared_checklist_template,
    can_execute_checklist_tasks,
    can_manage_shared_template,
    can_view_shared_catalogue,
    checklist_assignment_visible_to_membership,
    checklist_execution_visible_to_membership,
    checklist_template_visible_to_membership,
    personal_template_visible_to_membership,
    shared_template_visible_to_membership,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_membership,
)

pytestmark = pytest.mark.django_db


def test_all_active_roles_can_access_checklist_management(
    owner_membership,
    director_membership,
    manager_membership,
    staff_membership,
):
    assert can_access_checklist_management(owner_membership)
    assert can_access_checklist_management(director_membership)
    assert can_access_checklist_management(manager_membership)
    assert can_access_checklist_management(staff_membership)


def test_staff_denied_shared_template_creation(staff_membership):
    assert not can_create_shared_template(staff_membership)


def test_manager_can_create_shared_template(manager_membership):
    assert can_create_shared_template(manager_membership)


def test_staff_denied_shared_catalogue(staff_membership):
    assert not can_view_shared_catalogue(staff_membership)


def test_owner_sees_all_shared_templates_in_establishment(
    establishment,
    owner_membership,
    shared_template,
    business_unit,
):
    other_bu = create_business_unit(establishment=establishment, key="spa")
    from houston.checklists.models import ChecklistTemplate

    out_of_scope = ChecklistTemplate.objects.create(
        establishment=establishment,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        created_by=owner_membership,
        business_unit=other_bu,
        title="Spa checks",
        status=ChecklistTemplate.Status.ACTIVE,
    )
    assert shared_template_visible_to_membership(owner_membership, shared_template)
    assert shared_template_visible_to_membership(owner_membership, out_of_scope)


def test_manager_sees_only_scoped_shared_templates(
    establishment,
    manager_membership,
    shared_template,
    business_unit,
    owner_membership,
):
    from houston.checklists.models import ChecklistTemplate

    other_bu = create_business_unit(establishment=establishment, key="spa")
    out_of_scope = ChecklistTemplate.objects.create(
        establishment=establishment,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        created_by=owner_membership,
        business_unit=other_bu,
        title="Spa checks",
        status=ChecklistTemplate.Status.ACTIVE,
    )
    assert shared_template_visible_to_membership(manager_membership, shared_template)
    assert not shared_template_visible_to_membership(manager_membership, out_of_scope)


def test_staff_cannot_see_shared_template(shared_template, staff_membership):
    assert not shared_template_visible_to_membership(staff_membership, shared_template)


def test_personal_template_visible_only_to_creator(
    personal_template,
    staff_membership,
    other_staff_membership,
):
    assert personal_template_visible_to_membership(staff_membership, personal_template)
    assert not personal_template_visible_to_membership(
        other_staff_membership,
        personal_template,
    )
    assert not personal_template_visible_to_membership(
        other_staff_membership,
        personal_template,
    )


def test_all_roles_can_create_personal_template(staff_membership, manager_membership):
    assert can_create_personal_template(staff_membership)
    assert can_create_personal_template(manager_membership)


def test_manager_can_manage_shared_template_in_scope(
    manager_membership,
    shared_template,
):
    assert can_manage_shared_template(manager_membership, shared_template)


def test_manager_cannot_manage_shared_template_out_of_scope(
    establishment,
    manager_membership,
    owner_membership,
):
    from houston.checklists.models import ChecklistTemplate

    other_bu = create_business_unit(establishment=establishment, key="maintenance")
    template = ChecklistTemplate.objects.create(
        establishment=establishment,
        checklist_type=ChecklistTemplate.ChecklistType.SHARED,
        created_by=owner_membership,
        business_unit=other_bu,
        title="Maintenance",
        status=ChecklistTemplate.Status.ACTIVE,
    )
    assert not can_manage_shared_template(manager_membership, template)


def test_staff_can_create_personal_execution_for_own_template(
    personal_template,
    staff_membership,
    other_staff_membership,
):
    assert can_create_personal_execution(staff_membership, personal_template)
    assert not can_create_personal_execution(other_staff_membership, personal_template)


def test_staff_can_execute_assigned_shared_execution(
    shared_execution,
    staff_membership,
    other_staff_membership,
):
    assert can_execute_checklist_tasks(staff_membership, shared_execution)
    assert not can_execute_checklist_tasks(other_staff_membership, shared_execution)


def test_owner_can_cancel_shared_execution(owner_membership, shared_execution):
    assert can_cancel_shared_execution(owner_membership, shared_execution)
    assert can_cancel_checklist_execution(owner_membership, shared_execution)


def test_staff_cannot_cancel_shared_execution(staff_membership, shared_execution):
    assert not can_cancel_shared_execution(staff_membership, shared_execution)


def test_manager_in_scope_can_cancel_shared_execution(
    manager_membership,
    shared_execution,
):
    assert can_cancel_shared_execution(manager_membership, shared_execution)


def test_assignee_can_cancel_personal_execution(
    personal_execution,
    staff_membership,
):
    assert can_cancel_checklist_execution(staff_membership, personal_execution)


def test_assignment_visibility_follows_manager_scope(
    checklist_assignment,
    manager_membership,
    staff_membership,
):
    assert checklist_assignment_visible_to_membership(
        manager_membership,
        checklist_assignment,
    )
    assert not checklist_assignment_visible_to_membership(
        staff_membership,
        checklist_assignment,
    )


def test_owner_can_create_shared_assignment(owner_membership, shared_template):
    assert can_create_shared_assignment(owner_membership, shared_template)


def test_owner_can_delete_shared_template(owner_membership, shared_template):
    assert can_delete_shared_checklist_template(owner_membership, shared_template)


def test_director_can_delete_shared_template(director_membership, shared_template):
    assert can_delete_shared_checklist_template(director_membership, shared_template)


def test_manager_cannot_delete_shared_template(manager_membership, shared_template):
    assert can_manage_shared_template(manager_membership, shared_template)
    assert not can_delete_shared_checklist_template(manager_membership, shared_template)


def test_staff_cannot_delete_shared_template(staff_membership, shared_template):
    assert not can_delete_shared_checklist_template(staff_membership, shared_template)


def test_staff_cannot_create_shared_assignment(staff_membership, shared_template):
    assert not can_create_shared_assignment(staff_membership, shared_template)


def test_execution_visible_to_assignee_and_owner(
    shared_execution,
    staff_membership,
    owner_membership,
    other_staff_membership,
):
    assert checklist_execution_visible_to_membership(staff_membership, shared_execution)
    assert checklist_execution_visible_to_membership(owner_membership, shared_execution)
    assert not checklist_execution_visible_to_membership(
        other_staff_membership,
        shared_execution,
    )


def test_personal_execution_visible_only_to_assignee(
    personal_execution,
    staff_membership,
    owner_membership,
):
    assert checklist_execution_visible_to_membership(staff_membership, personal_execution)
    assert not checklist_execution_visible_to_membership(owner_membership, personal_execution)


def test_checklist_template_visible_routes_by_type(
    shared_template,
    personal_template,
    staff_membership,
):
    assert not checklist_template_visible_to_membership(staff_membership, shared_template)
    assert checklist_template_visible_to_membership(staff_membership, personal_template)


def test_manager_without_scope_sees_no_shared_assignment(
    establishment,
    shared_template,
    owner_membership,
    staff_membership,
):
    from django.utils import timezone

    from houston.checklists.models import ChecklistAssignment

    unscoped_manager = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
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
    assert not checklist_assignment_visible_to_membership(unscoped_manager, assignment)
