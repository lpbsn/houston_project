import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import { BUSINESS_TIMEZONE, splitIsoToCivil } from '@/lib/business-timezone'
import { getDisplayNameInitials } from '@/lib/display-names'

import {
  formatActionPlanFeedCardAssigneeDisplay,
  formatActionPlanFeedCardStatusLabel,
} from './action-plan-execution-feed-card-display'
import {
  executionCalendarCategory,
  executionCalendarDateRange,
  type ExecutionCalendarCategory,
} from './execution-calendar-layout'

type InvolvedPoleLike = {
  business_unit?: {
    specific_name?: string
  }
}

type CalendarEventChrome = {
  bar: string
  background: string
  text: string
}

const DEFAULT_CHROME: CalendarEventChrome = {
  bar: '#3A7A96',
  background: 'rgba(58, 122, 150, 0.12)',
  text: '#1a1a1a',
}

const STATUS_CHROME: Record<string, CalendarEventChrome> = {
  in_progress: DEFAULT_CHROME,
  pending_validation: {
    bar: '#EF9F27',
    background: 'rgba(239, 159, 39, 0.16)',
    text: '#1a1a1a',
  },
  scheduled: {
    bar: '#8B6914',
    background: 'rgba(139, 105, 20, 0.12)',
    text: '#1a1a1a',
  },
  done: {
    bar: '#1D9E75',
    background: 'rgba(29, 158, 117, 0.12)',
    text: '#1a1a1a',
  },
  canceled: {
    bar: '#7D7B75',
    background: 'rgba(125, 123, 117, 0.14)',
    text: '#555555',
  },
}

const MAX_ASSIGNEE_AVATARS = 3

function calendarEventChromeForStatus(status: string): CalendarEventChrome {
  return STATUS_CHROME[status] ?? DEFAULT_CHROME
}

export const CALENDAR_DAY_GROUP_LABEL: Record<ExecutionCalendarCategory, string> = {
  multi_day: 'Multi-jours',
  all_day: 'Journée entière',
  timed: 'Dans la journée',
}

export function calendarEventPilotLabel(item: ActionPlanExecutionFeedItem): string {
  return item.pilot_business_unit.specific_name.trim()
}

export function calendarEventEstablishmentLabel(item: ActionPlanExecutionFeedItem): string {
  return item.establishment_name?.trim() ?? ''
}

export function formatCalendarExecutionCount(count: number): string {
  return count === 1 ? '1 exécution' : `${count} exécutions`
}

export function formatCalendarOverflowLabel(count: number): string {
  if (count === 1) return '+1 autre'
  return `+${count} autres`
}

export function calendarEventDesktopAssignees(
  assignees: ActionPlanExecutionFeedItem['assignees'],
): { visible: string[]; overflow: number } {
  const display = formatActionPlanFeedCardAssigneeDisplay(assignees)
  return { visible: display.visible, overflow: display.overflow }
}

function utcNoon(date: string): Date {
  return new Date(`${date}T12:00:00.000Z`)
}

const shortCivilFormatter = new Intl.DateTimeFormat('fr-FR', {
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
})
const civilDayFormatter = new Intl.DateTimeFormat('fr-FR', {
  day: 'numeric',
  timeZone: 'UTC',
})
const createdCivilFormatter = new Intl.DateTimeFormat('fr-FR', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})

function formatShortCivil(date: string): string {
  return shortCivilFormatter.format(utcNoon(date))
}

export function calendarEventDateRangeLabel(
  item: ActionPlanExecutionFeedItem,
  timeZone: string = BUSINESS_TIMEZONE,
): string | null {
  const range = executionCalendarDateRange(item, timeZone)
  if (!range || range.start === range.end) return null
  if (range.start.slice(0, 7) === range.end.slice(0, 7)) {
    const startDay = civilDayFormatter.format(utcNoon(range.start))
    return `${startDay} – ${formatShortCivil(range.end)}`
  }
  return `${formatShortCivil(range.start)} – ${formatShortCivil(range.end)}`
}

export function calendarEventTimeLabel(
  item: ActionPlanExecutionFeedItem,
  timeZone: string = BUSINESS_TIMEZONE,
): string | null {
  const start = splitIsoToCivil(item.start_at ?? '', timeZone)
  if (!start.time) return null
  const end = splitIsoToCivil(item.end_at ?? '', timeZone)
  if (!end.time || (end.date === start.date && end.time === start.time)) return start.time
  return `${start.time} – ${end.time}`
}

export function calendarEventScheduleLabel(
  item: ActionPlanExecutionFeedItem,
  timeZone: string = BUSINESS_TIMEZONE,
): string | null {
  const category = executionCalendarCategory(item, timeZone)
  if (category === 'multi_day') return calendarEventDateRangeLabel(item, timeZone)
  if (category === 'timed') return calendarEventTimeLabel(item, timeZone)
  return null
}

function assigneeNames(assignees: ActionPlanExecutionFeedItem['assignees']): string[] {
  return assignees
    .map((assignee) => assignee.display_name.trim())
    .filter((name) => name.length > 0)
}

function calendarEventAssigneeInitials(
  assignees: ActionPlanExecutionFeedItem['assignees'],
): string[] {
  return assigneeNames(assignees)
    .slice(0, MAX_ASSIGNEE_AVATARS)
    .map((name) => getDisplayNameInitials(name))
}

function calendarEventAssigneeOverflow(
  assignees: ActionPlanExecutionFeedItem['assignees'],
): number {
  return Math.max(0, assigneeNames(assignees).length - MAX_ASSIGNEE_AVATARS)
}

export function calendarUnplannedCreatedDateLabel(createdAt: string | null | undefined): string | null {
  const date = splitIsoToCivil(createdAt ?? '').date
  if (!date) {
    return null
  }
  const formatted = createdCivilFormatter.format(new Date(`${date}T12:00:00.000Z`))
  return `Créé le ${formatted}`
}

export function calendarEventOrgBadges(item: ActionPlanExecutionFeedItem): string[] {
  const bu = item.pilot_business_unit.specific_name.trim()
  const pole =
    item.involved_poles
      .map((entry) => (entry as InvolvedPoleLike).business_unit?.specific_name?.trim() ?? '')
      .find((label) => label.length > 0) ?? ''
  if (!pole) {
    return bu ? [bu] : []
  }
  if (bu && pole !== bu) {
    return [pole, bu]
  }
  return [pole]
}

export function calendarEventPresentation(item: ActionPlanExecutionFeedItem): {
  title: string
  chrome: CalendarEventChrome
  statusLabel: string
  assigneeInitials: string[]
  assigneeOverflow: number
  orgBadges: string[]
} {
  return {
    title: item.title,
    chrome: calendarEventChromeForStatus(item.status),
    statusLabel: formatActionPlanFeedCardStatusLabel(item),
    assigneeInitials: calendarEventAssigneeInitials(item.assignees),
    assigneeOverflow: calendarEventAssigneeOverflow(item.assignees),
    orgBadges: calendarEventOrgBadges(item),
  }
}
