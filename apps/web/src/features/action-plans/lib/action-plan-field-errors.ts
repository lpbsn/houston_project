import type { ActionPlanTaskDraft } from './action-plan-form-validation'

/** User-content fields that make a task draft "active". Pole alone does not. */
export function isActionPlanTaskDraftEmpty(task: ActionPlanTaskDraft): boolean {
  return (
    !task.task.trim() &&
    !task.description.trim() &&
    !task.deadlineAt.trim() &&
    !task.assigneeMembershipId.trim()
  )
}

export function isActionPlanTaskDraftActive(task: ActionPlanTaskDraft): boolean {
  return !isActionPlanTaskDraftEmpty(task)
}

export type ActionPlanTaskFieldName =
  | 'task'
  | 'description'
  | 'deadlineAt'
  | 'assignee'
  | 'businessUnitId'

export function actionPlanTaskFieldKey(
  taskId: string,
  field: ActionPlanTaskFieldName,
): string {
  return `tasks.${taskId}.${field}`
}

export function parseActionPlanTaskFieldKey(
  key: string,
): { taskId: string; field: ActionPlanTaskFieldName } | null {
  const match = /^tasks\.([^.]+)\.(task|description|deadlineAt|assignee|businessUnitId)$/.exec(
    key,
  )
  if (!match) {
    return null
  }
  return {
    taskId: match[1],
    field: match[2] as ActionPlanTaskFieldName,
  }
}

/** Task advanced-section fields that require opening "Options avancées". */
export function isActionPlanTaskAdvancedFieldKey(key: string): boolean {
  const parsed = parseActionPlanTaskFieldKey(key)
  if (!parsed) {
    return false
  }
  return (
    parsed.field === 'deadlineAt' ||
    parsed.field === 'assignee' ||
    parsed.field === 'businessUnitId'
  )
}

export function taskIdsNeedingAdvancedExpand(
  fieldErrors: Record<string, string>,
): string[] {
  const ids = new Set<string>()
  for (const key of Object.keys(fieldErrors)) {
    if (!isActionPlanTaskAdvancedFieldKey(key)) {
      continue
    }
    const parsed = parseActionPlanTaskFieldKey(key)
    if (parsed) {
      ids.add(parsed.taskId)
    }
  }
  return [...ids]
}

export function mergeActionPlanFieldErrors(
  frontendFieldErrors: Record<string, string>,
  apiFieldErrors: Record<string, string>,
): Record<string, string> {
  return { ...frontendFieldErrors, ...apiFieldErrors }
}

export function clearActionPlanFieldErrorKey(
  errors: Record<string, string>,
  key: string,
): Record<string, string> {
  if (!(key in errors)) {
    return errors
  }
  const next = { ...errors }
  delete next[key]
  return next
}

export function firstMessage(messages: unknown): string | null {
  if (typeof messages === 'string' && messages.trim()) {
    return messages
  }
  if (Array.isArray(messages)) {
    for (const item of messages) {
      if (typeof item === 'string' && item.trim()) {
        return item
      }
    }
  }
  return null
}

/** Draft ids in the same order/filter as create/update task payloads (non-blank title). */
export function listActionPlanPayloadTaskIds(tasks: ActionPlanTaskDraft[]): string[] {
  return tasks.filter((task) => task.task.trim()).map((task) => task.id)
}
