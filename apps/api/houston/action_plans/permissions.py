from __future__ import annotations

from django.db.models import Exists, OuterRef

from houston.action_plans.constants import ACTIVE_EXECUTION_STATUSES, CATALOG_STATUS_ACTIVE
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanSchedule,
    ActionPlanTask,
)
from houston.comments.models import CommentMention
from houston.establishments.membership_scope import (
    _iter_membership_scopes,
    membership_scope_covers_business_unit,
)
from houston.establishments.models import BusinessUnit, EstablishmentMembership
from houston.establishments.permissions import (
    can_create_action as establishment_can_create_action,
)
from houston.establishments.permissions import (
    can_validate_action as establishment_can_validate_action,
)
from houston.establishments.permissions import is_valid_membership
from houston.establishments.role_constants import _MANAGEMENT_ROLES, ADMIN_ROLES
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES
from houston.signals.models import Signal
from houston.signals.permissions import (
    signal_actionable_by_membership,
    signal_matches_membership_scope,
)


def _is_active_membership_in_establishment(
    membership: EstablishmentMembership | None,
    *,
    establishment_id,
) -> bool:
    if membership is None:
        return False
    if membership.status != EstablishmentMembership.Status.ACTIVE:
        return False
    return membership.establishment_id == establishment_id


def is_action_plan_execution_assignee(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if membership is None:
        return False
    prefetched = getattr(execution, "_prefetched_objects_cache", None)
    if prefetched is not None and "assignees" in prefetched:
        return any(
            assignee.membership_id == membership.id for assignee in execution.assignees.all()
        )
    return ActionPlanAssignee.objects.filter(
        action_plan_execution_id=execution.id,
        membership_id=membership.id,
    ).exists()


def is_pilot_pole_assignee(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if membership is None:
        return False
    prefetched = getattr(execution, "_prefetched_objects_cache", None)
    if prefetched is not None and "assignees" in prefetched:
        return any(
            assignee.membership_id == membership.id and assignee.execution_team.is_pilot
            for assignee in execution.assignees.all()
        )
    return ActionPlanAssignee.objects.filter(
        action_plan_execution_id=execution.id,
        membership_id=membership.id,
        execution_team__is_pilot=True,
    ).exists()


def manages_business_unit(
    membership: EstablishmentMembership | None,
    business_unit: BusinessUnit,
) -> bool:
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role != EstablishmentMembership.Role.MANAGER:
        return False
    return membership_scope_covers_business_unit(membership, business_unit)


def manages_pilot_pole(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if membership is None:
        return False
    pilot_business_unit = execution.pilot_business_unit
    if pilot_business_unit is None:
        return False
    return manages_business_unit(membership, pilot_business_unit)


def can_manage_contributor_pole(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
    business_unit: BusinessUnit,
) -> bool:
    if membership is None:
        return False
    if business_unit.id == execution.pilot_business_unit_id:
        return manages_pilot_pole(membership, execution)
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role != EstablishmentMembership.Role.MANAGER:
        return False
    return membership_scope_covers_business_unit(membership, business_unit)


def _scope_business_unit_ids(membership: EstablishmentMembership) -> set:
    bu_ids: set = set()
    for scope in _iter_membership_scopes(membership):
        if scope.business_unit_id is not None:
            bu_ids.add(scope.business_unit_id)
    return bu_ids


def _is_non_pilot_unassigned_task(task_execution: ActionPlanExecutionTask) -> bool:
    if task_execution.assigned_membership_id is not None:
        return False
    execution = task_execution.action_plan_execution
    return (
        task_execution.execution_team.business_unit_id != execution.pilot_business_unit_id
    )


def is_open_pole_task_for_membership(
    membership: EstablishmentMembership,
    task_execution: ActionPlanExecutionTask,
) -> bool:
    if not _is_non_pilot_unassigned_task(task_execution):
        return False
    return membership_scope_covers_business_unit(
        membership,
        task_execution.execution_team.business_unit,
    )


def execution_has_open_pole_task_in_member_scopes(
    membership: EstablishmentMembership,
    execution: ActionPlanExecution,
) -> bool:
    if membership.role != EstablishmentMembership.Role.STAFF:
        return False
    scope_bu_ids = _scope_business_unit_ids(membership)
    if not scope_bu_ids:
        return False
    prefetched = getattr(execution, "_prefetched_objects_cache", None)
    if prefetched is not None and "task_executions" in prefetched:
        for task_execution in execution.task_executions.all():
            if (
                _is_non_pilot_unassigned_task(task_execution)
                and task_execution.execution_team.business_unit_id in scope_bu_ids
            ):
                return True
        return False
    return ActionPlanExecutionTask.objects.filter(
        action_plan_execution=execution,
        assigned_membership_id__isnull=True,
        execution_team__business_unit_id__in=scope_bu_ids,
    ).exclude(
        execution_team__business_unit_id=execution.pilot_business_unit_id,
    ).exists()


def can_manage_action_plan(
    membership: EstablishmentMembership | None,
    action_plan: ActionPlan,
) -> bool:
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=action_plan.establishment_id,
    ):
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return manages_business_unit(membership, action_plan.pilot_business_unit)


def can_delete_action_plan_template(
    membership: EstablishmentMembership | None,
    action_plan: ActionPlan,
) -> bool:
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=action_plan.establishment_id,
    ):
        return False
    if membership is None:
        return False
    if not action_plan.is_reusable:
        return False
    return membership.role in ADMIN_ROLES


def task_business_units_include_cross_pole_task(
    *,
    pilot_business_unit_id,
    task_business_unit_ids,
) -> bool:
    return any(bu_id != pilot_business_unit_id for bu_id in task_business_unit_ids)


def action_plan_has_cross_pole_tasks(action_plan: ActionPlan) -> bool:
    prefetched = getattr(action_plan, "_prefetched_objects_cache", None)
    if prefetched is not None and "tasks" in prefetched:
        tasks = action_plan.tasks.all()
    else:
        tasks = ActionPlanTask.objects.filter(action_plan_id=action_plan.id)
    return task_business_units_include_cross_pole_task(
        pilot_business_unit_id=action_plan.pilot_business_unit_id,
        task_business_unit_ids=[task.business_unit_id for task in tasks],
    )


def action_plan_cross_pole_tasks_exist_subquery() -> Exists:
    cross_pole_tasks = ActionPlanTask.objects.filter(
        action_plan_id=OuterRef("pk"),
    ).exclude(business_unit_id=OuterRef("pilot_business_unit_id"))
    return Exists(cross_pole_tasks)


def _action_plan_tasks_all_on_pilot_business_unit(action_plan: ActionPlan) -> bool:
    return not action_plan_has_cross_pole_tasks(action_plan)


def staff_catalog_action_plan_in_scope(
    membership: EstablishmentMembership | None,
    action_plan: ActionPlan,
) -> bool:
    if membership is None:
        return False
    if membership.role != EstablishmentMembership.Role.STAFF:
        return False
    if action_plan.establishment_id != membership.establishment_id:
        return False
    if not establishment_can_create_action(membership):
        return False
    if not action_plan.is_reusable:
        return False
    if action_plan.catalog_status != CATALOG_STATUS_ACTIVE:
        return False
    if not membership_scope_covers_business_unit(membership, action_plan.pilot_business_unit):
        return False
    return not action_plan_has_cross_pole_tasks(action_plan)


def can_view_action_plan_catalog(membership: EstablishmentMembership | None) -> bool:
    if membership is None:
        return False
    if membership.status != EstablishmentMembership.Status.ACTIVE:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return True
    if membership.role == EstablishmentMembership.Role.STAFF:
        return establishment_can_create_action(membership)
    return False


def action_plan_execution_visible_to_membership(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if execution.created_by_id == membership.id:
        return True
    if is_action_plan_execution_assignee(membership, execution):
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        prefetched = getattr(execution, "_prefetched_objects_cache", None)
        if prefetched is not None and "execution_teams" in prefetched:
            teams = execution.execution_teams.select_related("business_unit").all()
        else:
            teams = execution.execution_teams.select_related("business_unit").all()
        return any(manages_business_unit(membership, team.business_unit) for team in teams)
    if membership.role == EstablishmentMembership.Role.STAFF:
        return execution_has_open_pole_task_in_member_scopes(membership, execution)
    return False


def is_mentioned_on_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if membership is None:
        return False
    return CommentMention.objects.filter(
        mentioned_membership_id=membership.id,
        comment__action_plan_execution_id=execution.id,
        comment__establishment_id=membership.establishment_id,
    ).exists()


def action_plan_execution_readable_to_membership(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    return action_plan_execution_visible_to_membership(
        membership,
        execution,
    ) or is_mentioned_on_action_plan_execution(membership, execution)


def action_plan_visible_to_membership(
    membership: EstablishmentMembership | None,
    action_plan: ActionPlan,
) -> bool:
    if membership is None:
        return False
    if action_plan.establishment_id != membership.establishment_id:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_scope_covers_business_unit(
            membership,
            action_plan.pilot_business_unit,
        )
    if membership.role == EstablishmentMembership.Role.STAFF:
        return staff_catalog_action_plan_in_scope(membership, action_plan)
    return False


def can_define_cross_pole_task(membership: EstablishmentMembership | None) -> bool:
    if membership is None:
        return False
    return membership.role in ADMIN_ROLES


def can_assign_to_execution_business_unit(
    membership: EstablishmentMembership | None,
    *,
    business_unit: BusinessUnit,
) -> bool:
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_scope_covers_business_unit(membership, business_unit)
    return False


def can_create_staff_feed_execution_plan(
    membership: EstablishmentMembership | None,
    *,
    pilot_business_unit: BusinessUnit,
    assignees: list,
    tasks: list,
    requires_validation: bool,
) -> bool:
    if membership is None:
        return False
    if membership.role != EstablishmentMembership.Role.STAFF:
        return False
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=pilot_business_unit.establishment_id,
    ):
        return False
    if not establishment_can_create_action(membership):
        return False
    if requires_validation:
        return False
    if not membership_scope_covers_business_unit(membership, pilot_business_unit):
        return False
    if len(assignees) != 1:
        return False
    assignee = assignees[0]
    if assignee.membership.id != membership.id:
        return False
    if assignee.business_unit.id != pilot_business_unit.id:
        return False
    if task_business_units_include_cross_pole_task(
        pilot_business_unit_id=pilot_business_unit.id,
        task_business_unit_ids=[task_item["business_unit"].id for task_item in tasks],
    ):
        return False
    for task_item in tasks:
        if not membership_scope_covers_business_unit(membership, task_item["business_unit"]):
            return False
    return True


def can_update_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if membership is None:
        return False
    if not action_plan_execution_readable_to_membership(membership, execution):
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if manages_pilot_pole(membership, execution):
        return True
    return execution.created_by_id == membership.id


def can_update_action_plan_execution_content(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    """True when the actor may open/save content edit (requires in_progress)."""
    if execution.status != ActionPlanExecution.Status.IN_PROGRESS:
        return False
    return can_update_action_plan_execution(membership, execution)


def can_mark_action_plan_execution_done(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if execution.status != ActionPlanExecution.Status.IN_PROGRESS:
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if manages_pilot_pole(membership, execution):
        return True
    return is_pilot_pole_assignee(membership, execution)


def can_validate_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not establishment_can_validate_action(membership):
        return False
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if not execution.requires_validation:
        return False
    if execution.status != ActionPlanExecution.Status.PENDING_VALIDATION:
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return manages_pilot_pole(membership, execution)


def can_reopen_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not establishment_can_validate_action(membership):
        return False
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if execution.status not in {
        ActionPlanExecution.Status.PENDING_VALIDATION,
        ActionPlanExecution.Status.DONE,
    }:
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return manages_pilot_pole(membership, execution)


def can_cancel_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not establishment_can_validate_action(membership):
        return False
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    from houston.action_plans.constants import ACTIVE_EXECUTION_STATUSES

    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return manages_pilot_pole(membership, execution)


def can_cancel_scheduled_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    from houston.action_plans.constants import EXECUTION_STATUS_SCHEDULED

    if execution.status != EXECUTION_STATUS_SCHEDULED:
        return False
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if execution.created_by_id == membership.id:
        return True
    return manages_pilot_pole(membership, execution)


def can_access_signal_for_linked_action(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    if membership is None:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return signal_matches_membership_scope(membership, signal)


def can_create_catalog_action_plan(membership: EstablishmentMembership | None) -> bool:
    if not is_valid_membership(membership):
        return False
    return membership.role in _MANAGEMENT_ROLES


def can_create_action_plan(
    membership: EstablishmentMembership | None,
    *,
    establishment_id,
    pilot_business_unit: BusinessUnit | None = None,
) -> bool:
    if not establishment_can_create_action(membership):
        return False
    if not _is_active_membership_in_establishment(membership, establishment_id=establishment_id):
        return False
    if membership is None:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if pilot_business_unit is None:
        return membership.role == EstablishmentMembership.Role.MANAGER
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_scope_covers_business_unit(membership, pilot_business_unit)
    return False


def can_create_linked_action_plan(
    membership: EstablishmentMembership | None,
    *,
    signal: Signal,
) -> bool:
    if not establishment_can_create_action(membership):
        return False
    if membership is None:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if membership.role in ADMIN_ROLES:
        return can_access_signal_for_linked_action(membership, signal)
    if not can_access_signal_for_linked_action(membership, signal):
        return False
    return signal_actionable_by_membership(membership, signal)


def can_use_action_plan(
    membership: EstablishmentMembership | None,
    action_plan: ActionPlan,
) -> bool:
    if not action_plan.is_reusable:
        return False
    if action_plan.catalog_status != CATALOG_STATUS_ACTIVE:
        return False
    return action_plan_visible_to_membership(membership, action_plan)


def can_create_action_plan_schedule(
    membership: EstablishmentMembership | None,
    action_plan: ActionPlan,
) -> bool:
    if membership is None:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return staff_catalog_action_plan_in_scope(membership, action_plan)
    return can_use_action_plan(membership, action_plan)


def can_manage_action_plan_schedule(
    membership: EstablishmentMembership | None,
    schedule: ActionPlanSchedule,
) -> bool:
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=schedule.establishment_id,
    ):
        return False
    if membership is None:
        return False
    return can_manage_action_plan(membership, schedule.action_plan)


def can_view_action_plan_schedule(
    membership: EstablishmentMembership | None,
    schedule: ActionPlanSchedule,
) -> bool:
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=schedule.establishment_id,
    ):
        return False
    if membership is None:
        return False
    return action_plan_visible_to_membership(membership, schedule.action_plan)


def can_execute_action_plan_task(
    membership: EstablishmentMembership | None,
    task_execution: ActionPlanExecutionTask,
) -> bool:
    execution = task_execution.action_plan_execution
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        return False
    if membership is None:
        return False

    task_business_unit = task_execution.execution_team.business_unit
    if membership.role in ADMIN_ROLES:
        return True
    if can_manage_contributor_pole(membership, execution, task_business_unit):
        return True
    if membership.role != EstablishmentMembership.Role.STAFF:
        return False
    if is_open_pole_task_for_membership(membership, task_execution):
        return True
    return is_action_plan_execution_assignee(
        membership,
        execution,
    ) and membership_scope_covers_business_unit(membership, task_business_unit)
