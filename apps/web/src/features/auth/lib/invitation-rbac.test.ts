import { describe, expect, it } from 'vitest'

import { getAllowedInviteTargetRoles } from '@/features/auth/lib/invitation-rbac'

describe('invitation-rbac', () => {
  it('returns allowed invite target roles for actor roles', () => {
    expect(getAllowedInviteTargetRoles('owner')).toEqual(['staff', 'manager'])
    expect(getAllowedInviteTargetRoles('director')).toEqual(['staff', 'manager'])
    expect(getAllowedInviteTargetRoles('manager')).toEqual(['staff'])
    expect(getAllowedInviteTargetRoles('staff')).toEqual([])
    expect(getAllowedInviteTargetRoles(null)).toEqual([])
    expect(getAllowedInviteTargetRoles(undefined)).toEqual([])
  })
})
