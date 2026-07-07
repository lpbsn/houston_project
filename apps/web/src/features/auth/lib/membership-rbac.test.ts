import { describe, expect, it } from 'vitest'

import {
  canActorManageTargetRole,
  getEditableRoleOptions,
} from '@/features/auth/lib/membership-rbac'

describe('membership-rbac', () => {
  it('allows owners to manage all membership roles', () => {
    expect(getEditableRoleOptions('owner')).toEqual(['owner', 'director', 'manager', 'staff'])
    expect(canActorManageTargetRole('owner', 'director')).toBe(true)
  })

  it('restricts directors to manager and staff targets', () => {
    expect(getEditableRoleOptions('director')).toEqual(['manager', 'staff'])
    expect(canActorManageTargetRole('director', 'owner')).toBe(false)
    expect(canActorManageTargetRole('director', 'manager')).toBe(true)
  })

  it('allows managers to target staff and manager roles', () => {
    expect(getEditableRoleOptions('manager')).toEqual(['staff', 'manager'])
    expect(canActorManageTargetRole('manager', 'staff')).toBe(true)
    expect(canActorManageTargetRole('manager', 'owner')).toBe(false)
  })
})
