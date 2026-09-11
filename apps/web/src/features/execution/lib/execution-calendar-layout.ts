import {
  addCivilDays,
  BUSINESS_TIMEZONE,
  civilMinutesFromMidnight,
  splitIsoToCivil,
} from '@/lib/business-timezone'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

const DAY_MINUTES = 24 * 60
const OPEN_ENDED_MINUTES = 60

type TimedCalendarBlock = {
  item: ActionPlanExecutionFeedItem
  startMin: number
  endMin: number
  column: number
  columnCount: number
}

export function isExecutionAllDay(item: Pick<ActionPlanExecutionFeedItem, 'all_day'>): boolean {
  return item.all_day === true
}

function civilDatesInclusive(from: string, to: string): string[] {
  if (to < from) {
    return []
  }
  const dates: string[] = []
  let cursor = from
  while (cursor <= to) {
    dates.push(cursor)
    cursor = addCivilDays(cursor, 1)
  }
  return dates
}

type CivilDayCoverage =
  | { kind: 'none' }
  | { kind: 'full_day' }
  | { kind: 'partial'; startMin: number; endMin: number }

export function allDayDatesForItem(
  item: ActionPlanExecutionFeedItem,
  timeZone: string = BUSINESS_TIMEZONE,
): string[] {
  const start = splitIsoToCivil(item.start_at ?? '', timeZone).date
  if (!start) {
    return []
  }
  const end = splitIsoToCivil(item.end_at ?? '', timeZone).date || start
  return civilDatesInclusive(start, end)
}

function openEndedCoverageOnDay(
  item: ActionPlanExecutionFeedItem,
  day: string,
  timeZone: string,
): CivilDayCoverage {
  const startDate = splitIsoToCivil(item.start_at ?? '', timeZone).date
  if (!startDate || day !== startDate) {
    return { kind: 'none' }
  }
  const startMin = civilMinutesFromMidnight(item.start_at ?? '', timeZone) ?? 0
  let endMin = Math.min(DAY_MINUTES, startMin + OPEN_ENDED_MINUTES)
  if (endMin <= startMin) {
    endMin = Math.min(DAY_MINUTES, startMin + 15)
  }
  return { kind: 'partial', startMin, endMin }
}

export function civilCoverageOnDay(
  item: ActionPlanExecutionFeedItem,
  day: string,
  timeZone: string = BUSINESS_TIMEZONE,
): CivilDayCoverage {
  if (isExecutionAllDay(item) || !item.start_at) {
    return { kind: 'none' }
  }
  if (!item.end_at) {
    return openEndedCoverageOnDay(item, day, timeZone)
  }

  const startDate = splitIsoToCivil(item.start_at, timeZone).date
  const endDate = splitIsoToCivil(item.end_at, timeZone).date
  if (!startDate || !endDate || day < startDate || day > endDate) {
    return { kind: 'none' }
  }

  const intersectStart =
    day === startDate ? (civilMinutesFromMidnight(item.start_at, timeZone) ?? 0) : 0
  const intersectEnd =
    day === endDate ? (civilMinutesFromMidnight(item.end_at, timeZone) ?? 0) : DAY_MINUTES
  if (intersectEnd <= intersectStart) {
    return { kind: 'none' }
  }
  if (intersectStart === 0 && intersectEnd === DAY_MINUTES) {
    return { kind: 'full_day' }
  }
  return { kind: 'partial', startMin: intersectStart, endMin: intersectEnd }
}

export function timedIntervalOnDay(
  item: ActionPlanExecutionFeedItem,
  day: string,
  timeZone: string = BUSINESS_TIMEZONE,
): { startMin: number; endMin: number } | null {
  const coverage = civilCoverageOnDay(item, day, timeZone)
  if (coverage.kind !== 'partial') {
    return null
  }
  return { startMin: coverage.startMin, endMin: coverage.endMin }
}

export function occupiesAllDayLane(
  item: ActionPlanExecutionFeedItem,
  day: string,
  timeZone: string = BUSINESS_TIMEZONE,
): boolean {
  if (isExecutionAllDay(item)) {
    return allDayDatesForItem(item, timeZone).includes(day)
  }
  return civilCoverageOnDay(item, day, timeZone).kind === 'full_day'
}

export function occupiesMonthCell(
  item: ActionPlanExecutionFeedItem,
  day: string,
  timeZone: string = BUSINESS_TIMEZONE,
): boolean {
  if (isExecutionAllDay(item)) {
    return allDayDatesForItem(item, timeZone).includes(day)
  }
  return civilCoverageOnDay(item, day, timeZone).kind !== 'none'
}

export function isTimedDayLaneContinuation(
  item: ActionPlanExecutionFeedItem,
  day: string,
  timeZone: string = BUSINESS_TIMEZONE,
): boolean {
  if (isExecutionAllDay(item) || civilCoverageOnDay(item, day, timeZone).kind !== 'full_day') {
    return false
  }
  const startDate = splitIsoToCivil(item.start_at ?? '', timeZone).date
  return Boolean(startDate && startDate < day)
}

export function splitOverlappingColumns(
  blocks: Array<{ startMin: number; endMin: number; item: ActionPlanExecutionFeedItem }>,
): TimedCalendarBlock[] {
  const sorted = [...blocks].sort((left, right) => {
    if (left.startMin !== right.startMin) {
      return left.startMin - right.startMin
    }
    return right.endMin - left.endMin
  })
  const columnEnds: number[] = []
  const placed: Array<(typeof sorted)[number] & { column: number }> = []

  for (const block of sorted) {
    let column = columnEnds.findIndex((end) => end <= block.startMin)
    if (column < 0) {
      column = columnEnds.length
      columnEnds.push(block.endMin)
    } else {
      columnEnds[column] = block.endMin
    }
    placed.push({ ...block, column })
  }

  const overlappingCounts = placed.map((block) => {
    const overlapping = placed.filter(
      (candidate) => candidate.startMin < block.endMin && candidate.endMin > block.startMin,
    )
    const columnCount = overlapping.reduce((max, candidate) => Math.max(max, candidate.column + 1), 1)
    return { ...block, columnCount }
  })

  return overlappingCounts
}
