import { ChecklistsApiError } from '@/features/checklists/api'

export function resolveChecklistErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ChecklistsApiError) {
    if (error.detail.trim().length > 0) {
      return error.detail
    }
    if (error.status === 409) {
      return 'Une exécution est déjà en cours pour cette checklist.'
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
