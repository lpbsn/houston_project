import { describe, expect, it } from 'vitest'

import { canSeeChecklistLibrary } from './checklist-management-access'

describe('checklist-management-access', () => {
  it('allows all active roles to see the checklist library', () => {
    expect(canSeeChecklistLibrary('owner')).toBe(true)
    expect(canSeeChecklistLibrary('director')).toBe(true)
    expect(canSeeChecklistLibrary('manager')).toBe(true)
    expect(canSeeChecklistLibrary('staff')).toBe(true)
    expect(canSeeChecklistLibrary(null)).toBe(false)
  })
})
