from __future__ import annotations

from houston.checklists.constants import (
    ACTIVE_EXECUTION_STATUSES,
    ASSIGNMENT_STATUS_ACTIVE,
    CHECKLIST_TYPE_PERSONAL,
    CHECKLIST_TYPE_SHARED,
    TEMPLATE_STATUS_ACTIVE,
    TEMPLATE_STATUS_INACTIVE,
)
from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTemplate,
)
from houston.checklists.selectors import (
    get_active_execution_for_template,
    get_in_progress_execution_for_assignment,
)
from houston.establishments.models import EstablishmentMembership

from . import permissions as checklist_permissions


def _template_task_count(template: ChecklistTemplate) -> int:
    task_count = getattr(template, "task_count", None)
    if task_count is not None:
        return task_count
    return template.task_templates.count()


def _can_manage_template(
    membership: EstablishmentMembership,
    template: ChecklistTemplate,
) -> bool:
    if template.checklist_type == CHECKLIST_TYPE_SHARED:
        return checklist_permissions.can_manage_shared_template(membership, template)
    return checklist_permissions.can_manage_personal_template(membership, template)


def _build_checklist_template_permission_hints_core(
    *,
    membership: EstablishmentMembership,
    template: ChecklistTemplate,
    include_personal_execution_hint: bool,
    reflect_delete_conflicts: bool,
) -> dict[str, bool]:
    can_manage = _can_manage_template(membership, template)
    task_count = _template_task_count(template)
    has_tasks = task_count >= 1
    is_active = template.status == TEMPLATE_STATUS_ACTIVE
    is_inactive = template.status == TEMPLATE_STATUS_INACTIVE

    can_delete = False
    if template.checklist_type == CHECKLIST_TYPE_SHARED:
        can_delete = checklist_permissions.can_delete_shared_checklist_template(
            membership,
            template,
        )
    else:
        can_delete = checklist_permissions.can_manage_personal_template(membership, template)

    if can_delete and reflect_delete_conflicts:
        can_delete = get_active_execution_for_template(template=template) is None

    can_create_assignment = (
        template.checklist_type == CHECKLIST_TYPE_SHARED
        and checklist_permissions.can_create_shared_assignment(membership, template)
        and is_active
        and has_tasks
    )

    can_create_personal_execution = False
    if include_personal_execution_hint:
        can_create_personal_execution = (
            template.checklist_type == CHECKLIST_TYPE_PERSONAL
            and checklist_permissions.can_create_personal_execution(membership, template)
            and is_active
            and has_tasks
            and get_active_execution_for_template(template=template) is None
        )

    return {
        "can_update": can_manage,
        "can_manage_tasks": can_manage,
        "can_activate": can_manage and is_inactive and has_tasks,
        "can_deactivate": can_manage and is_active,
        "can_delete": can_delete,
        "can_create_assignment": can_create_assignment,
        "can_create_personal_execution": can_create_personal_execution,
    }


def build_checklist_template_list_permission_hints(
    *,
    membership: EstablishmentMembership,
    template: ChecklistTemplate,
) -> dict[str, bool]:
    return _build_checklist_template_permission_hints_core(
        membership=membership,
        template=template,
        include_personal_execution_hint=False,
        reflect_delete_conflicts=False,
    )


def build_checklist_template_detail_permission_hints(
    *,
    membership: EstablishmentMembership,
    template: ChecklistTemplate,
) -> dict[str, bool]:
    return _build_checklist_template_permission_hints_core(
        membership=membership,
        template=template,
        include_personal_execution_hint=True,
        reflect_delete_conflicts=True,
    )


def build_checklist_assignment_permission_hints(
    *,
    membership: EstablishmentMembership,
    assignment: ChecklistAssignment,
) -> dict[str, bool]:
    is_active = assignment.status == ASSIGNMENT_STATUS_ACTIVE
    can_manage = checklist_permissions.can_manage_shared_assignment(membership, assignment)
    can_deactivate = can_manage and is_active
    if can_deactivate:
        can_deactivate = (
            get_in_progress_execution_for_assignment(assignment=assignment) is None
        )
    return {
        "can_update": can_manage and is_active,
        "can_deactivate": can_deactivate,
    }


def build_checklist_execution_permission_hints(
    *,
    membership: EstablishmentMembership,
    execution: ChecklistExecution,
) -> dict[str, bool]:
    is_active = execution.status in ACTIVE_EXECUTION_STATUSES
    return {
        "can_execute_tasks": is_active
        and checklist_permissions.can_execute_checklist_tasks(membership, execution),
        "can_cancel": is_active
        and checklist_permissions.can_cancel_checklist_execution(membership, execution),
    }
