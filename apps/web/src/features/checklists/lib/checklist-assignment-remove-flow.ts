import { ChecklistsApiError } from '@/features/checklists/api'

export const CHECKLIST_ASSIGNMENT_REMOVE_CONFIRM_MESSAGE =
  'Retirer cette affectation ? Les exécutions à faire seront annulées. Les historiques resteront conservés.'

export const CHECKLIST_ASSIGNMENT_REMOVE_SUCCESS_MESSAGE = 'Affectation retirée.'

export const CHECKLIST_ASSIGNMENT_REMOVE_IN_PROGRESS_MESSAGE =
  "Cette affectation a une exécution en cours. Terminez ou annulez cette exécution avant de retirer l'affectation."

export function getActiveExecutionIdFromAssignmentRemoveError(error: unknown): string | null {
  if (error instanceof ChecklistsApiError && error.activeExecutionId) {
    return error.activeExecutionId
  }
  return null
}

export function resolveChecklistAssignmentRemoveErrorMessage(
  error: unknown,
  fallback: string,
): string {
  if (error instanceof ChecklistsApiError) {
    if (error.detail.trim().length > 0) {
      return error.detail
    }
    if (error.status === 409) {
      return CHECKLIST_ASSIGNMENT_REMOVE_IN_PROGRESS_MESSAGE
    }
    if (error.status === 403) {
      return 'Vous n’avez pas l’autorisation pour cette action.'
    }
    if (error.status === 404) {
      return 'Affectation introuvable.'
    }
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message
  }

  return fallback
}
