import type { ActionPlanRecurrenceDay } from './action-plan-schedule-constants'
import { ACTION_PLAN_RECURRENCE_DAY_LABELS } from './action-plan-schedule-constants'
import type { ActionPlanAssigneeDraft } from './action-plan-form-validation'
import type { ActionPlanScheduleDraft } from './action-plan-schedule-form'
import { createActionPlanScheduleDraft } from './action-plan-schedule-form'
import { buildActionPlanScheduleCreateRequest } from './action-plan-schedule-payload'
import type { ActionPlanScheduleCreateRequest, ActionPlanUseRequest } from '../types'
import { buildActionPlanUseRequest } from './action-plan-create-payload'

export type ActionPlanEventPlanningDraft = {
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
  planningPersisted?: boolean
  assigneeActionsEnabled?: boolean
}

export function hasGlobalRepeat(draft: ActionPlanEventPlanningDraft): boolean {
  return draft.repeatEnabled && !draft.usePerAssigneeChronology
}

export function hasPerAssigneeRepeat(draft: ActionPlanEventPlanningDraft): boolean {
  return draft.usePerAssigneeChronology && draft.assignees.some((assignee) => assignee.repeatEnabled)
}

export function shouldHidePrimaryPlanningActions(draft: ActionPlanEventPlanningDraft): boolean {
  return draft.usePerAssigneeChronology
}

export function createActionPlanEventPlanningDraft(): ActionPlanEventPlanningDraft {
  return {
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
  const endDate = hasGlobalRepeat(draft) ? draft.startDate : draft.endDate
  return {
    sharedStartAt: combineDateTimeToIso(draft.startDate, startTime, 'start'),
    sharedEndAt: combineDateTimeToIso(endDate, endTime, 'end'),
  }
}

export function toScheduleDraft(draft: ActionPlanEventPlanningDraft): ActionPlanScheduleDraft {
  if (!hasGlobalRepeat(draft)) {
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

export function formatTimeSummary(time: string): string {
  if (!time.trim()) {
    return '—'
  }
  return time.trim()
}

export function formatDateTimeSummary(date: string, time: string): string {
  if (!date.trim()) {
    return 'Non défini'
  }
  const timePart = formatTimeSummary(time)
  return timePart === '—' ? formatDateSummary(date) : `${formatDateSummary(date)}, ${timePart}`
}

export function formatRecurrenceDaysSummary(days: ActionPlanRecurrenceDay[]): string {
  if (days.length === 0) {
    return 'Aucun'
  }
  return days.map((day) => ACTION_PLAN_RECURRENCE_DAY_LABELS[day]).join(', ')
}

function resolveAssigneeSlotTimes(assignee: ActionPlanAssigneeDraft): {
  startTime: string
  endTime: string
} {
  const startParts = splitIsoToDateAndTime(assignee.startAt)
  const endParts = splitIsoToDateAndTime(assignee.endAt)
  return { startTime: startParts.time, endTime: endParts.time }
}

export function buildScheduleRequestForAssignee(
  _draft: ActionPlanEventPlanningDraft,
  assignee: ActionPlanAssigneeDraft,
  options: { staffMode?: boolean } = {},
): ActionPlanScheduleCreateRequest | undefined {
  const startParts = splitIsoToDateAndTime(assignee.startAt)
  const { endTime } = resolveAssigneeSlotTimes(assignee)
  const schedule: ActionPlanScheduleDraft = {
    enabled: true,
    recurrenceDays: [...assignee.recurrenceDays],
    startDate: startParts.date.trim(),
    endDate: assignee.recurrenceEndDate.trim(),
    startAt: startParts.time,
    endAt: endTime,
  }
  return buildActionPlanScheduleCreateRequest({
    schedule,
    assignees: options.staffMode ? [] : [assignee],
    useSharedChronology: false,
  })
}

export function buildScheduleRequestsFromDraft(
  draft: ActionPlanEventPlanningDraft,
  options: { staffMode?: boolean } = {},
): ActionPlanScheduleCreateRequest[] {
  if (hasGlobalRepeat(draft)) {
    const body = buildActionPlanScheduleCreateRequest({
      schedule: toScheduleDraft(draft),
      assignees: options.staffMode ? [] : draft.assignees,
      useSharedChronology: true,
    })
    return body ? [body] : []
  }

  if (!draft.usePerAssigneeChronology) {
    return []
  }

  return draft.assignees
    .filter((assignee) => assignee.repeatEnabled && assignee.membershipId && assignee.businessUnitId)
    .map((assignee) => buildScheduleRequestForAssignee(draft, assignee, options))
    .filter((body): body is ActionPlanScheduleCreateRequest => body !== undefined)
}

export function buildOneShotAssigneesFromDraft(
  draft: ActionPlanEventPlanningDraft,
): ActionPlanAssigneeDraft[] {
  if (draft.usePerAssigneeChronology) {
    return draft.assignees.filter((assignee) => !assignee.repeatEnabled && assignee.membershipId)
  }
  return draft.assignees.filter((assignee) => assignee.membershipId)
}

export function buildUseRequestFromDraft(
  draft: ActionPlanEventPlanningDraft,
  options: { staffMode?: boolean } = {},
): ActionPlanUseRequest {
  const oneShotAssignees = options.staffMode
    ? draft.assignees.filter((assignee) => assignee.membershipId)
    : buildOneShotAssigneesFromDraft(draft)
  const { sharedStartAt, sharedEndAt } = toSharedChronologyFields(draft)
  return buildActionPlanUseRequest({
    assignees: oneShotAssignees,
    useSharedChronology: !draft.usePerAssigneeChronology,
    sharedStartAt,
    sharedEndAt,
    sharedVisibleFrom: '',
  })
}

export function buildUseRequestForAssignee(
  _draft: ActionPlanEventPlanningDraft,
  assignee: ActionPlanAssigneeDraft,
): ActionPlanUseRequest | undefined {
  if (!assignee.membershipId || !assignee.businessUnitId) {
    return undefined
  }
  const startAt = assignee.startAt.trim()
  const endAt = assignee.endAt.trim()
  if (!startAt || !endAt) {
    return undefined
  }
  return buildActionPlanUseRequest({
    assignees: [assignee],
    useSharedChronology: false,
    sharedStartAt: startAt,
    sharedEndAt: endAt,
    sharedVisibleFrom: '',
  })
}

export function validateAssigneePlanningAction(
  draft: ActionPlanEventPlanningDraft,
  assigneeId: string,
  options: { allowRepeat?: boolean; action: 'schedule' | 'launch' } = { action: 'launch' },
): Record<string, string> {
  const assignee = draft.assignees.find((candidate) => candidate.id === assigneeId)
  if (!assignee) {
    return {}
  }

  const errors: Record<string, string> = {}
  const key = (field: string) => `assignee.${assigneeId}.${field}`

  if (!assignee.membershipId || !assignee.businessUnitId) {
    errors[key('assignee')] = 'Assigné incomplet.'
    return errors
  }

  const startParts = splitIsoToDateAndTime(assignee.startAt)
  const endParts = splitIsoToDateAndTime(assignee.endAt)

  if (options.action === 'schedule') {
    if (!options.allowRepeat) {
      errors[key('repeatEnabled')] = 'La planification récurrente n’est pas autorisée.'
      return errors
    }

    if (!startParts.date.trim()) {
      errors[key('startDate')] = 'La date de début est requise.'
    }
    if (!startParts.time) {
      errors[key('startTime')] = "L'heure de début est requise."
    }
    if (!endParts.time) {
      errors[key('endTime')] = "L'heure de fin du créneau est requise."
    }
    if (startParts.time && endParts.time && endParts.time <= startParts.time) {
      errors[key('endTime')] = "L'heure de fin doit être après l'heure de début."
    }
    if (assignee.recurrenceDays.length === 0) {
      errors[key('recurrenceDays')] = 'Sélectionnez au moins un jour.'
    }
    if (!assignee.recurrenceEndDate.trim()) {
      errors[key('recurrenceEndDate')] = 'La date de fin de récurrence est requise.'
    }
    if (
      startParts.date.trim() &&
      assignee.recurrenceEndDate.trim() &&
      assignee.recurrenceEndDate.trim() < startParts.date.trim()
    ) {
      errors[key('recurrenceEndDate')] =
        'La fin de récurrence doit être postérieure ou égale au début.'
    }
    return errors
  }

  if (!startParts.date.trim()) {
    errors[key('startDate')] = 'La date de début est requise.'
  }
  if (!startParts.time) {
    errors[key('startTime')] = "L'heure de début est requise."
  }
  if (!endParts.date.trim()) {
    errors[key('endDate')] = 'La date de fin est requise.'
  }
  if (!endParts.time) {
    errors[key('endTime')] = "L'heure de fin est requise."
  }

  const startAt =
    assignee.startAt.trim() ||
    combineDateAndTimeToIso(startParts.date, startParts.time, 'start')
  const endAt =
    assignee.endAt.trim() || combineDateAndTimeToIso(endParts.date, endParts.time, 'end')
  if (startAt && endAt && Date.parse(endAt) <= Date.parse(startAt)) {
    errors[key('endDate')] = 'La fin doit être postérieure au début.'
  }

  return errors
}

function recurringPlanningSignature(assignee: ActionPlanAssigneeDraft): string {
  const startDate = splitIsoToDateAndTime(assignee.startAt).date
  const days = [...assignee.recurrenceDays].sort().join(',')
  return `${startDate}|${assignee.recurrenceEndDate.trim()}|${days}`
}

export function validatePerAssigneePlanningDraft(
  draft: ActionPlanEventPlanningDraft,
  options: { allowRepeat?: boolean; requireCompatibleRepeats?: boolean } = {},
): Record<string, string> {
  const errors: Record<string, string> = {}
  const validAssignees = draft.assignees.filter(
    (assignee) => assignee.membershipId && assignee.businessUnitId,
  )

  if (validAssignees.length === 0) {
    errors.assignees = 'Ajoutez au moins un assigné pour lancer le plan.'
  }

  for (const assignee of draft.assignees) {
    const assigneeErrors = validateAssigneePlanningAction(draft, assignee.id, {
      allowRepeat: options.allowRepeat,
      action: assignee.repeatEnabled ? 'schedule' : 'launch',
    })
    Object.assign(errors, assigneeErrors)
  }

  if (options.requireCompatibleRepeats) {
    const signatures = new Set(
      validAssignees
        .filter((assignee) => assignee.repeatEnabled)
        .map(recurringPlanningSignature),
    )
    if (signatures.size > 1) {
      errors.assignees =
        'Les récurrences doivent partager les mêmes dates et jours pour être créées ensemble.'
    }
  }

  return errors
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

  if (draft.usePerAssigneeChronology) {
    return errors
  }

  if (!hasGlobalRepeat(draft)) {
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
