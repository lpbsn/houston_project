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
