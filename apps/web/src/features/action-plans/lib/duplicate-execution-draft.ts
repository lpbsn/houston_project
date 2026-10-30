import type { ActionPlanExecutionDetail } from '../types'
import { createActionPlanTaskDraft } from './action-plan-form-validation'

/** Copy content only; a new execution must never inherit outcomes or commitments. */
export function duplicateExecutionDraft(
  execution: Pick<
    ActionPlanExecutionDetail,
    'title' | 'description' | 'pilot_business_unit' | 'task_executions'
  >,
) {
  return {
    title: `${execution.title} (copie)`,
    description: execution.description ?? '',
    pilotBusinessUnitId: execution.pilot_business_unit.id,
    tasks: [...execution.task_executions]
      .sort((a, b) => a.position - b.position)
      .map((task) => ({
        ...createActionPlanTaskDraft(task.business_unit.id),
        task: task.task,
        description: task.description ?? '',
        // Existing form validation checks copied poles against the creator's scope.
      })),
  }
}
