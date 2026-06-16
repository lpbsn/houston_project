import { describe, expect, it } from 'vitest'

import { canAccessChecklistLibrary } from './checklist-management-access'

describe('checklist-management-access', () => {
  it('allows catalogue access when establishment and membership are active', () => {
    expect(
      canAccessChecklistLibrary({
        establishmentId: 'est-1',
        activeMembershipId: 'member-1',
      }),
    ).toBe(true)
    expect(
      canAccessChecklistLibrary({
        establishmentId: null,
        activeMembershipId: 'member-1',
      }),
    ).toBe(false)
    expect(
      canAccessChecklistLibrary({
        establishmentId: 'est-1',
        activeMembershipId: null,
      }),
    ).toBe(false)
  })
})
