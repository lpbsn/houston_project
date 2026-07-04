export type DeadlinePreset = '30m' | '1h' | '2h' | '3h'

const PRESET_OFFSET_MS: Record<DeadlinePreset, number> = {
  '30m': 30 * 60 * 1000,
  '1h': 60 * 60 * 1000,
  '2h': 2 * 60 * 60 * 1000,
  '3h': 3 * 60 * 60 * 1000,
}

export function applyDeadlinePreset(preset: DeadlinePreset, now: Date): Date {
  return new Date(now.getTime() + PRESET_OFFSET_MS[preset])
}

function padTwoDigits(value: number): string {
  return String(value).padStart(2, '0')
}

export function formatDateForInput(date: Date): string {
  return `${date.getFullYear()}-${padTwoDigits(date.getMonth() + 1)}-${padTwoDigits(date.getDate())}`
}

export function formatTimePartsFromDate(date: Date): { hours: string; minutes: string } {
  return {
    hours: padTwoDigits(date.getHours()),
    minutes: padTwoDigits(date.getMinutes()),
  }
}

export function buildDueAtFromParts(
  dateStr: string,
  hours: number,
  minutes: number,
): Date | null {
  const segments = dateStr.split('-')
  if (segments.length !== 3) {
    return null
  }
  const year = Number.parseInt(segments[0] ?? '', 10)
  const month = Number.parseInt(segments[1] ?? '', 10)
  const day = Number.parseInt(segments[2] ?? '', 10)
  if (Number.isNaN(year) || Number.isNaN(month) || Number.isNaN(day)) {
    return null
  }
  if (Number.isNaN(hours) || Number.isNaN(minutes)) {
    return null
  }
  return new Date(year, month - 1, day, hours, minutes, 0, 0)
}

export function syncDeadlineFieldsFromDueAt(dueAt: Date): {
  limitDate: string
  limitHours: string
  limitMinutes: string
} {
  const time = formatTimePartsFromDate(dueAt)
  return {
    limitDate: formatDateForInput(dueAt),
    limitHours: time.hours,
    limitMinutes: time.minutes,
  }
}

export function formatDeadlineDateLabel(dateStr: string): string {
  const due = buildDueAtFromParts(dateStr, 0, 0)
  if (!due) {
    return 'Choisir une date'
  }
  return due.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

export function formatDeadlineTimeLabel(hours: string, minutes: string): string {
  const h = Number.parseInt(hours, 10)
  const m = Number.parseInt(minutes, 10)
  if (Number.isNaN(h) || Number.isNaN(m) || h < 0 || h > 23 || m < 0 || m > 59) {
    return 'Choisir une heure'
  }
  return `${padTwoDigits(h)}:${padTwoDigits(m)}`
}

export const DEADLINE_HOUR_OPTIONS = Array.from({ length: 24 }, (_, i) => padTwoDigits(i))
export const DEADLINE_MINUTE_OPTIONS = Array.from({ length: 60 }, (_, i) => padTwoDigits(i))

/** @deprecated Prefer buildDueAtFromParts with an explicit date string. */
export function buildDueAtFromDateAndTime(baseDate: Date, hours: number, minutes: number): string {
  const due = buildDueAtFromParts(formatDateForInput(baseDate), hours, minutes)
  return (due ?? baseDate).toISOString()
}
