import { describe, expect, it } from 'vitest'

import {
  buildDashboardHref,
  DEFAULT_DASHBOARD_PERIOD_DAYS,
  parseDashboardPeriodDays,
} from '@/features/analytics/lib/dashboard-url-state'

describe('dashboard URL period', () => {
  it('defaults to 7 days', () => {
    expect(parseDashboardPeriodDays('')).toBe(DEFAULT_DASHBOARD_PERIOD_DAYS)
    expect(parseDashboardPeriodDays('?foo=1')).toBe(7)
  })

  it('parses allowed presets', () => {
    expect(parseDashboardPeriodDays('?period=15d')).toBe(15)
    expect(parseDashboardPeriodDays('?period=90d')).toBe(90)
  })

  it('rejects unknown presets', () => {
    expect(parseDashboardPeriodDays('?period=14d')).toBe(7)
    expect(parseDashboardPeriodDays('?period=7')).toBe(7)
  })

  it('writes the preset in the href', () => {
    expect(buildDashboardHref('/cross', 7)).toBe('/cross?period=7d')
    expect(buildDashboardHref('/e/abc', 30)).toBe('/e/abc?period=30d')
  })
})
