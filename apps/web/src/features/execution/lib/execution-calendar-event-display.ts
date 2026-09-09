import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import { formatActionPlanExecutionStatusLabel } from '@/features/action-plans/lib/action-plan-display'
import { splitIsoToCivil } from '@/lib/business-timezone'
import { getDisplayNameInitials } from '@/lib/display-names'

type InvolvedPoleLike = {
  business_unit?: {
    specific_name?: string
  }
}

export type CalendarEventChromeDensity = 'comfortable' | 'compact'

export type CalendarEventChrome = {
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

export function calendarEventChromeForStatus(status: string): CalendarEventChrome {
  return STATUS_CHROME[status] ?? DEFAULT_CHROME
}

export function calendarEventShortStatusLabel(
  status: string,
  validatedAt?: string | null,
): string {
  if (status === 'pending_validation') {
    return 'Validation'
  }
  return formatActionPlanExecutionStatusLabel(status, { validatedAt })
}

export function resolveCalendarEventChromeDensity(input: {
  variant: 'timed' | 'allDay' | 'month'
  heightPx?: number
  narrow?: boolean
}): CalendarEventChromeDensity {
  if (input.variant === 'month') {
    return 'compact'
  }
  if (input.variant === 'allDay') {
    return 'comfortable'
  }
  const height = input.heightPx ?? 0
  if (input.narrow) {
    return height < 56 ? 'compact' : 'comfortable'
  }
  return height < 44 ? 'compact' : 'comfortable'
}

function assigneeNames(assignees: ActionPlanExecutionFeedItem['assignees']): string[] {
  return assignees
    .map((assignee) => assignee.display_name.trim())
    .filter((name) => name.length > 0)
}

export function calendarEventAssigneeInitials(
  assignees: ActionPlanExecutionFeedItem['assignees'],
): string[] {
  return assigneeNames(assignees)
    .slice(0, MAX_ASSIGNEE_AVATARS)
    .map((name) => getDisplayNameInitials(name))
}

export function calendarEventAssigneeOverflow(
  assignees: ActionPlanExecutionFeedItem['assignees'],
): number {
  return Math.max(0, assigneeNames(assignees).length - MAX_ASSIGNEE_AVATARS)
}

export function calendarUnplannedCreatedDateLabel(createdAt: string | null | undefined): string | null {
  const date = splitIsoToCivil(createdAt ?? '').date
  if (!date) {
    return null
  }
  const formatted = new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${date}T12:00:00.000Z`))
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
    statusLabel: calendarEventShortStatusLabel(item.status, item.validated_at),
    assigneeInitials: calendarEventAssigneeInitials(item.assignees),
    assigneeOverflow: calendarEventAssigneeOverflow(item.assignees),
    orgBadges: calendarEventOrgBadges(item),
  }
}
