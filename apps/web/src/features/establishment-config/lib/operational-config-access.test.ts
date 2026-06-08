import { describe, expect, it } from 'vitest'

import { canAccessOperationalConfig } from '@/features/establishment-config/lib/operational-config-access'

describe('canAccessOperationalConfig', () => {
  it('allows owner and director', () => {
    expect(canAccessOperationalConfig('owner')).toBe(true)
    expect(canAccessOperationalConfig('director')).toBe(true)
  })

  it('denies manager and staff', () => {
    expect(canAccessOperationalConfig('manager')).toBe(false)
    expect(canAccessOperationalConfig('staff')).toBe(false)
  })

  it('denies missing or unknown roles', () => {
    expect(canAccessOperationalConfig(null)).toBe(false)
    expect(canAccessOperationalConfig(undefined)).toBe(false)
    expect(canAccessOperationalConfig('')).toBe(false)
    expect(canAccessOperationalConfig('admin')).toBe(false)
  })
})
