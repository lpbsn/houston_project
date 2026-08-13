import { describe, expect, it } from 'vitest'

import {
  buildAnalyticsPath,
  buildAnalyticsPatternDetailPath,
  buildAnalyticsReturnPath,
  buildAnalyticsSearchParams,
  buildAnalyticsSignalDetailPath,
  parseAnalyticsSignalReturnContext,
  parseAnalyticsUrlState,
} from '@/features/analytics/lib/analytics-url-state'

const NOW = new Date('2026-08-12T10:30:00.000Z')
const ORG_ID = '11111111-1111-4111-8111-111111111111'
const EST_ID = '22222222-2222-4222-8222-222222222222'
const BU_ID = '33333333-3333-4333-8333-333333333333'

const EMPTY_FILTERS = {
  establishmentIds: [],
  q: '',
  recurrence: 'all',
  responsibleBusinessUnitIds: [],
  responsibleBusinessUnitUnassigned: false,
  signalStatuses: [],
} as const

describe('analytics URL state', () => {
  it('uses a deterministic rolling 30 day period when the query is empty', () => {
    expect(parseAnalyticsUrlState('', { now: NOW })).toEqual({
      periodStart: '2026-07-13T10:30:00.000Z',
      periodEnd: '2026-08-12T10:30:00.000Z',
      organizationId: null,
      ...EMPTY_FILTERS,
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
      ...EMPTY_FILTERS,
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

  it('parses valid table filters and ignores unsupported establishment_id', () => {
    expect(
      parseAnalyticsUrlState(
        `?establishment_id=ignored&establishment_ids=${EST_ID}&q=+retard+&recurrence=recurrent&responsible_business_unit_ids=${BU_ID}&responsible_business_unit_unassigned=true&signal_statuses=open,canceled,archived`,
        { now: NOW },
      ),
    ).toMatchObject({
      establishmentIds: [EST_ID],
      q: 'retard',
      recurrence: 'recurrent',
      responsibleBusinessUnitIds: [BU_ID],
      responsibleBusinessUnitUnassigned: true,
      signalStatuses: ['archived', 'open'],
    })
  })

  it('ignores invalid organization IDs and invalid filter values', () => {
    expect(
      parseAnalyticsUrlState(
        `?organization_id=not-a-uuid&establishment_id=22222222-2222-4222-8222-222222222222`,
        { now: NOW },
      ),
    ).toEqual({
      periodStart: '2026-07-13T10:30:00.000Z',
      periodEnd: '2026-08-12T10:30:00.000Z',
      organizationId: null,
      ...EMPTY_FILTERS,
    })
  })

  it('builds stable search params without singular establishment_id', () => {
    const params = buildAnalyticsSearchParams({
      periodStart: '2026-07-01T00:00:00.000Z',
      periodEnd: '2026-08-01T00:00:00.000Z',
      organizationId: ORG_ID,
      establishmentIds: [EST_ID],
      q: 'froid',
      recurrence: 'non_recurrent',
      responsibleBusinessUnitIds: [BU_ID],
      responsibleBusinessUnitUnassigned: true,
      signalStatuses: ['open', 'resolved'],
    })

    expect(params.get('period_start')).toBe('2026-07-01T00:00:00.000Z')
    expect(params.get('period_end')).toBe('2026-08-01T00:00:00.000Z')
    expect(params.get('organization_id')).toBe(ORG_ID)
    expect(params.get('establishment_ids')).toBe(EST_ID)
    expect(params.get('q')).toBe('froid')
    expect(params.get('recurrence')).toBe('non_recurrent')
    expect(params.get('responsible_business_unit_ids')).toBe(BU_ID)
    expect(params.get('responsible_business_unit_unassigned')).toBe('true')
    expect(params.get('signal_statuses')).toBe('open,resolved')
    expect(params.has('establishment_id')).toBe(false)
  })

  it('builds analytics and return paths from the resolved state', () => {
    const state = {
      periodStart: '2026-07-01T00:00:00.000Z',
      periodEnd: '2026-08-01T00:00:00.000Z',
      organizationId: null,
      ...EMPTY_FILTERS,
    }

    expect(buildAnalyticsPath(state)).toBe(
      '/analytics?period_start=2026-07-01T00%3A00%3A00.000Z&period_end=2026-08-01T00%3A00%3A00.000Z',
    )
    expect(buildAnalyticsReturnPath(state)).toBe(buildAnalyticsPath(state))
  })

  it('builds pattern detail paths with the canonical analytics state', () => {
    const state = {
      periodStart: '2026-07-01T00:00:00.000Z',
      periodEnd: '2026-08-01T00:00:00.000Z',
      organizationId: ORG_ID,
      establishmentIds: [EST_ID],
      q: 'froid',
      recurrence: 'recurrent' as const,
      responsibleBusinessUnitIds: [BU_ID],
      responsibleBusinessUnitUnassigned: true,
      signalStatuses: ['open' as const],
    }

    const path = buildAnalyticsPatternDetailPath('pattern/with slash', state)
    const [pathname, search = ''] = path.split('?')
    const params = new URLSearchParams(search)

    expect(pathname).toBe('/analytics/patterns/pattern%2Fwith%20slash')
    expect(params.get('period_start')).toBe('2026-07-01T00:00:00.000Z')
    expect(params.get('period_end')).toBe('2026-08-01T00:00:00.000Z')
    expect(params.get('organization_id')).toBe(ORG_ID)
    expect(params.get('establishment_ids')).toBe(EST_ID)
    expect(params.get('q')).toBe('froid')
    expect(params.get('recurrence')).toBe('recurrent')
    expect(params.get('responsible_business_unit_ids')).toBe(BU_ID)
    expect(params.get('responsible_business_unit_unassigned')).toBe('true')
    expect(params.get('signal_statuses')).toBe('open')
    expect(params.has('return_path')).toBe(false)
    expect(params.has('establishment_id')).toBe(false)
  })

  it('builds and parses Signal detail paths with Analytics return context only', () => {
    const state = {
      periodStart: '2026-07-01T00:00:00.000Z',
      periodEnd: '2026-08-01T00:00:00.000Z',
      organizationId: ORG_ID,
      establishmentIds: [EST_ID],
      q: 'froid',
      recurrence: 'recurrent' as const,
      responsibleBusinessUnitIds: [BU_ID],
      responsibleBusinessUnitUnassigned: true,
      signalStatuses: ['open' as const],
    }

    const path = buildAnalyticsSignalDetailPath('signal/with slash', {
      patternId: '44444444-4444-4444-8444-444444444444',
      state,
    })
    const [pathname, search = ''] = path.split('?')
    const params = new URLSearchParams(search)

    expect(pathname).toBe('/signals/signal%2Fwith%20slash')
    expect(params.get('analytics_pattern_id')).toBe('44444444-4444-4444-8444-444444444444')
    expect(params.get('period_start')).toBe('2026-07-01T00:00:00.000Z')
    expect(params.get('period_end')).toBe('2026-08-01T00:00:00.000Z')
    expect(params.get('establishment_ids')).toBe(EST_ID)
    expect(params.get('q')).toBe('froid')
    expect(params.has('return_path')).toBe(false)
    expect(params.has('signal_establishment_id')).toBe(false)
    expect(params.has('establishment_id')).toBe(false)

    expect(parseAnalyticsSignalReturnContext(search, { now: NOW })).toEqual({
      patternId: '44444444-4444-4444-8444-444444444444',
      state,
    })
  })

  it('ignores invalid Analytics Signal return context', () => {
    expect(
      parseAnalyticsSignalReturnContext('?analytics_pattern_id=not-a-uuid', { now: NOW }),
    ).toBeNull()
  })
})
