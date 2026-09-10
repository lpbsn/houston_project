import { describe, expect, it } from 'vitest'

import { canManageOperationalConfigForEstablishment } from './can-manage-operational-config'

const EST_ID = '11111111-1111-4111-8111-111111111111'

describe('canManageOperationalConfigForEstablishment', () => {
  it('allows an active owner or director on that establishment', () => {
    expect(
      canManageOperationalConfigForEstablishment({
        memberships: [
          {
            status: 'active',
            role: 'owner',
            establishment_id: EST_ID,
          },
        ],
        establishmentId: EST_ID,
      }),
    ).toBe(true)
    expect(
      canManageOperationalConfigForEstablishment({
        memberships: [
          {
            status: 'active',
            role: 'director',
            establishment_id: EST_ID,
          },
        ],
        establishmentId: EST_ID,
      }),
    ).toBe(true)
  })

  it('rejects staff, manager, inactive, and other establishments', () => {
    expect(
      canManageOperationalConfigForEstablishment({
        memberships: [{ status: 'active', role: 'manager', establishment_id: EST_ID }],
        establishmentId: EST_ID,
      }),
    ).toBe(false)
    expect(
      canManageOperationalConfigForEstablishment({
        memberships: [{ status: 'active', role: 'staff', establishment_id: EST_ID }],
        establishmentId: EST_ID,
      }),
    ).toBe(false)
    expect(
      canManageOperationalConfigForEstablishment({
        memberships: [{ status: 'invited', role: 'owner', establishment_id: EST_ID }],
        establishmentId: EST_ID,
      }),
    ).toBe(false)
    expect(
      canManageOperationalConfigForEstablishment({
        memberships: [
          {
            status: 'active',
            role: 'owner',
            establishment_id: '22222222-2222-4222-8222-222222222222',
          },
        ],
        establishmentId: EST_ID,
      }),
    ).toBe(false)
  })
})
