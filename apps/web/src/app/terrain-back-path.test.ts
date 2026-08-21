import { describe, expect, it } from 'vitest'

import { resolveTerrainBackPath } from '@/app/terrain-back-path'
import { buildAnalyticsPatternDetailPath } from '@/features/analytics/lib/analytics-url-state'

const NOW = new Date('2026-08-12T10:30:00.000Z')
const PATTERN_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'

describe('resolveTerrainBackPath', () => {
  it('returns null on hubs and non-terrain routes', () => {
    expect(resolveTerrainBackPath({ kind: 'static', path: '/reporting' })).toBeNull()
    expect(resolveTerrainBackPath({ kind: 'static', path: '/login' })).toBeNull()
    expect(resolveTerrainBackPath({ kind: 'invitation', token: 't' })).toBeNull()
  })

  it('returns the semantic parent for a signal detail', () => {
    expect(resolveTerrainBackPath({ kind: 'signal-detail', signalId: 'sig-1' })).toBe('/signals')
  })

  it('returns the analytics pattern when a signal was opened from Analytics', () => {
    const search = `?analytics_pattern_id=${PATTERN_ID}`
    const href = resolveTerrainBackPath(
      { kind: 'signal-detail', signalId: 'sig-1' },
      { search, now: NOW },
    )
    expect(href).toBe(
      buildAnalyticsPatternDetailPath(PATTERN_ID, {
        periodStart: '2026-07-13T10:30:00.000Z',
        periodEnd: '2026-08-12T10:30:00.000Z',
        organizationId: null,
        establishmentIds: [],
        q: '',
        recurrence: 'all',
        responsibleBusinessUnitIds: [],
        responsibleBusinessUnitUnassigned: false,
        signalStatuses: [],
      }),
    )
  })

  it('preserves Analytics filters when leaving a pattern detail', () => {
    const href = resolveTerrainBackPath(
      { kind: 'analytics-pattern-detail', patternId: PATTERN_ID },
      { search: '?q=retard', now: NOW },
    )
    expect(href).toContain('/analytics?')
    expect(href).toContain('q=retard')
  })

  it('sends analytics without operational access to the authenticated landing', () => {
    expect(
      resolveTerrainBackPath(
        { kind: 'static', path: '/analytics' },
        { hasOperationalAccess: false, authenticatedLandingPath: '/organization' },
      ),
    ).toBe('/organization')
    expect(
      resolveTerrainBackPath(
        { kind: 'static', path: '/analytics' },
        { hasOperationalAccess: false },
      ),
    ).toBe('/login')
  })

  it('keeps /general as the analytics back path when operational access is present', () => {
    expect(
      resolveTerrainBackPath(
        { kind: 'static', path: '/analytics' },
        { hasOperationalAccess: true },
      ),
    ).toBe('/general')
  })

  it('sends scoped dashboards back to Général', () => {
    expect(
      resolveTerrainBackPath({
        kind: 'scoped-terrain',
        scope: { type: 'cross' },
        page: 'dashboard',
      }),
    ).toBe('/general')
    expect(
      resolveTerrainBackPath({
        kind: 'scoped-terrain',
        scope: { type: 'establishment', establishmentId: 'est-1' },
        page: 'dashboard',
      }),
    ).toBe('/general')
  })
})
