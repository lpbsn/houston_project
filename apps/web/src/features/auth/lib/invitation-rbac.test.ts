import { describe, expect, it } from 'vitest'

import { getAllowedInviteTargetRoles, requiresInviteScopes, resolveTeamInviteRoleOptions } from '@/features/auth/lib/invitation-rbac'

describe('invitation-rbac', () => {
  it('returns allowed invite target roles for actor roles', () => {
    expect(getAllowedInviteTargetRoles('owner')).toEqual(['director', 'manager', 'staff'])
    expect(getAllowedInviteTargetRoles('director')).toEqual(['manager', 'staff'])
    expect(getAllowedInviteTargetRoles('manager')).toEqual(['staff'])
    expect(getAllowedInviteTargetRoles('staff')).toEqual([])
    expect(getAllowedInviteTargetRoles(null)).toEqual([])
    expect(getAllowedInviteTargetRoles(undefined)).toEqual([])
  })

  it('prepends owner only when the actor can manage the organization', () => {
    expect(
      resolveTeamInviteRoleOptions({ actorRole: 'owner', canManageOrganization: true }),
    ).toEqual(['owner', 'director', 'manager', 'staff'])
    expect(
      resolveTeamInviteRoleOptions({ actorRole: 'owner', canManageOrganization: false }),
    ).toEqual(['director', 'manager', 'staff'])
    expect(
      resolveTeamInviteRoleOptions({ actorRole: 'director', canManageOrganization: true }),
    ).toEqual(['owner', 'manager', 'staff'])
    expect(
      resolveTeamInviteRoleOptions({ actorRole: 'staff', canManageOrganization: false }),
    ).toEqual([])
  })

  it('requires scopes only for manager and staff invites', () => {
    expect(requiresInviteScopes('staff')).toBe(true)
    expect(requiresInviteScopes('manager')).toBe(true)
    expect(requiresInviteScopes('director')).toBe(false)
    expect(requiresInviteScopes('owner')).toBe(false)
    expect(requiresInviteScopes(null)).toBe(false)
  })
})
