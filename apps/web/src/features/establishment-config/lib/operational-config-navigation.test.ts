import { describe, expect, it } from 'vitest'

import {
  buildOperationalConfigFallbackPath,
  buildOperationalConfigPath,
} from './operational-config-navigation'

const EST_ID = '11111111-1111-4111-8111-111111111111'

describe('operational-config-navigation', () => {
  it('builds the establishment-scoped ops-config path', () => {
    expect(buildOperationalConfigPath(EST_ID)).toBe(`/e/${EST_ID}/operational-config`)
  })

  it('builds the mobile fallback onto the same establishment reporting hub', () => {
    expect(buildOperationalConfigFallbackPath(EST_ID)).toBe(`/e/${EST_ID}/reporting`)
  })
})
