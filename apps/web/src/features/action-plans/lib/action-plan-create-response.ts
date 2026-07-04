import type { ActionPlanCreate201Response, ActionPlanExecutionDetail } from '../types'

export function isActionPlanExecutionDetail(
  data: ActionPlanCreate201Response,
): data is ActionPlanExecutionDetail {
  return (
    'status' in data &&
    typeof data.status === 'string' &&
    'action_plan_id' in data
  )
}
