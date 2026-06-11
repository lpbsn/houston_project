from __future__ import annotations

import pytest

from houston.accounts.models import User
from houston.checklists.constants import CHECKLIST_BADGE_PROCESS, CHECKLIST_BADGE_TODO
from houston.checklists.models import ChecklistTemplate
from houston.checklists.permissions import (
    can_access_checklist_management,
    can_cancel_checklist_execution,
    can_create_checklist_assignment,
    can_create_flash_todo,
    can_create_registered_template,
    can_delete_registered_template,
    can_execute_checklist_tasks,
    can_launch_template_execution,
    can_manage_registered_template,
    can_use_template,
    can_view_registered_catalogue,
    checklist_assignment_visible_to_membership,
    checklist_execution_visible_to_membership,
    checklist_template_visible_to_membership,
    registered_template_visible_to_membership,
)
from houston.checklists.tests.conftest import stable_assignment_times
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_membership,
)
from houston.organizations.models import Organization
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db


def _assert_checklist_access_denied(membership):
    assert not can_access_checklist_management(membership)
    assert not can_create_registered_template(membership)
    assert not can_view_registered_catalogue(membership)


def test_deactivated_membership_denies_checklist_permissions():
    membership = build_membership(membership_status=EstablishmentMembership.Status.DEACTIVATED)

    _assert_checklist_access_denied(membership)


@pytest.mark.parametrize(
    "establishment_status",
    [
        Establishment.Status.DRAFT,
        Establishment.Status.DEACTIVATED,
    ],
)
def test_non_active_establishment_denies_checklist_permissions(establishment_status):
    membership = build_membership(establishment_status=establishment_status)

    _assert_checklist_access_denied(membership)


@pytest.mark.parametrize(
    "organization_status",
    [
        Organization.Status.SUSPENDED,
        Organization.Status.ARCHIVED,
    ],
)
def test_non_active_organization_denies_checklist_permissions(organization_status):
    membership = build_membership(organization_status=organization_status)

    _assert_checklist_access_denied(membership)


@pytest.mark.parametrize(
    "user_status",
    [
        User.Status.PENDING,
        User.Status.SUSPENDED,
        User.Status.ANONYMIZED,
    ],
)
def test_non_active_user_denies_checklist_permissions(user_status):
    membership = build_membership(user_status=user_status)

    _assert_checklist_access_denied(membership)


def test_deactivated_membership_denies_object_scoped_checklist_permissions(
    registered_template,
    assignment_execution,
):
    membership = build_membership(membership_status=EstablishmentMembership.Status.DEACTIVATED)

    assert not registered_template_visible_to_membership(membership, registered_template)
    assert not can_execute_checklist_tasks(membership, assignment_execution)
    assert not checklist_execution_visible_to_membership(membership, assignment_execution)


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


def test_all_roles_can_access_registered_catalogue(staff_membership, manager_membership):
    assert can_view_registered_catalogue(staff_membership)
    assert can_view_registered_catalogue(manager_membership)


def test_owner_sees_all_registered_templates_in_establishment(
    establishment,
    owner_membership,
    registered_template,
    business_unit,
):
    other_bu = create_business_unit(establishment=establishment, key="spa")
    out_of_scope = ChecklistTemplate.objects.create(
        establishment=establishment,
        created_by=owner_membership,
        business_unit=other_bu,
        title="Spa checks",
        status=ChecklistTemplate.Status.ACTIVE,
    )
    assert registered_template_visible_to_membership(owner_membership, registered_template)
    assert registered_template_visible_to_membership(owner_membership, out_of_scope)


def test_manager_sees_only_scoped_registered_templates(
    establishment,
    manager_membership,
    registered_template,
    owner_membership,
):
    other_bu = create_business_unit(establishment=establishment, key="spa")
    out_of_scope = ChecklistTemplate.objects.create(
        establishment=establishment,
        created_by=owner_membership,
        business_unit=other_bu,
        title="Spa checks",
        status=ChecklistTemplate.Status.ACTIVE,
    )
    assert registered_template_visible_to_membership(manager_membership, registered_template)
    assert not registered_template_visible_to_membership(manager_membership, out_of_scope)


def test_staff_sees_scoped_registered_template(registered_template, staff_membership):
    assert registered_template_visible_to_membership(staff_membership, registered_template)


def test_staff_cannot_see_registered_template_out_of_scope(
    establishment,
    staff_membership,
    owner_membership,
):
    other_bu = create_business_unit(establishment=establishment, key="spa")
    template = ChecklistTemplate.objects.create(
        establishment=establishment,
        created_by=owner_membership,
        business_unit=other_bu,
        title="Spa checks",
        status=ChecklistTemplate.Status.ACTIVE,
    )
    assert not registered_template_visible_to_membership(staff_membership, template)


def test_staff_can_launch_execution_from_other_authors_template_in_scope(
    registered_template,
    staff_membership,
    other_staff_membership,
):
    assert can_launch_template_execution(staff_membership, registered_template)
    assert can_use_template(staff_membership, registered_template)
    assert can_launch_template_execution(other_staff_membership, registered_template)


def test_staff_can_manage_only_own_template(
    staff_owned_template,
    staff_membership,
    other_staff_membership,
):
    assert can_manage_registered_template(staff_membership, staff_owned_template)
    assert not can_manage_registered_template(other_staff_membership, staff_owned_template)


def test_all_roles_can_create_registered_template(staff_membership, manager_membership):
    assert can_create_registered_template(staff_membership)
    assert can_create_registered_template(manager_membership)


def test_manager_can_manage_registered_template_in_scope(
    manager_membership,
    registered_template,
):
    assert can_manage_registered_template(manager_membership, registered_template)


def test_manager_cannot_manage_registered_template_out_of_scope(
    establishment,
    manager_membership,
    owner_membership,
):
    other_bu = create_business_unit(establishment=establishment, key="maintenance")
    template = ChecklistTemplate.objects.create(
        establishment=establishment,
        created_by=owner_membership,
        business_unit=other_bu,
        title="Maintenance",
        status=ChecklistTemplate.Status.ACTIVE,
    )
    assert not can_manage_registered_template(manager_membership, template)


def test_staff_can_create_flash_todo_in_scope(staff_membership, business_unit):
    assert can_create_flash_todo(staff_membership, business_unit)


def test_staff_denied_flash_todo_out_of_scope(establishment, staff_membership):
    other_bu = create_business_unit(establishment=establishment, key="spa")
    assert not can_create_flash_todo(staff_membership, other_bu)


def test_badge_does_not_change_launch_permission(
    establishment,
    staff_membership,
    business_unit,
    owner_membership,
):
    process_template = ChecklistTemplate.objects.create(
        establishment=establishment,
        created_by=owner_membership,
        business_unit=business_unit,
        title="Process",
        badge=CHECKLIST_BADGE_PROCESS,
        status=ChecklistTemplate.Status.ACTIVE,
    )
    todo_template = ChecklistTemplate.objects.create(
        establishment=establishment,
        created_by=owner_membership,
        business_unit=business_unit,
        title="Todo",
        badge=CHECKLIST_BADGE_TODO,
        status=ChecklistTemplate.Status.ACTIVE,
    )
    assert can_launch_template_execution(staff_membership, process_template)
    assert can_launch_template_execution(staff_membership, todo_template)


def test_staff_can_execute_assigned_assignment_execution(
    assignment_execution,
    staff_membership,
    other_staff_membership,
):
    assert can_execute_checklist_tasks(staff_membership, assignment_execution)
    assert not can_execute_checklist_tasks(other_staff_membership, assignment_execution)


def test_owner_can_cancel_assignment_execution(owner_membership, assignment_execution):
    assert can_cancel_checklist_execution(owner_membership, assignment_execution)


def test_staff_assignee_can_cancel_execution(staff_membership, assignment_execution):
    assert can_cancel_checklist_execution(staff_membership, assignment_execution)


def test_staff_non_assignee_cannot_cancel_assignment_execution(
    assignment_execution,
    other_staff_membership,
):
    assert not can_cancel_checklist_execution(other_staff_membership, assignment_execution)


def test_manager_in_scope_can_cancel_assignment_execution(
    manager_membership,
    assignment_execution,
):
    assert can_cancel_checklist_execution(manager_membership, assignment_execution)


def test_assignee_can_cancel_template_execution(
    staff_template_execution,
    staff_membership,
):
    assert can_cancel_checklist_execution(staff_membership, staff_template_execution)


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


def test_owner_can_create_checklist_assignment(owner_membership, registered_template):
    assert can_create_checklist_assignment(owner_membership, registered_template)


def test_owner_can_delete_registered_template(owner_membership, registered_template):
    assert can_delete_registered_template(owner_membership, registered_template)


def test_director_can_delete_registered_template(director_membership, registered_template):
    assert can_delete_registered_template(director_membership, registered_template)


def test_manager_can_delete_registered_template_in_scope(
    manager_membership,
    registered_template,
):
    assert can_manage_registered_template(manager_membership, registered_template)
    assert can_delete_registered_template(manager_membership, registered_template)


def test_staff_can_delete_own_template(staff_membership, staff_owned_template):
    assert can_delete_registered_template(staff_membership, staff_owned_template)


def test_staff_cannot_delete_other_authors_template(
    staff_membership,
    registered_template,
):
    assert not can_delete_registered_template(staff_membership, registered_template)


def test_staff_cannot_create_checklist_assignment(staff_membership, registered_template):
    assert not can_create_checklist_assignment(staff_membership, registered_template)


def test_execution_visible_to_assignee_and_owner(
    assignment_execution,
    staff_membership,
    owner_membership,
    other_staff_membership,
):
    assert checklist_execution_visible_to_membership(staff_membership, assignment_execution)
    assert checklist_execution_visible_to_membership(owner_membership, assignment_execution)
    assert not checklist_execution_visible_to_membership(
        other_staff_membership,
        assignment_execution,
    )


def test_template_execution_visible_only_to_assignee_for_staff_roles(
    staff_template_execution,
    staff_membership,
    owner_membership,
):
    assert checklist_execution_visible_to_membership(staff_membership, staff_template_execution)
    assert checklist_execution_visible_to_membership(owner_membership, staff_template_execution)


def test_staff_sees_scoped_registered_template_regardless_of_author(
    registered_template,
    staff_owned_template,
    staff_membership,
):
    assert checklist_template_visible_to_membership(staff_membership, registered_template)
    assert checklist_template_visible_to_membership(staff_membership, staff_owned_template)


def test_manager_without_scope_sees_no_assignment(
    establishment,
    registered_template,
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
    assert not checklist_assignment_visible_to_membership(unscoped_manager, assignment)
