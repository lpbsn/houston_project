import type { components } from '@/api/generated/types'

import type { ChecklistTaskExecution } from '../types'
import { isChecklistTaskPending } from './checklist-display'

export type ChecklistExecutionPermissionHints =
  components['schemas']['ChecklistExecutionPermissionHints']

export function hasCompleteChecklistExecutionPermissionHints(
  hints: ChecklistExecutionPermissionHints | null | undefined,
): hints is ChecklistExecutionPermissionHints {
  return (
    hints != null &&
    typeof hints.can_execute_tasks === 'boolean' &&
    typeof hints.can_cancel === 'boolean'
  )
}

export function canShowChecklistExecutionTaskActions(
  hints: ChecklistExecutionPermissionHints | null | undefined,
  options: { isTerminal: boolean; task: ChecklistTaskExecution },
): boolean {
  const { isTerminal, task } = options
  if (!hasCompleteChecklistExecutionPermissionHints(hints)) {
    return false
  }
  if (!hints.can_execute_tasks || isTerminal) {
    return false
  }
  return isChecklistTaskPending(task)
}

export function canShowChecklistExecutionCancel(
  hints: ChecklistExecutionPermissionHints | null | undefined,
  options: { isTerminal: boolean },
): boolean {
  const { isTerminal } = options
  if (!hasCompleteChecklistExecutionPermissionHints(hints)) {
    return false
  }
  return hints.can_cancel && !isTerminal
}
