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

function executionCalendarCategoryForRange(
  item: ActionPlanExecutionFeedItem,
  range: { start: string; end: string },
): ExecutionCalendarCategory {
  if (range.start !== range.end) return 'multi_day'
  if (item.all_day) return 'all_day'
  return 'timed'
}

export function executionCalendarCategory(
  item: ActionPlanExecutionFeedItem,
  timeZone: string = BUSINESS_TIMEZONE,
): ExecutionCalendarCategory | null {
  const range = executionCalendarDateRange(item, timeZone)
  if (!range) return null
  return executionCalendarCategoryForRange(item, range)
}

const DESKTOP_MONTH_VISIBLE_BANDS = 3
const DESKTOP_MONTH_VISIBLE_SINGLES = 2

type DesktopWeekLayout = {
  bands: CalendarSpan[]
  columns: Array<{ day: string; items: ActionPlanExecutionFeedItem[] }>
}

type DesktopMonthDayCell = {
  day: string
  singles: CalendarSpan[]
  overflowCount: number
}

export type DesktopMonthRowLayout = {
  bands: CalendarSpan[]
  days: DesktopMonthDayCell[]
}

type DesktopDayGroup = {
  category: ExecutionCalendarCategory
  items: ActionPlanExecutionFeedItem[]
}

type DesktopDayLayout = {
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

export type CalendarPlacement = {
  item: ActionPlanExecutionFeedItem
  start: string
  end: string
  category: ExecutionCalendarCategory
}

/** One civil interval per execution. Later views only compare those dates to the grid. */
export function placeCalendarItems(
  items: ActionPlanExecutionFeedItem[],
  timeZone: string = BUSINESS_TIMEZONE,
): CalendarPlacement[] {
  const placed: CalendarPlacement[] = []
  for (const item of items) {
    const range = executionCalendarDateRange(item, timeZone)
    if (!range) continue
    placed.push({
      item,
      start: range.start,
      end: range.end,
      category: executionCalendarCategoryForRange(item, range),
    })
  }
  return placed
}

function splitPlaced(placed: CalendarPlacement[]) {
  const multiDay: CalendarPlacement[] = []
  const singleDay: CalendarPlacement[] = []
  for (const placement of placed) {
    if (placement.category === 'multi_day') multiDay.push(placement)
    else singleDay.push(placement)
  }
  return { multiDay, singleDay }
}

/** One segment per execution and visible row, with deterministic non-overlapping lanes. */
export function buildCalendarSpansFromPlaced(
  placed: CalendarPlacement[],
  days: string[],
): CalendarSpan[] {
  if (days.length === 0) return []
  const candidates = placed.flatMap((placement) => {
    const startColumn = days.findIndex((day) => day >= placement.start && day <= placement.end)
    if (startColumn < 0) return []
    let endColumn = startColumn
    while (endColumn + 1 < days.length && days[endColumn + 1] <= placement.end) endColumn += 1
    return [{
      item: placement.item,
      startColumn,
      endColumn,
      startDate: placement.start,
      endDate: placement.end,
      continuesBefore: placement.start < days[0],
      continuesAfter: placement.end > days[days.length - 1],
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

export function buildCalendarSpans(
  items: ActionPlanExecutionFeedItem[],
  days: string[],
  timeZone: string = BUSINESS_TIMEZONE,
): CalendarSpan[] {
  return buildCalendarSpansFromPlaced(placeCalendarItems(items, timeZone), days)
}

/** Multi-day bands keep lanes. Other executions stay in their column, ordered by start then id. */
export function buildDesktopWeekLayoutFromPlaced(
  placed: CalendarPlacement[],
  days: string[],
): DesktopWeekLayout {
  const { multiDay, singleDay } = splitPlaced(placed)
  return {
    bands: buildCalendarSpansFromPlaced(multiDay, days),
    columns: days.map((day) => ({
      day,
      items: singleDay
        .filter((placement) => placement.start <= day && placement.end >= day)
        .sort((a, b) => compareByStartThenId(a.item, b.item))
        .map((placement) => placement.item),
    })),
  }
}

export function buildDesktopWeekLayout(
  items: ActionPlanExecutionFeedItem[],
  days: string[],
  timeZone: string = BUSINESS_TIMEZONE,
): DesktopWeekLayout {
  return buildDesktopWeekLayoutFromPlaced(placeCalendarItems(items, timeZone), days)
}

function monthRowFromPlaced(placed: CalendarPlacement[], days: string[]): DesktopMonthRowLayout {
  const { multiDay, singleDay } = splitPlaced(placed)
  const spans = buildCalendarSpansFromPlaced(multiDay, days)
  const hiddenBands = Array.from({ length: days.length }, () => 0)
  for (const span of spans) {
    if (span.lane < DESKTOP_MONTH_VISIBLE_BANDS) continue
    for (let column = span.startColumn; column <= span.endColumn; column += 1) {
      hiddenBands[column] += 1
    }
  }
  const singlesByDay: CalendarSpan[][] = days.map(() => [])
  for (const span of buildCalendarSpansFromPlaced(singleDay, days)) {
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

/**
 * Keep the first three multi-day lanes across the whole row.
 * Each hidden execution counts once on every civil day it occupies.
 * Two single-day executions stay visible; the rest join that count.
 */
export function buildDesktopMonthRowsFromPlaced(
  placed: CalendarPlacement[],
  days: string[],
): DesktopMonthRowLayout[] {
  const rows: DesktopMonthRowLayout[] = []
  for (let index = 0; index < days.length; index += 7) {
    rows.push(monthRowFromPlaced(placed, days.slice(index, index + 7)))
  }
  return rows
}

export function buildDesktopMonthRow(
  items: ActionPlanExecutionFeedItem[],
  days: string[],
  timeZone: string = BUSINESS_TIMEZONE,
): DesktopMonthRowLayout {
  return monthRowFromPlaced(placeCalendarItems(items, timeZone), days)
}

/** Non-empty groups only, in multi-day, all-day, then timed order. */
export function buildDesktopDayLayoutFromPlaced(
  placed: CalendarPlacement[],
  day: string,
): DesktopDayLayout {
  const present = placed.filter((placement) => day >= placement.start && day <= placement.end)
  return {
    count: present.length,
    groups: DAY_GROUP_ORDER.flatMap((category) => {
      const grouped = present
        .filter((placement) => placement.category === category)
        .map((placement) => placement.item)
        .sort(compareByStartThenId)
      return grouped.length > 0 ? [{ category, items: grouped }] : []
    }),
  }
}

export function buildDesktopDayLayout(
  items: ActionPlanExecutionFeedItem[],
  day: string,
  timeZone: string = BUSINESS_TIMEZONE,
): DesktopDayLayout {
  return buildDesktopDayLayoutFromPlaced(placeCalendarItems(items, timeZone), day)
}
