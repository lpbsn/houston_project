import { describe, expect, it } from 'vitest'

import {
  clampWeekStartIndex,
  COMPACT_WEEK_VISIBLE_DAYS,
  initialWeekStartIndex,
  shiftWeekStartIndex,
  sliceVisibleWeekDays,
  weekVisibleDayCount,
} from './execution-calendar-visible-days'

const WEEK = [
  '2026-09-07',
  '2026-09-08',
  '2026-09-09',
  '2026-09-10',
  '2026-09-11',
  '2026-09-12',
  '2026-09-13',
]

describe('execution-calendar-visible-days', () => {
  it('uses 3 days under lg and the full week at lg', () => {
    expect(COMPACT_WEEK_VISIBLE_DAYS).toBe(3)
    expect(weekVisibleDayCount(false, 7)).toBe(3)
    expect(weekVisibleDayCount(true, 7)).toBe(7)
  })

  it('clamps the compact start to 0..4 for a 7-day week', () => {
    expect(clampWeekStartIndex(-2, 7, 3)).toBe(0)
    expect(clampWeekStartIndex(0, 7, 3)).toBe(0)
    expect(clampWeekStartIndex(4, 7, 3)).toBe(4)
    expect(clampWeekStartIndex(9, 7, 3)).toBe(4)
  })

  it('centers today in the 3-day window and clamps at the ends', () => {
    expect(initialWeekStartIndex({ days: WEEK, today: '2026-09-07', visibleCount: 3 })).toBe(0)
    expect(initialWeekStartIndex({ days: WEEK, today: '2026-09-08', visibleCount: 3 })).toBe(0)
    expect(initialWeekStartIndex({ days: WEEK, today: '2026-09-09', visibleCount: 3 })).toBe(1)
    expect(initialWeekStartIndex({ days: WEEK, today: '2026-09-10', visibleCount: 3 })).toBe(2)
    expect(initialWeekStartIndex({ days: WEEK, today: '2026-09-11', visibleCount: 3 })).toBe(3)
    expect(initialWeekStartIndex({ days: WEEK, today: '2026-09-12', visibleCount: 3 })).toBe(4)
    expect(initialWeekStartIndex({ days: WEEK, today: '2026-09-13', visibleCount: 3 })).toBe(4)
  })

  it('starts at Monday when today is outside the loaded week', () => {
    expect(initialWeekStartIndex({ days: WEEK, today: '2026-09-21', visibleCount: 3 })).toBe(0)
  })

  it('shifts the window by one day and does not wrap', () => {
    expect(shiftWeekStartIndex(0, 1, 7, 3)).toBe(1)
    expect(sliceVisibleWeekDays(WEEK, 0, 3)).toEqual(['2026-09-07', '2026-09-08', '2026-09-09'])
    expect(sliceVisibleWeekDays(WEEK, 1, 3)).toEqual(['2026-09-08', '2026-09-09', '2026-09-10'])
    expect(shiftWeekStartIndex(1, -1, 7, 3)).toBe(0)
    expect(shiftWeekStartIndex(0, -1, 7, 3)).toBe(0)
    expect(shiftWeekStartIndex(4, 1, 7, 3)).toBe(4)
  })

  it('returns the full week when seven days are visible', () => {
    expect(initialWeekStartIndex({ days: WEEK, today: '2026-09-10', visibleCount: 7 })).toBe(0)
    expect(clampWeekStartIndex(3, 7, 7)).toBe(0)
    expect(sliceVisibleWeekDays(WEEK, 0, 7)).toEqual(WEEK)
  })
})
