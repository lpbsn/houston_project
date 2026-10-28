// @vitest-environment jsdom

import { describe, expect, it } from 'vitest'

import {
  clearAccessArrival,
  readAccessArrivalForDisplay,
  releaseDisplayedAccessArrival,
  rememberAccessArrival,
  resolveAccessCopy,
} from './arrival'
import type { BootstrapResponse } from '@/features/auth/types'

const arrival = {
  userId: 'user-1',
  arrival: 'activated' as const,
  establishmentId: 'est-1',
}

function bootstrap(overrides: Partial<BootstrapResponse> = {}): BootstrapResponse {
  return {
    authenticated: true,
    user: { id: 'user-1', email: 'spore@example.com' },
    memberships: [
      {
        id: 'm-1',
        establishment_id: 'est-1',
        establishment_name: 'Hôtel des Mésanges',
        organization_id: 'org-1',
        organization_name: 'Org',
        role: 'staff',
        status: 'active',
        chat_available: false,
        scopes: [],
        scope_summary: { business_unit_count: 0 },
      },
    ],
    active_membership: null,
    pending_onboarding_memberships: [],
    permission_hints: {
      chat_available: false,
      can_create_action_plan: false,
      can_create_catalog_action_plan: false,
      can_view_action_plan_catalog: false,
      can_invite: false,
      can_manage_runtime_config: false,
      can_view_team: false,
      can_manage_organization: false,
      platform_operator_active: false,
    },
    ...overrides,
  } as BootstrapResponse
}

describe('access arrival', () => {
  it('shows a matching arrival once, then forgets it', async () => {
    rememberAccessArrival(arrival)
    expect(readAccessArrivalForDisplay()).toEqual(arrival)
    releaseDisplayedAccessArrival()
    expect(readAccessArrivalForDisplay()).toEqual(arrival)
    expect(sessionStorage.getItem('spore.access-arrival')).toBeNull()
    await Promise.resolve()
    expect(readAccessArrivalForDisplay()).toBeNull()
  })

  it('clears the arrival when the session ends', () => {
    rememberAccessArrival(arrival)
    clearAccessArrival()
    expect(readAccessArrivalForDisplay()).toBeNull()
    expect(sessionStorage.getItem('spore.access-arrival')).toBeNull()
  })
})

describe('resolveAccessCopy', () => {
  it('uses the joined establishment name only for the current account', () => {
    const copy = resolveAccessCopy(bootstrap(), {
      ...arrival,
      arrival: 'joined',
    })
    expect(copy.lines).toEqual(['Vous avez rejoint Hôtel des Mésanges.'])

    const otherAccount = resolveAccessCopy(bootstrap(), {
      ...arrival,
      userId: 'someone-else',
      arrival: 'joined',
    })
    expect(otherAccount.lines).toEqual([])
    expect(otherAccount.question).toBe('Où souhaitez-vous utiliser SPORE ?')
  })

  it('announces a pending establishment and other active access', () => {
    const copy = resolveAccessCopy(
      bootstrap({
        pending_onboarding_memberships: [
          {
            id: 'p-1',
            establishment_id: 'draft-1',
            establishment_name: 'Brouillon',
            establishment_status: 'draft',
            organization_id: 'org-1',
            organization_name: 'Org',
            role: 'staff',
            onboarding_session_id: null,
          },
        ],
      }),
      { userId: 'user-1', arrival: 'activated', establishmentId: 'draft-1' },
    )
    expect(copy.lines[0]).toBe(
      'Votre compte est activé. Votre établissement est encore en préparation.',
    )
    expect(copy.lines[1]).toBe('Vos autres établissements restent accessibles.')
  })
})
