import type {
  ActionPlanExecutionPermissionHints,
  ActionPlanPermissionHints,
  ActionPlanTaskExecution,
  ActionPlanTaskExecutionPermissionHints,
} from '../types'
import { isActionPlanTaskPending } from './action-plan-display'

export function canShowActionPlanUpdate(
  hints: ActionPlanPermissionHints | null | undefined,
): boolean {
  return hints?.can_update === true
}

export function canShowActionPlanActivate(
  hints: ActionPlanPermissionHints | null | undefined,
): boolean {
  return hints?.can_activate === true
}

export function canShowActionPlanDeactivate(
  hints: ActionPlanPermissionHints | null | undefined,
): boolean {
  return hints?.can_deactivate === true
}

export function canShowActionPlanUse(
  hints: ActionPlanPermissionHints | null | undefined,
): boolean {
  return hints?.can_use === true
}

export function canShowActionPlanSchedule(
  hints: ActionPlanPermissionHints | null | undefined,
): boolean {
  return hints?.can_schedule === true
}

export function canShowActionPlanExecutionMarkDone(
  hints: ActionPlanExecutionPermissionHints | null | undefined,
): boolean {
  return hints?.can_mark_done === true
}

export function canShowActionPlanExecutionValidate(
  hints: ActionPlanExecutionPermissionHints | null | undefined,
): boolean {
  return hints?.can_validate === true
}

export function canShowActionPlanExecutionReopen(
  hints: ActionPlanExecutionPermissionHints | null | undefined,
): boolean {
  return hints?.can_reopen === true
}

export function canShowActionPlanExecutionCancel(
  hints: ActionPlanExecutionPermissionHints | null | undefined,
  options: { isTerminal: boolean },
): boolean {
  return hints?.can_cancel === true && !options.isTerminal
}

export function canShowActionPlanTaskMarkDone(
  hints: ActionPlanTaskExecutionPermissionHints | null | undefined,
  options: { isTerminal: boolean; task: ActionPlanTaskExecution },
): boolean {
  if (!hints?.can_mark_done || options.isTerminal) {
    return false
  }
  return isActionPlanTaskPending(options.task)
}

export function canShowActionPlanTaskUnmarkDone(
  hints: ActionPlanTaskExecutionPermissionHints | null | undefined,
  options: { isTerminal: boolean; task: ActionPlanTaskExecution },
): boolean {
  if (!hints?.can_unmark_done || options.isTerminal) {
    return false
  }
  return options.task.status === 'done'
}

export function canShowActionPlanTaskSkip(
  hints: ActionPlanTaskExecutionPermissionHints | null | undefined,
  options: { isTerminal: boolean; task: ActionPlanTaskExecution },
): boolean {
  if (!hints?.can_skip || options.isTerminal) {
    return false
  }
  return isActionPlanTaskPending(options.task)
}

export function canShowActionPlanTaskCreateObservation(
  hints: ActionPlanTaskExecutionPermissionHints | null | undefined,
  options: { isTerminal: boolean; task: ActionPlanTaskExecution },
): boolean {
  if (!hints?.can_create_observation || options.isTerminal) {
    return false
  }
  return isActionPlanTaskPending(options.task)
}
