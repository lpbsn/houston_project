import {
  addCivilDays,
  BUSINESS_TIMEZONE,
  startOfMondayWeek,
  todayCivilDate,
} from '@/lib/business-timezone'

import type { ExecutionCalendarGranularity } from './execution-feed-url-state'

export type CalendarWindow = {
  from: string
  to: string
  days: string[]
}

export function resolveCalendarWindow(
  granularity: ExecutionCalendarGranularity,
  anchor: string,
): CalendarWindow {
  if (granularity === 'day') {
    return { from: anchor, to: anchor, days: [anchor] }
  }

  if (granularity === 'week') {
    const from = startOfMondayWeek(anchor)
    const days = Array.from({ length: 7 }, (_, index) => addCivilDays(from, index))
    return { from, to: days[6] ?? from, days }
  }

  const monthStart = `${anchor.slice(0, 7)}-01`
  const nextMonth = addCivilDays(monthStart, 32).slice(0, 7)
  const monthEnd = addCivilDays(`${nextMonth}-01`, -1)
  const from = startOfMondayWeek(monthStart)
  const lastWeekStart = startOfMondayWeek(monthEnd)
  const to = addCivilDays(lastWeekStart, 6)
  const days: string[] = []
  let cursor = from
  while (cursor <= to) {
    days.push(cursor)
    cursor = addCivilDays(cursor, 1)
  }
  return { from, to, days }
}

export function shiftCalendarAnchor(
  granularity: ExecutionCalendarGranularity,
  anchor: string,
  direction: -1 | 1,
): string {
  if (granularity === 'day') {
    return addCivilDays(anchor, direction)
  }
  if (granularity === 'week') {
    return addCivilDays(anchor, direction * 7)
  }
  const monthStart = `${anchor.slice(0, 7)}-01`
  if (direction < 0) {
    return addCivilDays(monthStart, -1).slice(0, 7) + '-01'
  }
  return addCivilDays(monthStart, 32).slice(0, 7) + '-01'
}

export function calendarAnchorToday(
  timeZone: string = BUSINESS_TIMEZONE,
  now: Date = new Date(),
): string {
  return todayCivilDate(timeZone, now)
}

export function calendarTimezoneScopeKey(
  source: 'establishment' | 'cross',
  establishmentId: string | null | undefined,
): string {
  return source === 'cross' ? 'cross' : `establishment:${establishmentId ?? ''}`
}

export type RememberedCalendarTimezone = {
  scopeKey: string
  timezone: string
}

export function rememberScopedCalendarTimezone(
  remembered: RememberedCalendarTimezone | null,
  scopeKey: string,
  liveTimezone: string | undefined,
): RememberedCalendarTimezone | null {
  if (liveTimezone) {
    return { scopeKey, timezone: liveTimezone }
  }
  if (remembered?.scopeKey === scopeKey) {
    return remembered
  }
  return null
}

export function resolveScopedCalendarTimezone(
  remembered: RememberedCalendarTimezone | null,
  liveTimezone: string | undefined,
): string {
  return liveTimezone ?? remembered?.timezone ?? BUSINESS_TIMEZONE
}

function utcNoon(date: string): Date {
  return new Date(`${date}T12:00:00.000Z`)
}

const CALENDAR_WEEKDAY_LABELS = ['lun.', 'mar.', 'mer.', 'jeu.', 'ven.', 'sam.', 'dim.']

export function calendarWeekdayLabel(date: string): string {
  const [year, month, day] = date.split('-').map((part) => Number.parseInt(part, 10))
  const weekday = new Date(Date.UTC(year, month - 1, day)).getUTCDay()
  const index = weekday === 0 ? 6 : weekday - 1
  return CALENDAR_WEEKDAY_LABELS[index] ?? ''
}

const longDayPeriodFormatter = new Intl.DateTimeFormat('fr-FR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
})
const monthPeriodFormatter = new Intl.DateTimeFormat('fr-FR', {
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
})

function formatCalendarDayPeriodLabel(date: string): string {
  return longDayPeriodFormatter.format(utcNoon(date))
}

function formatCalendarMonthPeriodLabel(anchor: string): string {
  return monthPeriodFormatter.format(utcNoon(`${anchor.slice(0, 7)}-01`))
}

/** Long desktop label. The mobile toolbar keeps formatCalendarPeriodLabel. */
export function formatDesktopCalendarPeriodLabel(
  granularity: ExecutionCalendarGranularity,
  window: CalendarWindow,
  anchor: string,
): string {
  if (granularity === 'day') {
    return formatCalendarDayPeriodLabel(window.from)
  }
  if (granularity === 'week') {
    const sameMonth = window.from.slice(0, 7) === window.to.slice(0, 7)
    const sameYear = window.from.slice(0, 4) === window.to.slice(0, 4)
    if (sameMonth) {
      const startDay = new Intl.DateTimeFormat('fr-FR', {
        day: 'numeric',
        timeZone: 'UTC',
      }).format(utcNoon(window.from))
      const end = new Intl.DateTimeFormat('fr-FR', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
        timeZone: 'UTC',
      }).format(utcNoon(window.to))
      return `${startDay} – ${end}`
    }
    const startOptions: Intl.DateTimeFormatOptions = {
      day: 'numeric',
      month: 'long',
      timeZone: 'UTC',
    }
    if (!sameYear) startOptions.year = 'numeric'
    const start = new Intl.DateTimeFormat('fr-FR', startOptions).format(utcNoon(window.from))
    const end = new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric',
      timeZone: 'UTC',
    }).format(utcNoon(window.to))
    return `${start} – ${end}`
  }
  return formatCalendarMonthPeriodLabel(anchor)
}

export function formatCalendarPeriodLabel(
  granularity: ExecutionCalendarGranularity,
  window: CalendarWindow,
  anchor: string,
): string {
  if (granularity === 'day') {
    return formatCalendarDayPeriodLabel(window.from)
  }
  if (granularity === 'week') {
    const start = new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'short',
      timeZone: 'UTC',
    }).format(utcNoon(window.from))
    const end = new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      timeZone: 'UTC',
    }).format(utcNoon(window.to))
    return `${start} – ${end}`
  }
  return formatCalendarMonthPeriodLabel(anchor)
}
