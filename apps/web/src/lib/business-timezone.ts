export const BUSINESS_TIMEZONE = 'Europe/Paris'

function partsInTimeZone(instant: Date, timeZone: string): Record<string, string> {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  })
  const parts: Record<string, string> = {}
  for (const part of formatter.formatToParts(instant)) {
    if (part.type !== 'literal') {
      parts[part.type] = part.value
    }
  }
  return parts
}

export function combineCivilDateTimeToIso(
  date: string,
  time: string,
  timeZone: string = BUSINESS_TIMEZONE,
): string {
  const dateMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date.trim())
  const timeMatch = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(time.trim())
  if (!dateMatch || !timeMatch) {
    return ''
  }
  const year = Number.parseInt(dateMatch[1], 10)
  const month = Number.parseInt(dateMatch[2], 10)
  const day = Number.parseInt(dateMatch[3], 10)
  const hour = Number.parseInt(timeMatch[1], 10)
  const minute = Number.parseInt(timeMatch[2], 10)
  const second = Number.parseInt(timeMatch[3] ?? '0', 10)
  const wanted = Date.UTC(year, month - 1, day, hour, minute, second)
  let guess = wanted
  for (let index = 0; index < 3; index += 1) {
    const parts = partsInTimeZone(new Date(guess), timeZone)
    const asUtc = Date.UTC(
      Number.parseInt(parts.year, 10),
      Number.parseInt(parts.month, 10) - 1,
      Number.parseInt(parts.day, 10),
      Number.parseInt(parts.hour, 10),
      Number.parseInt(parts.minute, 10),
      Number.parseInt(parts.second, 10),
    )
    const delta = wanted - asUtc
    if (delta === 0) {
      break
    }
    guess += delta
  }
  return new Date(guess).toISOString()
}

export function splitIsoToCivil(
  iso: string,
  timeZone: string = BUSINESS_TIMEZONE,
): { date: string; time: string } {
  if (!iso.trim()) {
    return { date: '', time: '' }
  }
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) {
    return { date: '', time: '' }
  }
  const parts = partsInTimeZone(parsed, timeZone)
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    time: `${parts.hour}:${parts.minute}`,
  }
}

export function todayCivilDate(timeZone: string = BUSINESS_TIMEZONE, now: Date = new Date()): string {
  const parts = partsInTimeZone(now, timeZone)
  return `${parts.year}-${parts.month}-${parts.day}`
}

export function addCivilDays(date: string, days: number): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date.trim())
  if (!match) {
    return date
  }
  const utc = Date.UTC(
    Number.parseInt(match[1], 10),
    Number.parseInt(match[2], 10) - 1,
    Number.parseInt(match[3], 10),
  )
  const next = new Date(utc)
  next.setUTCDate(next.getUTCDate() + days)
  return next.toISOString().slice(0, 10)
}

export function startOfMondayWeek(date: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date.trim())
  if (!match) {
    return date
  }
  const weekday = new Date(
    Date.UTC(
      Number.parseInt(match[1], 10),
      Number.parseInt(match[2], 10) - 1,
      Number.parseInt(match[3], 10),
    ),
  ).getUTCDay()
  const offset = weekday === 0 ? -6 : 1 - weekday
  return addCivilDays(date, offset)
}

export function formatCivilDateFr(date: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date.trim())
  if (!match) {
    return date
  }
  return `${match[3]}/${match[2]}/${match[1]}`
}

export function civilMinutesFromMidnight(
  iso: string,
  timeZone: string = BUSINESS_TIMEZONE,
): number | null {
  const { date, time } = splitIsoToCivil(iso, timeZone)
  if (!date || !time) {
    return null
  }
  const [hours, minutes] = time.split(':').map((part) => Number.parseInt(part, 10))
  if (Number.isNaN(hours) || Number.isNaN(minutes)) {
    return null
  }
  return hours * 60 + minutes
}
