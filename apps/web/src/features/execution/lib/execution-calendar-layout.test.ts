import { describe, expect, it } from 'vitest'
import { combineCivilDateTimeToIso } from '@/lib/business-timezone'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import { buildCalendarSpans, executionCalendarDateRange } from './execution-calendar-layout'

function item(id: string, start: string | null, end: string | null, allDay = false) {
  return { id, start_at: start, end_at: end, all_day: allDay } as ActionPlanExecutionFeedItem
}
const civil = combineCivilDateTimeToIso
const days = ['2026-10-12', '2026-10-13', '2026-10-14', '2026-10-15', '2026-10-16', '2026-10-17', '2026-10-18']

describe('date-only execution calendar', () => {
  it('creates a single Tuesday–Friday band from timed or all-day plans without mutating dates', () => {
    for (const allDay of [false, true]) {
      const plan = item('a', civil('2026-10-13', '14:30'), civil('2026-10-16', '10:00'), allDay)
      const original = { ...plan }
      const spans = buildCalendarSpans([plan], days)
      expect(spans).toHaveLength(1)
      expect(spans[0]).toMatchObject({ startColumn: 1, endColumn: 4, lane: 0, continuesBefore: false, continuesAfter: false })
      expect(plan).toEqual(original)
    }
  })

  it('stacks overlapping ranges and reuses a lane only after its last day', () => {
    const plans = [item('a', civil('2026-10-12', '08:00'), civil('2026-10-14', '10:00')),
      item('b', civil('2026-10-14', '12:00'), civil('2026-10-16', '12:00')),
      item('c', civil('2026-10-15', '08:00'), civil('2026-10-15', '09:00'))]
    const spans = buildCalendarSpans(plans, days)
    expect(spans.map(s => [s.item.id, s.lane])).toEqual([['a', 0], ['b', 1], ['c', 0]])
    expect(buildCalendarSpans([...plans].reverse(), days)).toEqual(spans)
  })

  it('clips at both edges and marks continuation without duplicating a plan per day', () => {
    const spans = buildCalendarSpans([item('a', civil('2026-10-10', '14:00'), civil('2026-10-21', '15:00'))], days)
    expect(spans).toHaveLength(1)
    expect(spans[0]).toMatchObject({ startColumn: 0, endColumn: 6, continuesBefore: true, continuesAfter: true })
  })

  it('uses the establishment timezone, not the browser timezone', () => {
    const plan = item('a', '2026-10-12T23:30:00Z', '2026-10-13T23:30:00Z')
    expect(executionCalendarDateRange(plan, 'Europe/Paris')).toEqual({ start: '2026-10-13', end: '2026-10-14' })
    expect(executionCalendarDateRange(plan, 'UTC')).toEqual({ start: '2026-10-12', end: '2026-10-13' })
  })

  it('preserves exclusive midnight for timed plans and inclusive dates for all-day plans', () => {
    const plan = item('a', civil('2026-10-12', '14:00'), civil('2026-10-14', '00:00'))
    expect(executionCalendarDateRange(plan)?.end).toBe('2026-10-13')
    expect(executionCalendarDateRange({ ...plan, all_day: true })?.end).toBe('2026-10-14')
    expect(executionCalendarDateRange({ ...plan, end_at: '2026-10-13T22:00:30Z' })?.end).toBe('2026-10-14')
  })

  it('does not enumerate years of civil days for long plans', () => {
    const spans = buildCalendarSpans([item('a', '2000-01-01T12:00:00Z', '2099-12-31T12:00:00Z', true)], days)
    expect(spans).toHaveLength(1)
    expect(spans[0].endColumn).toBe(6)
  })

  it('keeps an open-ended plan on its start date and excludes unplanned or out-of-window plans', () => {
    const open = item('open', civil('2026-10-13', '14:00'), null)
    expect(executionCalendarDateRange(open)).toEqual({ start: '2026-10-13', end: '2026-10-13' })
    expect(buildCalendarSpans([open, item('unplanned', null, null), item('past', civil('2026-10-01', '14:00'), null)], days)).toHaveLength(1)
    expect(buildCalendarSpans([open], [])).toEqual([])
  })

  it('handles a daylight-saving week using civil dates', () => {
    const plan = item('dst', civil('2026-10-24', '14:00'), civil('2026-10-26', '15:00'))
    expect(buildCalendarSpans([plan], ['2026-10-24', '2026-10-25', '2026-10-26'])[0]).toMatchObject({ startColumn: 0, endColumn: 2 })
  })
})
