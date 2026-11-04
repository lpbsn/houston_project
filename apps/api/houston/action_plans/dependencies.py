"""One prerequisite per task. All dependency writes lock the execution first."""

from django.db import transaction

from houston.action_plans.exceptions import ActionPlanPermissionError, ActionPlanValidationError
from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionTask
from houston.action_plans.permissions import can_update_action_plan_execution_content


def require_prerequisite_done(task):
    if (
        task.depends_on_id
        and not ActionPlanExecutionTask.objects.filter(
            pk=task.depends_on_id,
            status="done",
        ).exists()
    ):
        raise ActionPlanValidationError("Terminez d’abord la tâche préalable.")


@transaction.atomic
def set_dependency(*, actor, execution_id, task_id, depends_on_id):
    execution = (
        ActionPlanExecution.objects.select_for_update()
        .filter(
            pk=execution_id,
            establishment_id=actor.establishment_id,
        )
        .first()
    )
    if not execution or not can_update_action_plan_execution_content(actor, execution):
        raise ActionPlanPermissionError("Vous ne pouvez pas modifier ces tâches.")
    tasks = {task.id: task for task in execution.task_executions.select_for_update().all()}
    task = tasks.get(task_id)
    if task is None or task.status != "pending":
        raise ActionPlanValidationError("Choisissez une tâche encore à faire.")
    seen = {task.id}
    current = depends_on_id
    while current:
        if current in seen:
            raise ActionPlanValidationError("Cette dépendance créerait une boucle.")
        seen.add(current)
        predecessor = tasks.get(current)
        if predecessor is None:
            raise ActionPlanValidationError("Choisissez une tâche de ce même groupe de travail.")
        current = predecessor.depends_on_id
    task.depends_on_id = depends_on_id
    task.save(update_fields=["depends_on", "updated_at"])
    from houston.action_plans.services import touch_execution_activity

    touch_execution_activity(execution=execution)
    return task
