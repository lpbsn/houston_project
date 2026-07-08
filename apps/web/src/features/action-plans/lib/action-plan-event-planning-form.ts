import type { ActionPlanRecurrenceDay } from './action-plan-schedule-constants'
import { ACTION_PLAN_RECURRENCE_DAY_LABELS } from './action-plan-schedule-constants'
import type { ActionPlanAssigneeDraft } from './action-plan-form-validation'
import type { ActionPlanScheduleDraft } from './action-plan-schedule-form'
import { createActionPlanScheduleDraft } from './action-plan-schedule-form'

export type ActionPlanEventPlanningDraft = {
  allDay: boolean
  startDate: string
  startTime: string
  endDate: string
  endTime: string
  repeatEnabled: boolean
  recurrenceEndDate: string
  recurrenceDays: ActionPlanRecurrenceDay[]
  assignees: ActionPlanAssigneeDraft[]
  usePerAssigneeChronology: boolean
}

export type ActionPlanEventPlanningConfig = {
  canEditAssignees: boolean
  canSchedule: boolean
  staffMode: boolean
  showAdvancedChronology: boolean
  hideAssignees: boolean
  staffDisplayName?: string
}

export function createActionPlanEventPlanningDraft(): ActionPlanEventPlanningDraft {
  return {
    allDay: false,
    startDate: '',
    startTime: '',
    endDate: '',
    endTime: '',
    repeatEnabled: false,
    recurrenceEndDate: '',
    recurrenceDays: [],
    assignees: [],
    usePerAssigneeChronology: false,
  }
}

const ALL_DAY_START_TIME = '00:00'
const ALL_DAY_END_TIME = '23:59'

function resolveEffectiveTime(
  draft: ActionPlanEventPlanningDraft,
  part: 'start' | 'end',
): string {
  if (draft.allDay) {
    return part === 'start' ? ALL_DAY_START_TIME : ALL_DAY_END_TIME
  }
  return part === 'start' ? draft.startTime.trim() : draft.endTime.trim()
}

export function combineDateTimeToIso(
  date: string,
  time: string,
  part: 'start' | 'end',
): string {
  const trimmedDate = date.trim()
  if (!trimmedDate) {
    return ''
  }
  const effectiveTime =
    time.trim() || (part === 'start' ? ALL_DAY_START_TIME : ALL_DAY_END_TIME)
  const parsed = Date.parse(`${trimmedDate}T${effectiveTime}`)
  if (Number.isNaN(parsed)) {
    return ''
  }
  if (part === 'end' && effectiveTime === ALL_DAY_END_TIME) {
    return new Date(`${trimmedDate}T23:59:59`).toISOString()
  }
  return new Date(parsed).toISOString()
}

export function toSharedChronologyFields(draft: ActionPlanEventPlanningDraft): {
  sharedStartAt: string
  sharedEndAt: string
} {
  const startTime = resolveEffectiveTime(draft, 'start')
  const endTime = resolveEffectiveTime(draft, 'end')
  return {
    sharedStartAt: combineDateTimeToIso(draft.startDate, startTime, 'start'),
    sharedEndAt: combineDateTimeToIso(draft.endDate, endTime, 'end'),
  }
}

export function toScheduleDraft(draft: ActionPlanEventPlanningDraft): ActionPlanScheduleDraft {
  if (!draft.repeatEnabled) {
    return createActionPlanScheduleDraft()
  }
  const startTime = resolveEffectiveTime(draft, 'start')
  const endTime = resolveEffectiveTime(draft, 'end')
  return {
    enabled: true,
    recurrenceDays: [...draft.recurrenceDays],
    startDate: draft.startDate.trim(),
    endDate: draft.recurrenceEndDate.trim(),
    startAt: startTime,
    endAt: endTime,
  }
}

export function toCreateFormPlanningSlice(draft: ActionPlanEventPlanningDraft): {
  useSharedChronology: boolean
  sharedStartAt: string
  sharedEndAt: string
  sharedVisibleFrom: string
  schedule: ActionPlanScheduleDraft
  assignees: ActionPlanAssigneeDraft[]
} {
  const { sharedStartAt, sharedEndAt } = toSharedChronologyFields(draft)
  return {
    useSharedChronology: !draft.usePerAssigneeChronology,
    sharedStartAt,
    sharedEndAt,
    sharedVisibleFrom: '',
    schedule: toScheduleDraft(draft),
    assignees: draft.assignees,
  }
}

export function toUseRequestOptions(draft: ActionPlanEventPlanningDraft): {
  assignees: ActionPlanAssigneeDraft[]
  useSharedChronology: boolean
  sharedStartAt: string
  sharedEndAt: string
  sharedVisibleFrom: string
} {
  const { sharedStartAt, sharedEndAt } = toSharedChronologyFields(draft)
  return {
    assignees: draft.assignees,
    useSharedChronology: !draft.usePerAssigneeChronology,
    sharedStartAt,
    sharedEndAt,
    sharedVisibleFrom: '',
  }
}

export function formatAssigneeSummary(
  assignees: ActionPlanAssigneeDraft[],
  options: { staffMode?: boolean; staffDisplayName?: string } = {},
): string {
  if (options.staffMode) {
    return options.staffDisplayName ?? 'Moi'
  }
  const valid = assignees.filter((assignee) => assignee.membershipId)
  if (valid.length === 0) {
    return 'Aucun'
  }
  if (valid.length === 1) {
    return valid[0].displayName || '1 assigné'
  }
  return `${valid.length} assignés`
}

export function getDefaultPlanningTime(now: Date = new Date()): string {
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  return snapTimeToFiveMinutes(`${hours}:${minutes}`)
}

export function snapTimeToFiveMinutes(time: string): string {
  const trimmed = time.trim()
  if (!trimmed) {
    return ''
  }
  const match = /^(\d{1,2}):(\d{2})$/.exec(trimmed)
  if (!match) {
    return trimmed
  }
  let hours = Number.parseInt(match[1], 10)
  const minutes = Number.parseInt(match[2], 10)
  if (Number.isNaN(hours) || Number.isNaN(minutes)) {
    return trimmed
  }
  let snapped = Math.round(minutes / 5) * 5
  if (snapped === 60) {
    snapped = 0
    hours = (hours + 1) % 24
  }
  return `${String(hours).padStart(2, '0')}:${String(snapped).padStart(2, '0')}`
}

export function formatTimePillLabel(time: string): string {
  if (!time.trim()) {
    return '—'
  }
  return snapTimeToFiveMinutes(time)
}

export function formatDatePillLabel(date: string): string {
  const summary = formatDateSummary(date)
  return summary === 'Non défini' ? '—' : summary
}

export function splitIsoToDateAndTime(iso: string): { date: string; time: string } {
  if (!iso.trim()) {
    return { date: '', time: '' }
  }
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) {
    return { date: '', time: '' }
  }
  const offset = parsed.getTimezoneOffset()
  const local = new Date(parsed.getTime() - offset * 60_000)
  const isoLocal = local.toISOString()
  return {
    date: isoLocal.slice(0, 10),
    time: snapTimeToFiveMinutes(isoLocal.slice(11, 16)),
  }
}

export function combineDateAndTimeToIso(
  date: string,
  time: string,
  part: 'start' | 'end' = 'start',
): string {
  return combineDateTimeToIso(date, snapTimeToFiveMinutes(time), part)
}

export function formatDateSummary(date: string): string {
  if (!date.trim()) {
    return 'Non défini'
  }
  const parsed = Date.parse(`${date.trim()}T12:00:00`)
  if (Number.isNaN(parsed)) {
    return date
  }
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(parsed))
}

export function formatTimeSummary(time: string, allDay: boolean): string {
  if (allDay) {
    return ''
  }
  if (!time.trim()) {
    return '—'
  }
  return time.trim()
}

export function formatDateTimeSummary(
  date: string,
  time: string,
  allDay: boolean,
): string {
  if (!date.trim()) {
    return 'Non défini'
  }
  if (allDay) {
    return formatDateSummary(date)
  }
  const timePart = formatTimeSummary(time, false)
  return timePart === '—' ? formatDateSummary(date) : `${formatDateSummary(date)}, ${timePart}`
}

export function formatRecurrenceDaysSummary(days: ActionPlanRecurrenceDay[]): string {
  if (days.length === 0) {
    return 'Aucun'
  }
  return days.map((day) => ACTION_PLAN_RECURRENCE_DAY_LABELS[day]).join(', ')
}

export function validateActionPlanEventPlanningDraft(
  draft: ActionPlanEventPlanningDraft,
  options: { requireAssignees?: boolean; allowRepeat?: boolean } = {},
): Record<string, string> {
  const errors: Record<string, string> = {}

  if (options.requireAssignees) {
    const valid = draft.assignees.filter((assignee) => assignee.membershipId)
    if (valid.length === 0) {
      errors.assignees = 'Ajoutez au moins un assigné pour lancer le plan.'
    }
  }

  if (!draft.repeatEnabled) {
    const { sharedStartAt, sharedEndAt } = toSharedChronologyFields(draft)
    if (sharedStartAt && sharedEndAt && Date.parse(sharedEndAt) <= Date.parse(sharedStartAt)) {
      errors.endDate = 'La fin doit être postérieure au début.'
    }
    return errors
  }

  if (!options.allowRepeat) {
    errors.repeatEnabled = 'La planification récurrente n’est pas autorisée.'
    return errors
  }

  if (draft.recurrenceDays.length === 0) {
    errors.recurrenceDays = 'Sélectionnez au moins un jour.'
  }
  if (!draft.recurrenceEndDate.trim()) {
    errors.recurrenceEndDate = 'La date de fin de récurrence est requise.'
  }
  if (
    draft.startDate.trim() &&
    draft.recurrenceEndDate.trim() &&
    draft.recurrenceEndDate.trim() < draft.startDate.trim()
  ) {
    errors.recurrenceEndDate = 'La fin de récurrence doit être postérieure ou égale au début.'
  }

  const startTime = resolveEffectiveTime(draft, 'start')
  const endTime = resolveEffectiveTime(draft, 'end')
  if (!startTime) {
    errors.startTime = "L'heure de début est requise."
  }
  if (!endTime) {
    errors.endTime = "L'heure de fin est requise."
  }
  if (startTime && endTime && endTime <= startTime) {
    errors.endTime = "L'heure de fin doit être après l'heure de début."
  }

  return errors
}
