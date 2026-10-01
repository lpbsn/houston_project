import type {
  ActionPlanCreate201Response,
  ActionPlanExecutionDetail,
  ActionPlanPlanningSubmitResponse,
} from '../types'

export function isActionPlanExecutionDetail(
  data: ActionPlanCreate201Response,
): data is ActionPlanExecutionDetail {
  return (
    'status' in data &&
    typeof data.status === 'string' &&
    'action_plan_id' in data &&
    !('replayed' in data)
  )
}

export function resolvePlanningSuccessPath(response: ActionPlanPlanningSubmitResponse): string {
  const execution = response.executions.length === 1 ? response.executions[0] : null
  if (execution && response.schedules.length === 0 && execution.id) {
    return `/action-plans/executions/${execution.id}`
  }
  return '/execution'
}

export function isActionPlanPlanningSubmitResponse(
  data: unknown,
): data is ActionPlanPlanningSubmitResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'replayed' in data &&
    typeof (data as ActionPlanPlanningSubmitResponse).replayed === 'boolean' &&
    'summary' in data &&
    'executions' in data &&
    Array.isArray((data as ActionPlanPlanningSubmitResponse).executions) &&
    'schedules' in data &&
    Array.isArray((data as ActionPlanPlanningSubmitResponse).schedules)
  )
}
