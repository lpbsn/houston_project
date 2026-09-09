import { describe, expect, it } from 'vitest'

import { resolveCalendarWindow, shiftCalendarAnchor } from './execution-calendar-window'

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
})
