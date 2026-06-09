from __future__ import annotations

from django.db.models import Q

from houston.checklists.constants import CHECKLIST_TYPE_PERSONAL, CHECKLIST_TYPE_SHARED
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
    return (
        membership is not None
        and membership.status == EstablishmentMembership.Status.ACTIVE
    )


def _same_establishment(
    membership: EstablishmentMembership,
    establishment_id,
) -> bool:
    return membership.establishment_id == establishment_id


def membership_covers_checklist_business_unit(
    membership: EstablishmentMembership,
    business_unit: BusinessUnit | None,
) -> bool:
    if business_unit is None:
        return False
    if membership.role in _ADMIN_ROLES:
        return business_unit.establishment_id == membership.establishment_id
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_scope_covers_business_unit(membership, business_unit)
    return False


def build_checklist_visibility_scope_q(*, membership: EstablishmentMembership) -> Q | None:
    """Manager general feed: executions whose snapshot BU is in MembershipScope."""
    if membership.role in _ADMIN_ROLES:
        return Q(establishment_id=membership.establishment_id)
    if membership.role != EstablishmentMembership.Role.MANAGER:
        return None

    bu_ids: set = set()
    for scope in membership.scope_links.all():
        if scope.business_unit_id is not None:
            bu_ids.add(scope.business_unit_id)
    if not bu_ids:
        return None
    return Q(business_unit_id__in=bu_ids)


def can_access_checklist_management(membership: EstablishmentMembership | None) -> bool:
    return _is_active_membership(membership)


def can_create_shared_template(membership: EstablishmentMembership | None) -> bool:
    if not _is_active_membership(membership):
        return False
    return membership.role in _MANAGEMENT_ROLES


def can_delete_shared_checklist_template(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if template.checklist_type != CHECKLIST_TYPE_SHARED:
        return False
    if not _same_establishment(membership, template.establishment_id):
        return False
    return membership.role in _ADMIN_ROLES


def can_manage_shared_template(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if template.checklist_type != CHECKLIST_TYPE_SHARED:
        return False
    if not _same_establishment(membership, template.establishment_id):
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_covers_checklist_business_unit(membership, template.business_unit)
    return False


def can_view_shared_catalogue(membership: EstablishmentMembership | None) -> bool:
    if not _is_active_membership(membership):
        return False
    return membership.role in _MANAGEMENT_ROLES


def shared_template_visible_to_membership(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    if not can_view_shared_catalogue(membership):
        return False
    if template.checklist_type != CHECKLIST_TYPE_SHARED:
        return False
    if not _same_establishment(membership, template.establishment_id):
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    return membership_covers_checklist_business_unit(membership, template.business_unit)


def can_create_personal_template(membership: EstablishmentMembership | None) -> bool:
    return _is_active_membership(membership)


def personal_template_visible_to_membership(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if template.checklist_type != CHECKLIST_TYPE_PERSONAL:
        return False
    if not _same_establishment(membership, template.establishment_id):
        return False
    return template.created_by_id == membership.id


def checklist_template_visible_to_membership(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    if template.checklist_type == CHECKLIST_TYPE_SHARED:
        return shared_template_visible_to_membership(membership, template)
    return personal_template_visible_to_membership(membership, template)


def can_manage_personal_template(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    return personal_template_visible_to_membership(membership, template)


def can_create_shared_assignment(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    return can_manage_shared_template(membership, template)


def checklist_assignment_visible_to_membership(
    membership: EstablishmentMembership | None,
    assignment: ChecklistAssignment,
) -> bool:
    if not can_view_shared_catalogue(membership):
        return False
    if not _same_establishment(membership, assignment.establishment_id):
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    return membership_covers_checklist_business_unit(membership, assignment.business_unit)


def can_manage_shared_assignment(
    membership: EstablishmentMembership | None,
    assignment: ChecklistAssignment,
) -> bool:
    return checklist_assignment_visible_to_membership(membership, assignment)


def can_create_personal_execution(
    membership: EstablishmentMembership | None,
    template: ChecklistTemplate,
) -> bool:
    return can_manage_personal_template(membership, template)


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

    if execution.checklist_type == CHECKLIST_TYPE_PERSONAL:
        return execution.assigned_to_id == membership.id

    if membership.role in _ADMIN_ROLES:
        return True
    if execution.assigned_to_id == membership.id:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_covers_checklist_business_unit(membership, execution.business_unit)
    return False


def can_cancel_shared_execution(
    membership: EstablishmentMembership | None,
    execution: ChecklistExecution,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if execution.checklist_type != CHECKLIST_TYPE_SHARED:
        return False
    if not _same_establishment(membership, execution.establishment_id):
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_covers_checklist_business_unit(membership, execution.business_unit)
    return False


def can_cancel_personal_execution(
    membership: EstablishmentMembership | None,
    execution: ChecklistExecution,
) -> bool:
    if not _is_active_membership(membership):
        return False
    if execution.checklist_type != CHECKLIST_TYPE_PERSONAL:
        return False
    if not _same_establishment(membership, execution.establishment_id):
        return False
    return execution.assigned_to_id == membership.id


def can_cancel_checklist_execution(
    membership: EstablishmentMembership | None,
    execution: ChecklistExecution,
) -> bool:
    if execution.checklist_type == CHECKLIST_TYPE_SHARED:
        return can_cancel_shared_execution(membership, execution)
    return can_cancel_personal_execution(membership, execution)
