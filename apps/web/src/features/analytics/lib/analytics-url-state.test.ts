import { describe, expect, it } from 'vitest'

import {
  buildAnalyticsPath,
  buildAnalyticsReturnPath,
  buildAnalyticsSearchParams,
  parseAnalyticsUrlState,
} from '@/features/analytics/lib/analytics-url-state'

const NOW = new Date('2026-08-12T10:30:00.000Z')
const ORG_ID = '11111111-1111-4111-8111-111111111111'

describe('analytics URL state', () => {
  it('uses a deterministic rolling 30 day period when the query is empty', () => {
    expect(parseAnalyticsUrlState('', { now: NOW })).toEqual({
      periodStart: '2026-07-13T10:30:00.000Z',
      periodEnd: '2026-08-12T10:30:00.000Z',
      organizationId: null,
    })
  })

  it('keeps a valid timezone-aware period and organization scope', () => {
    expect(
      parseAnalyticsUrlState(
        `?period_start=2026-07-01T00:00:00%2B02:00&period_end=2026-08-01T00:00:00Z&organization_id=${ORG_ID}`,
        { now: NOW },
      ),
    ).toEqual({
      periodStart: '2026-06-30T22:00:00.000Z',
      periodEnd: '2026-08-01T00:00:00.000Z',
      organizationId: ORG_ID,
    })
  })

  it.each([
    ['naive period', '?period_start=2026-07-01T00:00:00&period_end=2026-08-01T00:00:00Z'],
    ['invalid period', '?period_start=2026-13-01T00:00:00Z&period_end=2026-08-01T00:00:00Z'],
    ['partial period', '?period_start=2026-07-01T00:00:00Z'],
    ['inverted period', '?period_start=2026-08-01T00:00:00Z&period_end=2026-07-01T00:00:00Z'],
  ])('falls back to the default period for %s', (_label, search) => {
    expect(parseAnalyticsUrlState(search, { now: NOW })).toMatchObject({
      periodStart: '2026-07-13T10:30:00.000Z',
      periodEnd: '2026-08-12T10:30:00.000Z',
    })
  })

  it('ignores invalid organization IDs and establishment IDs in v1', () => {
    expect(
      parseAnalyticsUrlState(
        `?organization_id=not-a-uuid&establishment_id=22222222-2222-4222-8222-222222222222`,
        { now: NOW },
      ),
    ).toEqual({
      periodStart: '2026-07-13T10:30:00.000Z',
      periodEnd: '2026-08-12T10:30:00.000Z',
      organizationId: null,
    })
  })

  it('builds stable search params without establishment_id', () => {
    const params = buildAnalyticsSearchParams({
      periodStart: '2026-07-01T00:00:00.000Z',
      periodEnd: '2026-08-01T00:00:00.000Z',
      organizationId: ORG_ID,
    })

    expect(params.get('period_start')).toBe('2026-07-01T00:00:00.000Z')
    expect(params.get('period_end')).toBe('2026-08-01T00:00:00.000Z')
    expect(params.get('organization_id')).toBe(ORG_ID)
    expect(params.has('establishment_id')).toBe(false)
  })

  it('builds analytics and return paths from the resolved state', () => {
    const state = {
      periodStart: '2026-07-01T00:00:00.000Z',
      periodEnd: '2026-08-01T00:00:00.000Z',
      organizationId: null,
    }

    expect(buildAnalyticsPath(state)).toBe(
      '/analytics?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z',
    )
    expect(buildAnalyticsReturnPath(state)).toBe(buildAnalyticsPath(state))
  })
})
