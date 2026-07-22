import { describe, expect, it } from 'vitest'

import {
  canOpenEstablishmentsHub,
  canSwitchEstablishment,
} from '@/features/auth/lib/establishment-switch'
import type { PendingOnboardingMembership } from '@/features/auth/lib/pending-onboarding'
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

function pending(
  overrides: Partial<PendingOnboardingMembership> = {},
): PendingOnboardingMembership {
  return {
    id: 'pending-1',
    establishment_id: 'draft-1',
    establishment_name: 'Draft Hotel',
    establishment_status: 'draft',
    role: 'owner',
    onboarding_session_id: 'session-1',
    can_continue_onboarding: true,
    ...overrides,
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

describe('canOpenEstablishmentsHub', () => {
  it('opens for owner with a single ACTIVE when create is allowed', () => {
    expect(
      canOpenEstablishmentsHub({
        memberships: [membership('est-1', 'Nice')],
        activeEstablishmentId: 'est-1',
        pendingOnboardingMemberships: [],
        canCreateEstablishment: true,
      }),
    ).toBe(true)
  })

  it('opens when pending onboarding exists', () => {
    expect(
      canOpenEstablishmentsHub({
        memberships: [membership('est-1', 'Nice')],
        activeEstablishmentId: 'est-1',
        pendingOnboardingMemberships: [pending()],
        canCreateEstablishment: false,
      }),
    ).toBe(true)
  })

  it('opens when multiple ACTIVE memberships allow switch', () => {
    expect(
      canOpenEstablishmentsHub({
        memberships: [membership('est-1', 'Nice'), membership('est-2', 'Cannes')],
        activeEstablishmentId: 'est-1',
        pendingOnboardingMemberships: [],
        canCreateEstablishment: false,
      }),
    ).toBe(true)
  })

  it('stays closed with one ACTIVE and no create/pending', () => {
    expect(
      canOpenEstablishmentsHub({
        memberships: [membership('est-1', 'Nice')],
        activeEstablishmentId: 'est-1',
        pendingOnboardingMemberships: [],
        canCreateEstablishment: false,
      }),
    ).toBe(false)
  })
})
