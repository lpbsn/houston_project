import type { ActionPlanRecurrenceDay } from './action-plan-schedule-constants'

export type ActionPlanScheduleDraft = {
  enabled: boolean
  recurrenceDays: ActionPlanRecurrenceDay[]
  startDate: string
  endDate: string
  startAt: string
  endAt: string
}

export function createActionPlanScheduleDraft(): ActionPlanScheduleDraft {
  return {
    enabled: false,
    recurrenceDays: [],
    startDate: '',
    endDate: '',
    startAt: '',
    endAt: '',
  }
}

export function isActionPlanScheduleConfigured(draft: ActionPlanScheduleDraft): boolean {
  return (
    draft.enabled &&
    draft.recurrenceDays.length > 0 &&
    draft.endDate.trim() !== '' &&
    draft.startAt.trim() !== '' &&
    draft.endAt.trim() !== ''
  )
}

export function validateActionPlanScheduleDraft(
  draft: ActionPlanScheduleDraft,
): Record<string, string> {
  if (!draft.enabled) {
    return {}
  }

  const errors: Record<string, string> = {}
  if (draft.recurrenceDays.length === 0) {
    errors.recurrenceDays = 'Sélectionnez au moins un jour.'
  }
  if (!draft.endDate.trim()) {
    errors.endDate = 'La date de fin est requise.'
  }
  if (!draft.startAt.trim()) {
    errors.startAt = "L'heure de début est requise."
  }
  if (!draft.endAt.trim()) {
    errors.endAt = "L'heure de fin est requise."
  }
  if (
    draft.startAt.trim() &&
    draft.endAt.trim() &&
    draft.endAt.trim() <= draft.startAt.trim()
  ) {
    errors.endAt = "L'heure de fin doit être après l'heure de début."
  }
  return errors
}
