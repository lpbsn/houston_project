import { describe, expect, it } from 'vitest'

import {
  calendarAnchorToday,
  formatCalendarPeriodLabel,
  formatDesktopCalendarPeriodLabel,
  rememberScopedCalendarTimezone,
  resolveCalendarWindow,
  resolveScopedCalendarTimezone,
  shiftCalendarAnchor,
} from './execution-calendar-window'

describe('execution-calendar-window', () => {
  it('uses a Monday-start week including the requested day', () => {
    const window = resolveCalendarWindow('week', '2026-09-09')
    expect(window.from).toBe('2026-09-07')
    expect(window.to).toBe('2026-09-13')
    expect(window.days).toHaveLength(7)
  })

  it('includes adjacent days for the month grid', () => {
    const window = resolveCalendarWindow('month', '2026-09-15')
    expect(window.from <= '2026-09-01').toBe(true)
    expect(window.to >= '2026-09-30').toBe(true)
    expect(window.days.length % 7).toBe(0)
  })

  it('shifts month anchors to the first of the month', () => {
    expect(shiftCalendarAnchor('month', '2026-09-15', 1)).toBe('2026-10-01')
    expect(shiftCalendarAnchor('month', '2026-09-15', -1)).toBe('2026-08-01')
  })

  it('anchors today in the requested timezone', () => {
    const now = new Date('2026-09-08T22:30:00.000Z')
    expect(calendarAnchorToday('UTC', now)).toBe('2026-09-08')
    expect(calendarAnchorToday('Europe/Paris', now)).toBe('2026-09-09')
  })

  it('keeps a known timezone across a missing payload for the same scope', () => {
    const remembered = rememberScopedCalendarTimezone(null, 'establishment:est-1', 'UTC')
    const duringTransition = rememberScopedCalendarTimezone(
      remembered,
      'establishment:est-1',
      undefined,
    )
    expect(resolveScopedCalendarTimezone(duringTransition, undefined)).toBe('UTC')
  })

  it('formats the long desktop period without changing the mobile week label', () => {
    const day = resolveCalendarWindow('day', '2026-10-12')
    expect(formatDesktopCalendarPeriodLabel('day', day, '2026-10-12')).toBe('lundi 12 octobre 2026')
    const week = resolveCalendarWindow('week', '2026-10-14')
    expect(formatDesktopCalendarPeriodLabel('week', week, '2026-10-14')).toBe('12 – 18 octobre 2026')
    const crossing = resolveCalendarWindow('week', '2026-10-01')
    expect(formatDesktopCalendarPeriodLabel('week', crossing, '2026-10-01')).toBe(
      '28 septembre – 4 octobre 2026',
    )
    const month = resolveCalendarWindow('month', '2026-10-14')
    expect(formatDesktopCalendarPeriodLabel('month', month, '2026-10-14')).toBe('octobre 2026')
    expect(formatCalendarPeriodLabel('week', week, '2026-10-14')).not.toBe('12 – 18 octobre 2026')
  })

  it('forgets a known timezone after an establishment or source change', () => {
    const remembered = rememberScopedCalendarTimezone(null, 'establishment:est-1', 'UTC')
    expect(
      rememberScopedCalendarTimezone(remembered, 'establishment:est-2', undefined),
    ).toBeNull()
    expect(rememberScopedCalendarTimezone(remembered, 'cross', undefined)).toBeNull()
    expect(resolveScopedCalendarTimezone(null, undefined)).toBe('Europe/Paris')
  })
})
