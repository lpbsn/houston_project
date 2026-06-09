import { ChecklistsApiError } from '@/features/checklists/api'

export const CHECKLIST_DELETE_ACTIVE_EXECUTION_MESSAGE =
  "Cette checklist est en cours d'exécution. Terminez ou annulez l'exécution avant de la supprimer."

export function getActiveExecutionIdFromDeleteError(error: unknown): string | null {
  if (error instanceof ChecklistsApiError && error.activeExecutionId) {
    return error.activeExecutionId
  }
  return null
}

export function resolveChecklistDeleteErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ChecklistsApiError) {
    if (error.detail.trim().length > 0) {
      return error.detail
    }
    if (error.status === 409) {
      return CHECKLIST_DELETE_ACTIVE_EXECUTION_MESSAGE
    }
    if (error.status === 403) {
      return 'Vous n’avez pas l’autorisation pour cette action.'
    }
    if (error.status === 404) {
      return 'Checklist introuvable.'
    }
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message
  }

  return fallback
}
