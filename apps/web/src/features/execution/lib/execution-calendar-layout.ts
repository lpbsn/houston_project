import {
  addCivilDays,
  civilMinutesFromMidnight,
  splitIsoToCivil,
} from '@/lib/business-timezone'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

const DAY_MINUTES = 24 * 60
const OPEN_ENDED_MINUTES = 60

export type TimedCalendarBlock = {
  item: ActionPlanExecutionFeedItem
  startMin: number
  endMin: number
  column: number
  columnCount: number
}

export function isExecutionAllDay(item: Pick<ActionPlanExecutionFeedItem, 'all_day'>): boolean {
  return item.all_day === true
}

export function civilDatesInclusive(from: string, to: string): string[] {
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

export function allDayDatesForItem(item: ActionPlanExecutionFeedItem): string[] {
  const start = splitIsoToCivil(item.start_at ?? '').date
  if (!start) {
    return []
  }
  const end = splitIsoToCivil(item.end_at ?? '').date || start
  return civilDatesInclusive(start, end)
}

export function timedIntervalOnDay(
  item: ActionPlanExecutionFeedItem,
  day: string,
): { startMin: number; endMin: number } | null {
  if (isExecutionAllDay(item) || !item.start_at) {
    return null
  }
  const start = splitIsoToCivil(item.start_at)
  if (!start.date) {
    return null
  }
  const end = item.end_at ? splitIsoToCivil(item.end_at) : { date: start.date, time: '' }
  const endDate = end.date || start.date
  if (day < start.date || day > endDate) {
    return null
  }

  const startMin =
    day === start.date ? (civilMinutesFromMidnight(item.start_at) ?? 0) : 0
  let endMin = DAY_MINUTES
  if (!item.end_at) {
    endMin = Math.min(DAY_MINUTES, startMin + OPEN_ENDED_MINUTES)
  } else if (day === endDate) {
    endMin = civilMinutesFromMidnight(item.end_at) ?? DAY_MINUTES
  }
  if (endMin <= startMin) {
    endMin = Math.min(DAY_MINUTES, startMin + 15)
  }
  return { startMin, endMin }
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
