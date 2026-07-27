import { ActionPlansApiError } from '../api'
import {
  actionPlanTaskFieldKey,
  firstMessage,
  type ActionPlanTaskFieldName,
} from './action-plan-field-errors'
import { resolveActionPlanErrorMessage } from './action-plan-errors'

/**
 * Confirmed DRF serializer error trees only (see plan audit):
 * - create/update: errors.tasks[i].{task,business_unit_id,...}
 * - execution PATCH: errors.pending_tasks[i].…
 * - planning: errors.items[i].{end_date,start_at,end_at,recurrence_days,…}
 * Service flat {code,detail} and PlanningSubmissionItemError → global.
 */

export type MapActionPlanApiErrorsOptions = {
  /** Draft ids parallel to submitted `tasks` / `pending_tasks` array. */
  payloadTaskIds?: string[]
  /** API list key for task errors. */
  taskListKey?: 'tasks' | 'pending_tasks'
  fallbackDetail?: string
}

export type MappedActionPlanApiErrors = {
  apiFieldErrors: Record<string, string>
  globalError: string | null
}

const TOP_LEVEL_FIELD_MAP: Record<string, string> = {
  title: 'title',
  pilot_business_unit_id: 'pilotBusinessUnitId',
  description: 'description',
  assignees: 'assignees',
  end_at: 'endAt',
  issue_focus: 'issueFocus',
}

const TASK_FIELD_MAP: Record<string, ActionPlanTaskFieldName> = {
  task: 'task',
  description: 'description',
  deadline_at: 'deadlineAt',
  assigned_membership_id: 'assignee',
  business_unit_id: 'businessUnitId',
}

const PLANNING_ITEM_FIELD_MAP: Record<string, string> = {
  end_date: 'endDate',
  start_at: 'startAt',
  end_at: 'endAt',
  recurrence_days: 'recurrenceDays',
  start_date: 'startDate',
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function mapTaskListErrors(
  list: unknown,
  payloadTaskIds: string[],
  apiFieldErrors: Record<string, string>,
  unmapped: string[],
): void {
  if (!Array.isArray(list)) {
    const message = firstMessage(list)
    if (message) {
      unmapped.push(message)
    }
    return
  }

  list.forEach((item, index) => {
    const taskId = payloadTaskIds[index]
    if (!taskId) {
      const message = firstMessage(item) ?? (isPlainObject(item) ? null : null)
      if (isPlainObject(item)) {
        for (const value of Object.values(item)) {
          const nested = firstMessage(value)
          if (nested) {
            unmapped.push(nested)
          }
        }
      } else if (message) {
        unmapped.push(message)
      }
      return
    }

    if (!isPlainObject(item)) {
      const message = firstMessage(item)
      if (message) {
        unmapped.push(message)
      }
      return
    }

    for (const [apiField, value] of Object.entries(item)) {
      const message = firstMessage(value)
      if (!message) {
        continue
      }
      const mappedField = TASK_FIELD_MAP[apiField]
      if (!mappedField) {
        unmapped.push(message)
        continue
      }
      apiFieldErrors[actionPlanTaskFieldKey(taskId, mappedField)] = message
    }
  })
}

function mapPlanningItemsErrors(
  list: unknown,
  apiFieldErrors: Record<string, string>,
  unmapped: string[],
): void {
  if (!Array.isArray(list)) {
    const message = firstMessage(list)
    if (message) {
      unmapped.push(message)
    }
    return
  }

  list.forEach((item, index) => {
    if (!isPlainObject(item)) {
      const message = firstMessage(item)
      if (message) {
        unmapped.push(message)
      }
      return
    }

    for (const [apiField, value] of Object.entries(item)) {
      const message = firstMessage(value)
      if (!message) {
        continue
      }
      const mapped = PLANNING_ITEM_FIELD_MAP[apiField]
      // Only attach first item's known schedule fields to shared planning controls.
      if (mapped && index === 0) {
        apiFieldErrors[mapped] = message
      } else {
        unmapped.push(message)
      }
    }
  })
}

export function mapActionPlanApiErrors(
  error: unknown,
  options: MapActionPlanApiErrorsOptions = {},
): MappedActionPlanApiErrors {
  const fallback =
    options.fallbackDetail ?? 'Une erreur est survenue.'
  const detail = resolveActionPlanErrorMessage(error, fallback)

  if (!(error instanceof ActionPlansApiError) || error.errors == null) {
    return { apiFieldErrors: {}, globalError: detail }
  }

  if (!isPlainObject(error.errors)) {
    return { apiFieldErrors: {}, globalError: detail }
  }

  const apiFieldErrors: Record<string, string> = {}
  const unmapped: string[] = []
  const payloadTaskIds = options.payloadTaskIds ?? []
  const taskListKey = options.taskListKey ?? 'tasks'

  for (const [key, value] of Object.entries(error.errors)) {
    if (key === 'non_field_errors') {
      const message = firstMessage(value)
      if (message) {
        unmapped.push(message)
      }
      continue
    }

    if (key === taskListKey) {
      mapTaskListErrors(value, payloadTaskIds, apiFieldErrors, unmapped)
      continue
    }

    if (key === 'items') {
      mapPlanningItemsErrors(value, apiFieldErrors, unmapped)
      continue
    }

    const mappedTop = TOP_LEVEL_FIELD_MAP[key]
    if (mappedTop) {
      const message = firstMessage(value)
      if (message) {
        apiFieldErrors[mappedTop] = message
      } else if (isPlainObject(value) || Array.isArray(value)) {
        unmapped.push(detail)
      }
      continue
    }

    const message = firstMessage(value)
    if (message) {
      unmapped.push(message)
    } else {
      unmapped.push(detail)
    }
  }

  const hasFieldErrors = Object.keys(apiFieldErrors).length > 0
  return {
    apiFieldErrors,
    globalError: unmapped.length > 0 ? unmapped[0] : hasFieldErrors ? null : detail,
  }
}
