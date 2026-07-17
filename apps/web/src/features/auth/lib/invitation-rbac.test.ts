import { describe, expect, it } from 'vitest'

import { getAllowedInviteTargetRoles, requiresInviteScopes } from '@/features/auth/lib/invitation-rbac'

describe('invitation-rbac', () => {
  it('returns allowed invite target roles for actor roles', () => {
    expect(getAllowedInviteTargetRoles('owner')).toEqual([
      'owner',
      'director',
      'manager',
      'staff',
    ])
    expect(getAllowedInviteTargetRoles('director')).toEqual(['director', 'manager', 'staff'])
    expect(getAllowedInviteTargetRoles('manager')).toEqual(['staff'])
    expect(getAllowedInviteTargetRoles('staff')).toEqual([])
    expect(getAllowedInviteTargetRoles(null)).toEqual([])
    expect(getAllowedInviteTargetRoles(undefined)).toEqual([])
  })

  it('requires scopes only for manager and staff invites', () => {
    expect(requiresInviteScopes('staff')).toBe(true)
    expect(requiresInviteScopes('manager')).toBe(true)
    expect(requiresInviteScopes('owner')).toBe(false)
    expect(requiresInviteScopes('director')).toBe(false)
    expect(requiresInviteScopes(null)).toBe(false)
  })
})
