import type { components } from '@/api/generated/types'

export type ChecklistAssignmentPermissionHints =
  components['schemas']['ChecklistAssignmentPermissionHints']

export function hasCompleteChecklistAssignmentPermissionHints(
  hints: ChecklistAssignmentPermissionHints | null | undefined,
): hints is ChecklistAssignmentPermissionHints {
  return (
    hints != null &&
    typeof hints.can_update === 'boolean' &&
    typeof hints.can_deactivate === 'boolean'
  )
}

export function canShowChecklistAssignmentUpdate(
  hints: ChecklistAssignmentPermissionHints | null | undefined,
): boolean {
  return hasCompleteChecklistAssignmentPermissionHints(hints) && hints.can_update
}

export function canShowChecklistAssignmentDeactivate(
  hints: ChecklistAssignmentPermissionHints | null | undefined,
): boolean {
  return hasCompleteChecklistAssignmentPermissionHints(hints) && hints.can_deactivate
}
