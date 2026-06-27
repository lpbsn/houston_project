import { describe, expect, it } from 'vitest'

import { canSwitchEstablishment } from '@/features/auth/lib/establishment-switch'
import type { Membership } from '@/features/auth/types'

function membership(establishmentId: string, establishmentName: string): Membership {
  return {
    id: `member-${establishmentId}`,
    establishment_id: establishmentId,
    establishment_name: establishmentName,
    organization_id: 'org-1',
    organization_name: 'Org',
    role: 'staff',
    status: 'active',
    scopes: [],
    scope_summary: {
      business_unit_count: 0,
    },
  }
}

describe('canSwitchEstablishment', () => {
  it('returns false for a single membership', () => {
    expect(canSwitchEstablishment([membership('est-1', 'Nice')], 'est-1')).toBe(false)
  })

  it('returns true when another establishment is available', () => {
    expect(
      canSwitchEstablishment(
        [membership('est-1', 'Nice'), membership('est-2', 'Cannes')],
        'est-1',
      ),
    ).toBe(true)
  })

  it('returns true for multiple memberships without an active establishment', () => {
    expect(
      canSwitchEstablishment(
        [membership('est-1', 'Nice'), membership('est-2', 'Cannes')],
        null,
      ),
    ).toBe(true)
  })

  it('returns false when active establishment is the only distinct target', () => {
    expect(
      canSwitchEstablishment([membership('est-1', 'Nice')], 'est-2'),
    ).toBe(false)
  })
})
