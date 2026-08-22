import { describe, expect, it } from 'vitest'

import { parseAppRoute, serializeAppRoute } from '@/app/app-routes'
import {
  parseScopedTerrainRoute,
  serializeScopedExecutionDetailPath,
  serializeScopedSignalDetailPath,
  serializeScopedTerrainPath,
} from '@/app/scoped-terrain'

const EST_ID = '22222222-2222-4222-8222-222222222222'
const SIGNAL_ID = '33333333-3333-4333-8333-333333333333'
const EXEC_ID = '44444444-4444-4444-8444-444444444444'

describe('scoped terrain routes', () => {
  it('parses Cross dashboard and hub pages', () => {
    expect(parseScopedTerrainRoute('/cross')).toEqual({
      kind: 'scoped-terrain',
      scope: { type: 'cross' },
      page: 'dashboard',
    })
    expect(parseScopedTerrainRoute('/cross/signals')).toEqual({
      kind: 'scoped-terrain',
      scope: { type: 'cross' },
      page: 'signals',
    })
  })

  it('parses establishment dashboard and hub pages', () => {
    expect(parseScopedTerrainRoute(`/e/${EST_ID}`)).toEqual({
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: EST_ID },
      page: 'dashboard',
    })
    expect(parseScopedTerrainRoute(`/e/${EST_ID}/general`)).toEqual({
      kind: 'scoped-terrain',
      scope: { type: 'establishment', establishmentId: EST_ID },
      page: 'general',
    })
  })

  it('parses scoped signal and execution details', () => {
    expect(parseAppRoute(`/cross/signals/${SIGNAL_ID}`)).toEqual({
      kind: 'signal-detail',
      signalId: SIGNAL_ID,
      scope: { type: 'cross' },
    })
    expect(parseAppRoute(`/e/${EST_ID}/execution/${EXEC_ID}`)).toEqual({
      kind: 'action-plan-execution-detail',
      executionId: EXEC_ID,
      scope: { type: 'establishment', establishmentId: EST_ID },
    })
  })

  it('rejects invalid establishment ids', () => {
    expect(parseScopedTerrainRoute('/e/not-a-uuid')).toBeNull()
    expect(parseAppRoute('/e/not-a-uuid').kind).toBe('unknown')
  })

  it('round-trips scoped paths', () => {
    const hrefs = [
      '/cross',
      '/cross/signals',
      '/cross/settings',
      serializeScopedSignalDetailPath({ type: 'cross' }, SIGNAL_ID),
      serializeScopedExecutionDetailPath({ type: 'cross' }, EXEC_ID),
      serializeScopedTerrainPath({ type: 'establishment', establishmentId: EST_ID }),
      serializeScopedTerrainPath(
        { type: 'establishment', establishmentId: EST_ID },
        'signals',
      ),
      serializeScopedSignalDetailPath(
        { type: 'establishment', establishmentId: EST_ID },
        SIGNAL_ID,
      ),
    ]

    for (const href of hrefs) {
      expect(serializeAppRoute(parseAppRoute(href))).toBe(href)
    }
  })
})
