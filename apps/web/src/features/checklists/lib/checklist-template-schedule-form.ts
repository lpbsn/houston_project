import type { ScopedUserSearchResult } from '@/features/actions/types'
import { formatRecurrenceDaysLabel } from '@/features/checklists/lib/checklist-recurrence'

export type TemplateScheduleFormValues = {
  assignedTo: string
  startAt: string
  endAt: string
  recurrenceDays: string[]
  recurrenceEndDate: string
}

export function getBrowserLocalDateIso(date: Date = new Date()): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function getScheduleReferenceDateIso(establishmentLocalDateIso?: string | null): string {
  if (establishmentLocalDateIso?.trim()) {
    return establishmentLocalDateIso.trim()
  }
  return getBrowserLocalDateIso()
}

export function getScheduleModeUnavailableMessage(isRecurring: boolean): string {
  return isRecurring
    ? 'Vous ne pouvez pas créer une affectation récurrente.'
    : 'Vous ne pouvez pas lancer une exécution ponctuelle.'
}

export function formatScheduleTimeLabel(value: string): string {
  if (!value.trim()) {
    return '—'
  }
  return value.slice(0, 5)
}

export function formatScheduleDateLabel(value: string): string {
  if (!value.trim()) {
    return '—'
  }
  const date = new Date(`${value}T00:00:00`)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleDateString('fr-FR')
}

export function getScheduleAssigneeLabel(options: {
  assignedTo: string
  activeMembershipId: string
  selectedUser: ScopedUserSearchResult | null
  activeMembershipDisplayName?: string | null
}): string {
  if (!options.assignedTo) {
    return '—'
  }
  if (options.assignedTo === options.activeMembershipId) {
    return 'Moi'
  }
  return (
    options.selectedUser?.display_name ??
    options.activeMembershipDisplayName ??
    'Membre sélectionné'
  )
}

export function getScheduleRecurrenceLabel(recurrenceDays: string[]): string {
  return formatRecurrenceDaysLabel(recurrenceDays)
}

export function getScheduleSubmitLabel(recurrenceDays: string[]): string {
  return recurrenceDays.length > 0 ? 'Créer l’affectation' : 'Exécution'
}

export function isRecurringSchedule(recurrenceDays: string[]): boolean {
  return recurrenceDays.length > 0
}
