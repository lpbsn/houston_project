import { describe, expect, it } from 'vitest'

import { getEstablishmentAdminInviteTargetRoles } from './establishment-admin-invite-roles'

describe('getEstablishmentAdminInviteTargetRoles', () => {
  it('allows owner to invite director manager staff only', () => {
    expect(getEstablishmentAdminInviteTargetRoles('owner')).toEqual([
      'director',
      'manager',
      'staff',
    ])
  })

  it('allows director to invite manager and staff only', () => {
    expect(getEstablishmentAdminInviteTargetRoles('director')).toEqual([
      'manager',
      'staff',
    ])
  })

  it('returns empty for other roles', () => {
    expect(getEstablishmentAdminInviteTargetRoles('manager')).toEqual([])
    expect(getEstablishmentAdminInviteTargetRoles(null)).toEqual([])
  })
})
