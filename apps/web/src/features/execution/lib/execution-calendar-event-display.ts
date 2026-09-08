import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import { formatActionPlanExecutionStatusLabel } from '@/features/action-plans/lib/action-plan-display'
import { getDisplayNameInitials } from '@/lib/display-names'

type InvolvedPoleLike = {
  business_unit?: {
    specific_name?: string
  }
}

export type CalendarEventChromeDensity = 'title' | 'status' | 'assignees' | 'org'

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

const MAX_ASSIGNEE_INITIALS = 2

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
    return 'title'
  }
  if (input.variant === 'allDay') {
    return 'status'
  }
  const height = input.heightPx ?? 0
  if (input.narrow) {
    if (height < 36) {
      return 'title'
    }
    if (height < 56) {
      return 'status'
    }
    return 'assignees'
  }
  if (height < 28) {
    return 'title'
  }
  if (height < 44) {
    return 'status'
  }
  if (height < 68) {
    return 'assignees'
  }
  return 'org'
}

export function calendarEventAssigneeInitials(
  assignees: ActionPlanExecutionFeedItem['assignees'],
): string[] {
  return assignees
    .map((assignee) => assignee.display_name.trim())
    .filter((name) => name.length > 0)
    .slice(0, MAX_ASSIGNEE_INITIALS)
    .map((name) => getDisplayNameInitials(name))
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

export function calendarEventPresentation(
  item: ActionPlanExecutionFeedItem,
  density: CalendarEventChromeDensity,
): {
  title: string
  chrome: CalendarEventChrome
  statusLabel: string | null
  assigneeInitials: string[]
  orgBadges: string[]
} {
  const showStatus = density !== 'title'
  const showAssignees = density === 'assignees' || density === 'org'
  const showOrg = density === 'org'
  return {
    title: item.title,
    chrome: calendarEventChromeForStatus(item.status),
    statusLabel: showStatus
      ? calendarEventShortStatusLabel(item.status, item.validated_at)
      : null,
    assigneeInitials: showAssignees ? calendarEventAssigneeInitials(item.assignees) : [],
    orgBadges: showOrg ? calendarEventOrgBadges(item) : [],
  }
}
