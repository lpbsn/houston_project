import { describe, expect, it } from 'vitest'

import {
  canAccessTeamInvite,
  canSeeInviteMemberButton,
  getAllowedInviteTargetRoles,
} from '@/features/auth/lib/invitation-rbac'

describe('invitation-rbac', () => {
  it('shows invite button for owner/director/manager only', () => {
    expect(canSeeInviteMemberButton('owner')).toBe(true)
    expect(canSeeInviteMemberButton('director')).toBe(true)
    expect(canSeeInviteMemberButton('manager')).toBe(true)
    expect(canSeeInviteMemberButton('staff')).toBe(false)
    expect(canSeeInviteMemberButton(null)).toBe(false)
    expect(canSeeInviteMemberButton(undefined)).toBe(false)
  })

  it('allows team invite page for owner/director/manager only', () => {
    expect(canAccessTeamInvite('owner')).toBe(true)
    expect(canAccessTeamInvite('director')).toBe(true)
    expect(canAccessTeamInvite('manager')).toBe(true)
    expect(canAccessTeamInvite('staff')).toBe(false)
    expect(canAccessTeamInvite(null)).toBe(false)
    expect(canAccessTeamInvite(undefined)).toBe(false)
  })

  it('returns allowed target roles by actor role', () => {
    expect(getAllowedInviteTargetRoles('owner')).toEqual(['staff', 'manager'])
    expect(getAllowedInviteTargetRoles('director')).toEqual(['staff', 'manager'])
    expect(getAllowedInviteTargetRoles('manager')).toEqual(['staff'])
    expect(getAllowedInviteTargetRoles('staff')).toEqual([])
    expect(getAllowedInviteTargetRoles(null)).toEqual([])
    expect(getAllowedInviteTargetRoles(undefined)).toEqual([])
  })
})
