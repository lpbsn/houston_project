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

/** One segment per execution and visible row, with deterministic non-overlapping lanes. */
export function buildCalendarSpans(
  items: ActionPlanExecutionFeedItem[],
  days: string[],
  timeZone: string = BUSINESS_TIMEZONE,
) {
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
