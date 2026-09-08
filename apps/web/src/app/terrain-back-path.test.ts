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

  it('keeps /analytics without a back path when operational access is present', () => {
    expect(
      resolveTerrainBackPath(
        { kind: 'static', path: '/analytics' },
        { hasOperationalAccess: true },
      ),
    ).toBeNull()
  })

  it('returns the execution feed with calendar search from a detail', () => {
    expect(
      resolveTerrainBackPath(
        { kind: 'action-plan-execution-detail', executionId: 'exec-1' },
        { search: '?layout=calendar&granularity=week&anchor=2026-09-08' },
      ),
    ).toBe('/execution?layout=calendar&granularity=week&anchor=2026-09-08')
    expect(
      resolveTerrainBackPath(
        {
          kind: 'action-plan-execution-detail',
          executionId: 'exec-1',
          scope: { type: 'establishment', establishmentId: 'est-1' },
        },
        { search: '?layout=calendar&granularity=day&anchor=2026-09-08' },
      ),
    ).toBe('/e/est-1/execution?layout=calendar&granularity=day&anchor=2026-09-08')
  })

  it('keeps calendar search when leaving execution edit for the detail', () => {
    expect(
      resolveTerrainBackPath(
        { kind: 'action-plan-execution-edit', executionId: 'exec-1' },
        { search: '?layout=calendar&granularity=week&anchor=2026-09-08&tab=comments' },
      ),
    ).toBe(
      '/action-plans/executions/exec-1?layout=calendar&granularity=week&anchor=2026-09-08&tab=comments',
    )
  })

  it('does not attach calendar state when leaving a cross-establishment execution', () => {
    expect(
      resolveTerrainBackPath({
        kind: 'action-plan-execution-detail',
        executionId: 'exec-1',
        scope: { type: 'cross' },
      }),
    ).toBe('/cross/execution')
  })

  it('does not treat scoped dashboards as nested details', () => {
    expect(
      resolveTerrainBackPath({
        kind: 'scoped-terrain',
        scope: { type: 'cross' },
        page: 'dashboard',
      }),
    ).toBeNull()
    expect(
      resolveTerrainBackPath({
        kind: 'scoped-terrain',
        scope: { type: 'establishment', establishmentId: 'est-1' },
        page: 'dashboard',
      }),
    ).toBeNull()
  })
})
