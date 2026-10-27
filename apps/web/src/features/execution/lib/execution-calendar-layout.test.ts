import { describe, expect, it } from 'vitest'
import { addCivilDays, combineCivilDateTimeToIso } from '@/lib/business-timezone'
import type { ActionPlanExecutionFeedItem } from '@/features/action-plans/types'
import {
  buildCalendarSpans,
  buildDesktopDayLayout,
  buildDesktopMonthRow,
  buildDesktopMonthRowsFromPlaced,
  buildDesktopWeekLayout,
  executionCalendarCategory,
  executionCalendarDateRange,
  placeCalendarItems,
} from './execution-calendar-layout'

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

  it('classifies two civil dates as multi-day, including a span under 24h and a one-second midnight crossing', () => {
    const overnight = item('short', civil('2026-10-13', '23:30'), civil('2026-10-14', '00:30'))
    expect(executionCalendarCategory(overnight)).toBe('multi_day')
    const exactMidnight = item('exact', civil('2026-10-13', '14:00'), civil('2026-10-14', '00:00:00'))
    const afterMidnight = item('after', civil('2026-10-13', '14:00'), civil('2026-10-14', '00:00:30'))
    expect(executionCalendarCategory(exactMidnight)).toBe('timed')
    expect(executionCalendarCategory(afterMidnight)).toBe('multi_day')
    expect(executionCalendarCategory(item('day', civil('2026-10-13', '00:00'), civil('2026-10-13', '23:59'), true))).toBe('all_day')
    expect(executionCalendarCategory(item('span', civil('2026-10-13', '00:00'), civil('2026-10-15', '00:00'), true))).toBe('multi_day')
  })

  it('keeps a multi-day execution on the band when only one day of it is visible', () => {
    const plan = item('long', civil('2026-10-13', '14:00'), civil('2026-10-16', '10:00'))
    const layout = buildDesktopWeekLayout([plan], ['2026-10-14'])
    expect(executionCalendarCategory(plan)).toBe('multi_day')
    expect(layout.bands).toHaveLength(1)
    expect(layout.columns[0]?.items).toEqual([])
  })

  it('puts single-day executions in the week column, sorted by start then id, without a lane', () => {
    const later = item('b', civil('2026-10-13', '15:00'), civil('2026-10-13', '16:00'))
    const earlier = item('a', civil('2026-10-13', '09:00'), civil('2026-10-13', '10:00'))
    const sameStart = item('c', civil('2026-10-13', '09:00'), civil('2026-10-13', '09:30'))
    const allDay = item('d', civil('2026-10-13', '00:00'), civil('2026-10-13', '23:59'), true)
    const layout = buildDesktopWeekLayout([later, sameStart, earlier, allDay], days)
    expect(layout.bands).toEqual([])
    expect(layout.columns[1]?.items.map((entry) => entry.id)).toEqual(['d', 'a', 'c', 'b'])
  })

  it('keeps three continuous month bands and counts a discarded band on every occupied day', () => {
    const plans = [
      item('a', civil('2026-10-12', '08:00'), civil('2026-10-18', '18:00')),
      item('b', civil('2026-10-12', '08:00'), civil('2026-10-18', '18:00')),
      item('c', civil('2026-10-12', '08:00'), civil('2026-10-18', '18:00')),
      item('d', civil('2026-10-12', '08:00'), civil('2026-10-16', '18:00')),
      item('s1', civil('2026-10-12', '09:00'), civil('2026-10-12', '10:00')),
      item('s2', civil('2026-10-12', '11:00'), civil('2026-10-12', '12:00')),
      item('s3', civil('2026-10-12', '13:00'), civil('2026-10-12', '14:00')),
    ]
    const row = buildDesktopMonthRow(plans, days)
    expect(row.bands.map((span) => [span.item.id, span.startColumn, span.endColumn, span.lane])).toEqual([
      ['a', 0, 6, 0],
      ['b', 0, 6, 1],
      ['c', 0, 6, 2],
    ])
    expect(row.days[0]).toMatchObject({
      singles: [expect.objectContaining({ item: expect.objectContaining({ id: 's1' }) }), expect.objectContaining({ item: expect.objectContaining({ id: 's2' }) })],
      overflowCount: 2,
    })
    expect(row.days[4]?.overflowCount).toBe(1)
    expect(row.days[5]?.overflowCount).toBe(0)
    expect(row.days.map((cell) => cell.overflowCount)).toEqual([2, 1, 1, 1, 1, 0, 0])
  })

  it('shows two single-day executions before the overflow count', () => {
    const plans = ['s1', 's2', 's3', 's4'].map((id, index) =>
      item(id, civil('2026-10-13', `${9 + index}:00`), civil('2026-10-13', `${10 + index}:00`)),
    )
    const monday = buildDesktopMonthRow(plans, days).days[1]
    expect(monday?.singles.map((span) => span.item.id)).toEqual(['s1', 's2'])
    expect(monday?.overflowCount).toBe(2)
  })

  it('keeps the same month rows when the civil interval is placed once', () => {
    const plans = [
      item('a', civil('2026-10-12', '08:00'), civil('2026-10-20', '18:00')),
      item('s1', civil('2026-10-13', '09:00'), civil('2026-10-13', '10:00')),
    ]
    const twoWeeks = [...days, ...days.map((day) => addCivilDays(day, 7))]
    expect(buildDesktopMonthRowsFromPlaced(placeCalendarItems(plans), twoWeeks)).toEqual([
      buildDesktopMonthRow(plans, twoWeeks.slice(0, 7)),
      buildDesktopMonthRow(plans, twoWeeks.slice(7)),
    ])
  })

  it('bounds a very long plan to the visible month row', () => {
    const row = buildDesktopMonthRow([item('century', '2000-01-01T12:00:00Z', '2099-12-31T12:00:00Z', true)], days)
    expect(row.bands).toHaveLength(1)
    expect(row.bands[0]).toMatchObject({ startColumn: 0, endColumn: 6 })
    expect(row.days.every((cell) => cell.overflowCount === 0)).toBe(true)
  })

  it('groups a mixed day and leaves an empty day without groups', () => {
    const plans = [
      item('timed', civil('2026-10-13', '09:00'), civil('2026-10-13', '10:00')),
      item('all', civil('2026-10-13', '00:00'), civil('2026-10-13', '23:59'), true),
      item('multi', civil('2026-10-12', '18:00'), civil('2026-10-14', '09:00')),
    ]
    const mixed = buildDesktopDayLayout(plans, '2026-10-13')
    expect(mixed.count).toBe(3)
    expect(mixed.groups.map((group) => group.category)).toEqual(['multi_day', 'all_day', 'timed'])
    expect(buildDesktopDayLayout(plans, '2026-10-18')).toEqual({ count: 0, groups: [] })
  })
})
