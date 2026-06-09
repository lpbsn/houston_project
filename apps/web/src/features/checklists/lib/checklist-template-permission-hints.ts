import type { components } from '@/api/generated/types'

export type ChecklistTemplatePermissionHints =
  components['schemas']['ChecklistTemplatePermissionHints']

export function hasCompleteChecklistTemplatePermissionHints(
  hints: ChecklistTemplatePermissionHints | null | undefined,
): hints is ChecklistTemplatePermissionHints {
  return (
    hints != null &&
    typeof hints.can_update === 'boolean' &&
    typeof hints.can_manage_tasks === 'boolean' &&
    typeof hints.can_create_assignment === 'boolean' &&
    typeof hints.can_launch_execution === 'boolean' &&
    typeof hints.can_delete === 'boolean'
  )
}

export function canShowChecklistTemplateUpdate(
  hints: ChecklistTemplatePermissionHints | null | undefined,
): boolean {
  return hasCompleteChecklistTemplatePermissionHints(hints) && hints.can_update
}

export function canShowChecklistTemplateManageTasks(
  hints: ChecklistTemplatePermissionHints | null | undefined,
): boolean {
  return hasCompleteChecklistTemplatePermissionHints(hints) && hints.can_manage_tasks
}

export function canShowChecklistTemplateCreateAssignment(
  hints: ChecklistTemplatePermissionHints | null | undefined,
): boolean {
  return hasCompleteChecklistTemplatePermissionHints(hints) && hints.can_create_assignment
}

export function canShowChecklistTemplateLaunchExecution(
  hints: ChecklistTemplatePermissionHints | null | undefined,
): boolean {
  return hasCompleteChecklistTemplatePermissionHints(hints) && hints.can_launch_execution
}

export function canShowChecklistTemplateDelete(
  hints: ChecklistTemplatePermissionHints | null | undefined,
): boolean {
  return hasCompleteChecklistTemplatePermissionHints(hints) && hints.can_delete
}
