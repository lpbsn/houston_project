import type { ActionPlanTaskExecution } from '../types'

export function filterActionPlanTasksByPole(
  tasks: ActionPlanTaskExecution[],
  businessUnitId: string | null,
): ActionPlanTaskExecution[] {
  if (!businessUnitId) {
    return tasks
  }

  return tasks.filter((task) => task.business_unit.id === businessUnitId)
}
