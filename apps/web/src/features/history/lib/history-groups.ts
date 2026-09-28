import { BUSINESS_TIMEZONE, todayCivilDate } from '@/lib/business-timezone'

export type HistoryDatedItem = {
  id: string
  terminal_at: string | null
}

export type HistoryGroup<T extends HistoryDatedItem> = {
  key: string
  label: string
  items: T[]
}

const UNKNOWN_KEY = 'unknown'

export function reconcileHistoryItems<T extends HistoryDatedItem>(items: T[]): T[] {
  const reconciled: T[] = []
  const indexById = new Map<string, number>()
  for (const item of items) {
    const existing = indexById.get(item.id)
    if (existing === undefined) {
      indexById.set(item.id, reconciled.length)
      reconciled.push(item)
    } else {
      reconciled[existing] = item
    }
  }
  return reconciled
}

function civilDateInParis(iso: string): string | null {
  const parsed = new Date(iso)
  if (Number.isNaN(parsed.getTime())) {
    return null
  }
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: BUSINESS_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(parsed)
  return parts
}

function formatCivilDayLabel(civilDate: string, today: string): string {
  if (civilDate === today) {
    return 'Aujourd’hui'
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(civilDate)
  if (!match) {
    return civilDate
  }
  const includeYear = civilDate.slice(0, 4) !== today.slice(0, 4)
  return new Intl.DateTimeFormat('fr-FR', {
    timeZone: 'UTC',
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    ...(includeYear ? { year: 'numeric' as const } : {}),
  }).format(
    new Date(
      Date.UTC(
        Number.parseInt(match[1], 10),
        Number.parseInt(match[2], 10) - 1,
        Number.parseInt(match[3], 10),
        12,
      ),
    ),
  )
}

export function groupHistoryItems<T extends HistoryDatedItem>(
  items: T[],
  now: Date = new Date(),
): HistoryGroup<T>[] {
  const today = todayCivilDate(BUSINESS_TIMEZONE, now)
  const groups: HistoryGroup<T>[] = []
  const indexByKey = new Map<string, number>()
  const undated: T[] = []

  for (const item of items) {
    const civilDate = item.terminal_at ? civilDateInParis(item.terminal_at) : null
    if (!civilDate) {
      undated.push(item)
      continue
    }
    const existing = indexByKey.get(civilDate)
    if (existing === undefined) {
      indexByKey.set(civilDate, groups.length)
      groups.push({
        key: civilDate,
        label: formatCivilDayLabel(civilDate, today),
        items: [item],
      })
    } else {
      groups[existing]!.items.push(item)
    }
  }

  if (undated.length > 0) {
    groups.push({ key: UNKNOWN_KEY, label: 'Date inconnue', items: undated })
  }
  return groups
}
