from __future__ import annotations

from django.db.models import Q

from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTemplate,
)
from houston.establishments.membership_scope import membership_scope_covers_business_unit
from houston.establishments.models import BusinessUnit, EstablishmentMembership

_ADMIN_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }
)

_MANAGEMENT_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
        EstablishmentMembership.Role.MANAGER,
    }
)


def _is_active_membership(membership: EstablishmentMembership | None) -> bool:
    return membership is not None and membership.status == EstablishmentMembership.Status.ACTIVE


def _same_establishment(
    membership: EstablishmentMembership,
    establishment_id,
) -> bool:
    return membership.establishment_id == establishment_id


def _scope_business_unit_ids(membership: EstablishmentMembership) -> set:
    bu_ids: set = set()
    for scope in membership.scope_links.all():
        if scope.business_unit_id is not None:
            bu_ids.add(scope.business_unit_id)
    return bu_ids


def membership_covers_checklist_business_unit(
    membership: EstablishmentMembership,
    business_unit: BusinessUnit | None,
) -> bool:
    if business_unit is None:
        return False
    if membership.role in _ADMIN_ROLES:
        return business_unit.establishment_id == membership.establishment_id
    if membership.role in {
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    }:
        return membership_scope_covers_business_unit(membership, business_unit)
    return False


def build_checklist_visibility_scope_q(*, membership: EstablishmentMembership) -> Q | None:
    """Manager/Staff feed: executions whose snapshot BU is in MembershipScope."""
    if membership.role in _ADMIN_ROLES:
        return Q(establishment_id=membership.establishment_id)
    if membership.role not in {
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    }:
        return None

    bu_ids = _scope_business_unit_ids(membership)
    if not bu_ids:
        return None
    return Q(business_unit_id__in=bu_ids)


def can_access_checklist_management(membership: EstablishmentMembership | None) -> bool:
    return _is_active_membership(membership)


def can_create_registered_template(membership: EstablishmentMembership | None) -> bool:
    return _is_active_membership(membership)


def can_delete_registered_template(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if not _same_establishment(membership, template.establishment_id):
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_covers_checklist_business_unit(membership, template.business_unit)
    if membership.role == EstablishmentMembership.Role.STAFF:
        return template.created_by_id == membership.id
    return False


def can_manage_registered_template(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    return can_delete_registered_template(membership, template)


def can_view_registered_catalogue(membership: EstablishmentMembership | None) -> bool:
    return can_access_checklist_management(membership)


def registered_template_visible_to_membership(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if not _same_establishment(membership, template.establishment_id):
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    bu_ids = _scope_business_unit_ids(membership)
    if not bu_ids:
        return False
    return template.business_unit_id in bu_ids


def checklist_template_visible_to_membership(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    return registered_template_visible_to_membership(membership, template)


def can_create_checklist_assignment(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    if not _is_active_membership(membership):
        return False
    return membership.role in _MANAGEMENT_ROLES and can_manage_registered_template(
        membership,
        template,
    )


def checklist_assignment_visible_to_membership(
    membership: EstablishmentMembership | None,
    assignment: ChecklistAssignment,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if not _same_establishment(membership, assignment.establishment_id):
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_covers_checklist_business_unit(membership, assignment.business_unit)
    return False


def can_manage_checklist_assignment(
    membership: EstablishmentMembership | None,
    assignment: ChecklistAssignment,
) -> bool:
    return checklist_assignment_visible_to_membership(membership, assignment)


def can_create_flash_todo(
    membership: EstablishmentMembership | None,
    business_unit: BusinessUnit,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if not _same_establishment(membership, business_unit.establishment_id):
        return False
    return membership_covers_checklist_business_unit(membership, business_unit)


def can_launch_template_execution(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    if not checklist_template_visible_to_membership(membership, template):
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    return membership_covers_checklist_business_unit(membership, template.business_unit)


def can_use_template(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    return can_launch_template_execution(membership, template)


def can_execute_checklist_tasks(
    membership: EstablishmentMembership | None,
    execution: ChecklistExecution,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if not _same_establishment(membership, execution.establishment_id):
        return False
    return execution.assigned_to_id == membership.id


def checklist_execution_visible_to_membership(
    membership: EstablishmentMembership | None,
    execution: ChecklistExecution,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if not _same_establishment(membership, execution.establishment_id):
        return False

    if execution.assigned_to_id == membership.id:
        return True
    if execution.assigned_by_id == membership.id:
        return True
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_covers_checklist_business_unit(membership, execution.business_unit)
    return False


def can_cancel_checklist_execution(
    membership: EstablishmentMembership | None,
    execution: ChecklistExecution,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if not _same_establishment(membership, execution.establishment_id):
        return False
    if execution.assigned_to_id == membership.id:
        return True
    if execution.assigned_by_id == membership.id:
        return True
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_covers_checklist_business_unit(membership, execution.business_unit)
    return False
