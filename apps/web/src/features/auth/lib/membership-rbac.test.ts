import { describe, expect, it } from 'vitest'

import {
  canActorManageTargetRole,
  canChangeMembershipRoleViaPatch,
  getEditableRoleOptions,
} from '@/features/auth/lib/membership-rbac'

describe('membership-rbac', () => {
  it('allows owners to manage all membership roles', () => {
    expect(canActorManageTargetRole('owner', 'director')).toBe(true)
    expect(canActorManageTargetRole('owner', 'owner')).toBe(true)
  })

  it('restricts directors to manager and staff manage targets', () => {
    expect(canActorManageTargetRole('director', 'owner')).toBe(false)
    expect(canActorManageTargetRole('director', 'director')).toBe(false)
    expect(canActorManageTargetRole('director', 'manager')).toBe(true)
  })

  it('allows managers to target staff and manager roles for manage', () => {
    expect(canActorManageTargetRole('manager', 'staff')).toBe(true)
    expect(canActorManageTargetRole('manager', 'owner')).toBe(false)
  })

  it('never offers owner or director as PATCH destinations', () => {
    expect(getEditableRoleOptions('owner')).toEqual(['manager', 'staff'])
    expect(getEditableRoleOptions('director')).toEqual(['manager', 'staff'])
    expect(getEditableRoleOptions('manager')).toEqual(['manager', 'staff'])
  })

  it('blocks PATCH role changes for owner targets', () => {
    expect(canChangeMembershipRoleViaPatch('owner')).toBe(false)
    expect(getEditableRoleOptions('owner', 'owner')).toEqual([])
  })

  it('allows director demotion destinations for owner actors', () => {
    expect(canChangeMembershipRoleViaPatch('director')).toBe(true)
    expect(getEditableRoleOptions('owner', 'director')).toEqual(['manager', 'staff'])
  })
})
