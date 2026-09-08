import { describe, expect, it } from 'vitest'

import { combineCivilDateTimeToIso } from '@/lib/business-timezone'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'

import {
  civilCoverageOnDay,
  isTimedDayLaneContinuation,
  occupiesAllDayLane,
  occupiesMonthCell,
  splitOverlappingColumns,
  timedIntervalOnDay,
} from './execution-calendar-layout'

function item(
  id: string,
  startAt: string | null,
  endAt: string | null,
  allDay = false,
): ActionPlanExecutionFeedItem {
  return {
    id,
    title: id,
    start_at: startAt,
    end_at: endAt,
    all_day: allDay,
  } as ActionPlanExecutionFeedItem
}

function civil(date: string, time: string): string {
  return combineCivilDateTimeToIso(date, time)
}

describe('execution-calendar-layout', () => {
  it('places overlapping timed events in adjacent columns', () => {
    const first = {
      item: item('a', '2026-09-08T08:00:00.000Z', '2026-09-08T10:00:00.000Z'),
      startMin: 60,
      endMin: 180,
    }
    const second = {
      item: item('b', '2026-09-08T09:00:00.000Z', '2026-09-08T11:00:00.000Z'),
      startMin: 120,
      endMin: 240,
    }
    const placed = splitOverlappingColumns([first, second])
    expect(placed).toHaveLength(2)
    expect(new Set(placed.map((block) => block.column)).size).toBe(2)
    expect(placed.every((block) => block.columnCount >= 2)).toBe(true)
  })

  it('keeps all-day events out of the timed grid', () => {
    expect(
      timedIntervalOnDay(
        item('all', '2026-09-08T22:00:00.000Z', '2026-09-09T21:59:59.000Z', true),
        '2026-09-08',
      ),
    ).toBeNull()
  })

  it('projects a timed span by civil coverage without inferring all_day', () => {
    const span = item('span', civil('2026-09-08', '14:00'), civil('2026-09-13', '15:00'))
    expect(span.all_day).toBe(false)
    expect(timedIntervalOnDay(span, '2026-09-08')).toEqual({ startMin: 14 * 60, endMin: 24 * 60 })
    expect(civilCoverageOnDay(span, '2026-09-09')).toEqual({ kind: 'full_day' })
    expect(civilCoverageOnDay(span, '2026-09-12')).toEqual({ kind: 'full_day' })
    expect(timedIntervalOnDay(span, '2026-09-09')).toBeNull()
    expect(timedIntervalOnDay(span, '2026-09-13')).toEqual({ startMin: 0, endMin: 15 * 60 })
    expect(occupiesAllDayLane(span, '2026-09-08')).toBe(false)
    expect(occupiesAllDayLane(span, '2026-09-10')).toBe(true)
    expect(occupiesMonthCell(span, '2026-09-10')).toBe(true)
    expect(occupiesMonthCell(span, '2026-09-08')).toBe(true)
  })

  it('puts a midnight-starting full first day in the day lane', () => {
    const span = item('midnight-start', civil('2026-09-08', '00:00'), civil('2026-09-13', '15:00'))
    expect(civilCoverageOnDay(span, '2026-09-08')).toEqual({ kind: 'full_day' })
    expect(timedIntervalOnDay(span, '2026-09-08')).toBeNull()
    expect(occupiesAllDayLane(span, '2026-09-08')).toBe(true)
    expect(isTimedDayLaneContinuation(span, '2026-09-08')).toBe(false)
    expect(isTimedDayLaneContinuation(span, '2026-09-09')).toBe(true)
  })

  it('drops a zero-length segment when end_at is exactly midnight', () => {
    const span = item('midnight-end', civil('2026-09-08', '14:00'), civil('2026-09-13', '00:00'))
    expect(civilCoverageOnDay(span, '2026-09-13')).toEqual({ kind: 'none' })
    expect(timedIntervalOnDay(span, '2026-09-13')).toBeNull()
    expect(occupiesAllDayLane(span, '2026-09-13')).toBe(false)
    expect(occupiesMonthCell(span, '2026-09-13')).toBe(false)
    expect(occupiesMonthCell(span, '2026-09-12')).toBe(true)
    expect(civilCoverageOnDay(span, '2026-09-12')).toEqual({ kind: 'full_day' })
  })

  it('keeps two consecutive partial days in the time grid', () => {
    const span = item('two-days', civil('2026-09-08', '14:00'), civil('2026-09-09', '15:00'))
    expect(timedIntervalOnDay(span, '2026-09-08')).toEqual({ startMin: 14 * 60, endMin: 24 * 60 })
    expect(timedIntervalOnDay(span, '2026-09-09')).toEqual({ startMin: 0, endMin: 15 * 60 })
    expect(occupiesAllDayLane(span, '2026-09-08')).toBe(false)
    expect(occupiesAllDayLane(span, '2026-09-09')).toBe(false)
  })

  it('keeps open-ended timed events as a 60-minute start-day block', () => {
    const open = item('open', civil('2026-09-08', '14:00'), null)
    expect(timedIntervalOnDay(open, '2026-09-08')).toEqual({ startMin: 14 * 60, endMin: 15 * 60 })
    expect(civilCoverageOnDay(open, '2026-09-09')).toEqual({ kind: 'none' })
    expect(occupiesMonthCell(open, '2026-09-08')).toBe(true)
  })
})
