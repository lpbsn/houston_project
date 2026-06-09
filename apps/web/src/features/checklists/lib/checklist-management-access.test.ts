import { describe, expect, it } from 'vitest'

import {
  canSeePersonalChecklistManagement,
  canSeeSharedChecklistManagement,
} from './checklist-management-access'

describe('checklist-management-access', () => {
  it('allows shared management visibility for owner, director, and manager only', () => {
    expect(canSeeSharedChecklistManagement('owner')).toBe(true)
    expect(canSeeSharedChecklistManagement('director')).toBe(true)
    expect(canSeeSharedChecklistManagement('manager')).toBe(true)
    expect(canSeeSharedChecklistManagement('staff')).toBe(false)
    expect(canSeeSharedChecklistManagement(null)).toBe(false)
  })

  it('allows personal management for all active roles', () => {
    expect(canSeePersonalChecklistManagement('owner')).toBe(true)
    expect(canSeePersonalChecklistManagement('director')).toBe(true)
    expect(canSeePersonalChecklistManagement('manager')).toBe(true)
    expect(canSeePersonalChecklistManagement('staff')).toBe(true)
    expect(canSeePersonalChecklistManagement(null)).toBe(false)
  })
})
