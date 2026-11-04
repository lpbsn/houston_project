import type { FieldRecord } from './api'

export type GanttZoom = 'month' | 'quarter'

const DAY = 86_400_000
const iso = (date: Date) => date.toISOString().slice(0, 10)

export function shiftGanttMonth(month: string, amount: number) {
  const date = new Date(`${month}-01T12:00:00Z`)
  date.setUTCMonth(date.getUTCMonth() + amount)
  return iso(date).slice(0, 7)
}

export function dateInZone(timeZone: string, date = new Date()) {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(date)
  const value = (type: string) =>
    parts.find((part) => part.type === type)!.value
  return `${value('year')}-${value('month')}-${value('day')}`
}

// Three calendar months stay within the API's bounded 94-day window.
export function ganttWindow(month: string, zoom: GanttZoom) {
  const first = new Date(`${month}-01T12:00:00Z`)
  const after = new Date(first)
  after.setUTCMonth(after.getUTCMonth() + (zoom === 'quarter' ? 3 : 1))
  const count = Math.round((after.getTime() - first.getTime()) / DAY)
  const days = Array.from({ length: count }, (_, i) =>
    iso(new Date(first.getTime() + i * DAY)),
  )
  return { from: days[0], to: days[days.length - 1], days }
}

export function ganttSpan(record: FieldRecord, from: string, to: string) {
  const calendar = record.calendar
    ? {
        ...record.calendar,
        start:
          record.planned_start_on ??
          (record.is_milestone ? record.due_on! : record.calendar.start),
      }
    : null
  if (!record.due_on || !calendar || calendar.start > to || calendar.end < from)
    return null
  const index = (day: string) =>
    Math.round((Date.parse(day) - Date.parse(from)) / DAY)
  const last = index(to)
  const start = Math.max(0, index(calendar.start))
  const end = Math.min(last, index(calendar.end))
  const due = index(calendar.due)
  const lateStart = Math.max(start, due + 1)
  return {
    start,
    end,
    due: due >= 0 && due <= last ? due : null,
    lateStart: calendar.overdue && lateStart <= end ? lateStart : null,
    continuesBefore: calendar.start < from,
    continuesAfter: calendar.end > to,
  }
}

export function shiftDay(day: string, amount: number) {
  return iso(new Date(Date.parse(`${day}T12:00:00Z`) + amount * DAY))
}
