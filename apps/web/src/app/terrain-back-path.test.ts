import { describe, expect, it } from 'vitest'

import { createMemoryHistory } from '@/app/app-history'
import {
  classifyTerrainTransition,
  performTerrainBack,
  resolveTerrainBackPath,
} from '@/app/terrain-back-path'
import { buildAnalyticsPatternDetailPath } from '@/features/analytics/lib/analytics-url-state'

const NOW = new Date('2026-08-12T10:30:00.000Z')
const PATTERN_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'

describe('resolveTerrainBackPath', () => {
  it('returns null on hubs and non-terrain routes', () => {
    expect(resolveTerrainBackPath({ kind: 'static', path: '/reporting' })).toBeNull()
    expect(resolveTerrainBackPath({ kind: 'static', path: '/login' })).toBeNull()
    expect(resolveTerrainBackPath({ kind: 'invitation' })).toBeNull()
    expect(resolveTerrainBackPath({ kind: 'email-change' })).toBeNull()
    expect(resolveTerrainBackPath({ kind: 'password-reset' })).toBeNull()
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
        { hasOperationalAccess: false, authenticatedLandingPath: '/no-establishment' },
      ),
    ).toBe('/no-establishment')
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

  it('restores cross calendar search from a cross execution detail', () => {
    expect(
      resolveTerrainBackPath(
        {
          kind: 'action-plan-execution-detail',
          executionId: 'exec-1',
          scope: { type: 'cross' },
        },
        { search: '?layout=calendar&granularity=week&anchor=2026-09-08&view_mode=personal' },
      ),
    ).toBe(
      '/cross/execution?layout=calendar&granularity=week&anchor=2026-09-08&view_mode=personal',
    )
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

  it('returns to history instead of the operational feed when the detail was opened from history', () => {
    expect(
      resolveTerrainBackPath(
        {
          kind: 'action-plan-execution-detail',
          executionId: 'exec-1',
          scope: { type: 'cross' },
        },
        { search: '?entry=history&kind=executions&anchor=exec-1' },
      ),
    ).toBe('/cross/history?kind=executions&anchor=exec-1')
    expect(
      resolveTerrainBackPath(
        {
          kind: 'signal-detail',
          signalId: 'sig-1',
          scope: { type: 'establishment', establishmentId: 'est-1' },
        },
        { search: '?entry=history&period=custom&from=2026-03-01&to=2026-03-29&anchor=sig-1' },
      ),
    ).toBe('/e/est-1/general/history?period=custom&from=2026-03-01&to=2026-03-29&anchor=sig-1')
    expect(
      resolveTerrainBackPath(
        { kind: 'signal-detail', signalId: 'sig-1' },
        { search: '?entry=history' },
      ),
    ).toBe('/general/history')
  })

  it('returns the signal detail, including analytics context, from plan creation', () => {
    expect(
      resolveTerrainBackPath(
        { kind: 'signal-action-create', signalId: 'sig-1' },
        { search: `?analytics_pattern_id=${PATTERN_ID}`, now: NOW },
      ),
    ).toContain('/signals/sig-1?')
    expect(
      resolveTerrainBackPath({ kind: 'signal-action-create', signalId: 'sig-1' }),
    ).toBe('/signals/sig-1')
  })
})

describe('performTerrainBack', () => {
  it('pops to the real parent when it is still the resolved destination', () => {
    const history = createMemoryHistory('/signals')
    history.navigate('/signals/sig-1')

    expect(performTerrainBack(history)).toBe('navigated')
    expect(history.getHref()).toBe('/signals')
    expect(history.getNavigationCause()).toBe('pop')
  })

  it('replaces with the fallback when the detail was opened directly', () => {
    const history = createMemoryHistory('/signals/sig-1')

    expect(performTerrainBack(history)).toBe('navigated')
    expect(history.getHref()).toBe('/signals')
    expect(history.getNavigationCause()).toBe('programmatic')
    expect(history.getLineage()).toBeNull()
  })

  it('does not pop a parent from another establishment', () => {
    const other = '22222222-2222-4222-8222-222222222222'
    const current = '33333333-3333-4333-8333-333333333333'
    const signalId = '44444444-4444-4444-8444-444444444444'
    const history = createMemoryHistory(`/e/${other}/signals`)
    history.navigate(`/e/${current}/signals/${signalId}`)

    expect(
      performTerrainBack(history, { activeEstablishmentId: current }),
    ).toBe('navigated')
    expect(history.getHref()).toBe(`/e/${current}/signals`)
    expect(history.getNavigationCause()).toBe('programmatic')
  })

  it('keeps the filtered parent when a local replace happened before opening the detail', () => {
    const history = createMemoryHistory('/execution')
    history.navigate('/execution?layout=calendar', { replace: true })
    history.navigate('/action-plans/executions/exec-1?layout=calendar')

    expect(performTerrainBack(history, { search: '?layout=calendar' })).toBe('navigated')
    expect(history.getHref()).toBe('/execution?layout=calendar')
    expect(history.getNavigationCause()).toBe('pop')
  })
})

describe('classifyTerrainTransition', () => {
  it('treats hub to detail as forward and the return as back', () => {
    const hub = { kind: 'static' as const, path: '/signals' as const }
    const detail = { kind: 'signal-detail' as const, signalId: 'sig-1' }
    expect(classifyTerrainTransition(hub, detail)).toBe('forward')
    expect(classifyTerrainTransition(detail, hub)).toBe('back')
  })

  it('does not treat a primary change as hierarchical', () => {
    expect(
      classifyTerrainTransition(
        { kind: 'static', path: '/signals' },
        { kind: 'static', path: '/execution' },
      ),
    ).toBe('fade')
  })
})
