import { addCivilDays, BUSINESS_TIMEZONE, splitIsoToCivil } from '@/lib/business-timezone'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

/** Preserve the API's existing civil-day coverage; never rewrite persisted timestamps. */
export function executionCalendarDateRange(
  item: ActionPlanExecutionFeedItem,
  timeZone: string = BUSINESS_TIMEZONE,
): { start: string; end: string } | null {
  const start = splitIsoToCivil(item.start_at ?? '', timeZone).date
  if (!start) return null
  const endCivil = splitIsoToCivil(item.end_at ?? '', timeZone)
  let end = endCivil.date || start
  // Timed intervals ending at midnight do not occupy the following day.
  // All-day plans already use inclusive civil dates in this calendar.
  if (!item.all_day && item.end_at && endCivil.time === '00:00') {
    const instant = new Date(item.end_at)
    if (instant.getUTCSeconds() === 0 && instant.getUTCMilliseconds() === 0) {
      end = addCivilDays(end, -1)
    }
  }
  if (end < start) return null
  return { start, end }
}

export type CalendarSpan = {
  item: ActionPlanExecutionFeedItem
  startColumn: number
  endColumn: number
  startDate: string
  endDate: string
  continuesBefore: boolean
  continuesAfter: boolean
  lane: number
}

/** Two distinct civil dates are multi-day, including spans under 24h. */
export type ExecutionCalendarCategory = 'multi_day' | 'all_day' | 'timed'

export function executionCalendarCategory(
  item: ActionPlanExecutionFeedItem,
  timeZone: string = BUSINESS_TIMEZONE,
): ExecutionCalendarCategory | null {
  const range = executionCalendarDateRange(item, timeZone)
  if (!range) return null
  if (range.start !== range.end) return 'multi_day'
  if (item.all_day) return 'all_day'
  return 'timed'
}

export const DESKTOP_MONTH_VISIBLE_BANDS = 3
export const DESKTOP_MONTH_VISIBLE_SINGLES = 2

export type DesktopWeekLayout = {
  bands: CalendarSpan[]
  columns: Array<{ day: string; items: ActionPlanExecutionFeedItem[] }>
}

export type DesktopMonthDayCell = {
  day: string
  singles: CalendarSpan[]
  overflowCount: number
}

export type DesktopMonthRowLayout = {
  bands: CalendarSpan[]
  days: DesktopMonthDayCell[]
}

export type DesktopDayGroup = {
  category: ExecutionCalendarCategory
  items: ActionPlanExecutionFeedItem[]
}

export type DesktopDayLayout = {
  count: number
  groups: DesktopDayGroup[]
}

const DAY_GROUP_ORDER: ExecutionCalendarCategory[] = ['multi_day', 'all_day', 'timed']

function compareByStartThenId(
  a: ActionPlanExecutionFeedItem,
  b: ActionPlanExecutionFeedItem,
): number {
  const start = (a.start_at ?? '').localeCompare(b.start_at ?? '')
  if (start !== 0) return start
  return a.id.localeCompare(b.id)
}

function splitByCategory(
  items: ActionPlanExecutionFeedItem[],
  timeZone: string,
): { multiDay: ActionPlanExecutionFeedItem[]; singleDay: ActionPlanExecutionFeedItem[] } {
  const multiDay: ActionPlanExecutionFeedItem[] = []
  const singleDay: ActionPlanExecutionFeedItem[] = []
  for (const item of items) {
    const category = executionCalendarCategory(item, timeZone)
    if (category === 'multi_day') multiDay.push(item)
    else if (category != null) singleDay.push(item)
  }
  return { multiDay, singleDay }
}

/** Multi-day bands keep lanes. Other executions stay in their column, ordered by start then id. */
export function buildDesktopWeekLayout(
  items: ActionPlanExecutionFeedItem[],
  days: string[],
  timeZone: string = BUSINESS_TIMEZONE,
): DesktopWeekLayout {
  const { multiDay, singleDay } = splitByCategory(items, timeZone)
  return {
    bands: buildCalendarSpans(multiDay, days, timeZone),
    columns: days.map((day) => ({
      day,
      items: singleDay
        .filter((item) => {
          const range = executionCalendarDateRange(item, timeZone)
          return range != null && range.start <= day && range.end >= day
        })
        .sort(compareByStartThenId),
    })),
  }
}

/**
 * Keep the first three multi-day lanes across the whole row.
 * Each hidden execution counts once on every civil day it occupies.
 * Two single-day executions stay visible; the rest join that count.
 */
export function buildDesktopMonthRow(
  items: ActionPlanExecutionFeedItem[],
  days: string[],
  timeZone: string = BUSINESS_TIMEZONE,
): DesktopMonthRowLayout {
  const { multiDay, singleDay } = splitByCategory(items, timeZone)
  const spans = buildCalendarSpans(multiDay, days, timeZone)
  const hiddenBands = Array.from({ length: days.length }, () => 0)
  for (const span of spans) {
    if (span.lane < DESKTOP_MONTH_VISIBLE_BANDS) continue
    for (let column = span.startColumn; column <= span.endColumn; column += 1) {
      hiddenBands[column] += 1
    }
  }
  const singlesByDay: CalendarSpan[][] = days.map(() => [])
  for (const span of buildCalendarSpans(singleDay, days, timeZone)) {
    singlesByDay[span.startColumn]?.push(span)
  }
  return {
    bands: spans.filter((span) => span.lane < DESKTOP_MONTH_VISIBLE_BANDS),
    days: days.map((day, index) => {
      const singles = singlesByDay[index] ?? []
      const hiddenSingles = Math.max(0, singles.length - DESKTOP_MONTH_VISIBLE_SINGLES)
      return {
        day,
        singles: singles.slice(0, DESKTOP_MONTH_VISIBLE_SINGLES),
        overflowCount: (hiddenBands[index] ?? 0) + hiddenSingles,
      }
    }),
  }
}

/** Non-empty groups only, in multi-day, all-day, then timed order. */
export function buildDesktopDayLayout(
  items: ActionPlanExecutionFeedItem[],
  day: string,
  timeZone: string = BUSINESS_TIMEZONE,
): DesktopDayLayout {
  const present = items.flatMap((item) => {
    const range = executionCalendarDateRange(item, timeZone)
    const category = executionCalendarCategory(item, timeZone)
    if (!range || !category || day < range.start || day > range.end) return []
    return [{ item, category }]
  })
  return {
    count: present.length,
    groups: DAY_GROUP_ORDER.flatMap((category) => {
      const grouped = present
        .filter((entry) => entry.category === category)
        .map((entry) => entry.item)
        .sort(compareByStartThenId)
      return grouped.length > 0 ? [{ category, items: grouped }] : []
    }),
  }
}

/** One segment per execution and visible row, with deterministic non-overlapping lanes. */
export function buildCalendarSpans(
  items: ActionPlanExecutionFeedItem[],
  days: string[],
  timeZone: string = BUSINESS_TIMEZONE,
): CalendarSpan[] {
  if (days.length === 0) return []
  const candidates = items.flatMap((item) => {
    const range = executionCalendarDateRange(item, timeZone)
    if (!range) return []
    const startColumn = days.findIndex((day) => day >= range.start && day <= range.end)
    if (startColumn < 0) return []
    let endColumn = startColumn
    while (endColumn + 1 < days.length && days[endColumn + 1] <= range.end) endColumn++
    return [{
      item, startColumn, endColumn,
      startDate: range.start,
      endDate: range.end,
      continuesBefore: range.start < days[0],
      continuesAfter: range.end > days[days.length - 1],
    }]
  }).sort((a, b) => a.startDate.localeCompare(b.startDate) || b.endDate.localeCompare(a.endDate) || a.item.id.localeCompare(b.item.id))
  const laneEnds: number[] = []
  return candidates.map((candidate) => {
    let lane = laneEnds.findIndex((end) => end < candidate.startColumn)
    if (lane < 0) lane = laneEnds.length
    laneEnds[lane] = candidate.endColumn
    return { ...candidate, lane }
  })
}
