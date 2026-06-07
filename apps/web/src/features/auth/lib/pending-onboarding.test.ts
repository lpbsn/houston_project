import { describe, expect, it } from 'vitest'

import {
  buildOnboardingUrl,
  resolvePendingLanding,
  type PendingOnboardingMembership,
} from '@/features/auth/lib/pending-onboarding'

function pending(overrides: Partial<PendingOnboardingMembership>): PendingOnboardingMembership {
  return {
    id: '11111111-1111-1111-1111-111111111111',
    establishment_id: '22222222-2222-2222-2222-222222222222',
    establishment_name: 'Demo Hotel',
    establishment_status: 'draft',
    role: 'owner',
    onboarding_session_id: '33333333-3333-3333-3333-333333333333',
    can_continue_onboarding: true,
    ...overrides,
  }
}

describe('resolvePendingLanding', () => {
  it('returns none when there are no pending memberships', () => {
    expect(resolvePendingLanding([])).toEqual({ kind: 'none' })
  })

  it('returns onboarding for a single owner pending membership', () => {
    const item = pending({ role: 'owner', can_continue_onboarding: true })
    expect(resolvePendingLanding([item])).toEqual({ kind: 'onboarding', pending: item })
  })

  it('returns waiting for a single director pending membership', () => {
    const item = pending({
      role: 'director',
      can_continue_onboarding: false,
    })
    expect(resolvePendingLanding([item])).toEqual({ kind: 'waiting', pending: item })
  })

  it('returns selection when multiple pending memberships exist', () => {
    const first = pending({ establishment_name: 'Hotel A' })
    const second = pending({
      id: '44444444-4444-4444-4444-444444444444',
      establishment_id: '55555555-5555-5555-5555-555555555555',
      establishment_name: 'Hotel B',
      role: 'director',
      can_continue_onboarding: false,
    })

    expect(resolvePendingLanding([first, second])).toEqual({
      kind: 'selection',
      pendingMemberships: [first, second],
    })
  })
})

describe('buildOnboardingUrl', () => {
  it('includes establishment and session ids in the query string', () => {
    const item = pending({})
    expect(buildOnboardingUrl(item)).toBe(
      '/onboarding?establishmentId=22222222-2222-2222-2222-222222222222&sessionId=33333333-3333-3333-3333-333333333333',
    )
  })
})
